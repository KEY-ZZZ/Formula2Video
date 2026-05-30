"""Scene Spec Agent (WP5) - compile the script into the enriched SceneSpec.

This is the single source of truth generator. For every script segment it
builds a :class:`SceneBeat`, attaching the Manim / PixVerse / TTS / music
sub-specs the downstream agents read, then recomputes the timeline.
"""
from __future__ import annotations

from typing import Optional, Union

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import (
    CameraType,
    Intent,
    ManimAction,
    ManimObject,
    ManimSpec,
    MusicCue,
    Pacing,
    PixVerseSpec,
    SceneBeat,
    SceneSpec,
    Script,
    ScriptSegment,
    TTSSpec,
    VisualType,
)

# Chinese narration is delivered at roughly this many characters per second.
_BASE_CPS = 4.5
_PACING_MULT = {"fast": 0.85, "normal": 1.0, "slow": 1.25}
_MIN_DURATION_S = 1.5


def estimate_duration_s(text: str, pacing: Union[Pacing, str]) -> float:
    """Estimate narration duration in seconds.

    Chinese is ~4.5 chars/sec; pacing scales it (fast 0.85, normal 1.0,
    slow 1.25). The result is never below ``1.5`` seconds.
    """
    key = getattr(pacing, "value", pacing)
    mult = _PACING_MULT.get(key, 1.0)
    n = max(len((text or "").strip()), 1)
    raw = n / _BASE_CPS * mult
    return round(max(raw, _MIN_DURATION_S), 2)


_MANIM_SYSTEM = (
    "你是 Manim 场景规划助手。给定一段旁白，输出一个 JSON 描述需要绘制的对象与动画。"
    "字段：scene_class(str), camera_type(Scene|MovingCameraScene|ThreeDScene), "
    "camera_action(可空), objects([{id,type,content,color}]), "
    "animation_sequence([{action,target,run_time,duration}])。只输出 JSON。"
)


def _scene_class_name(index: int) -> str:
    return f"Beat{index:02d}Scene"


def _mock_manim_spec(segment: ScriptSegment, index: int) -> ManimSpec:
    """Placeholder Manim spec: a single caption Text written onto the screen."""
    caption = ManimObject(
        id="caption",
        type="Text",
        content=segment.narration[:40] or "公式",
        color="WHITE",
    )
    return ManimSpec(
        scene_class=_scene_class_name(index),
        camera_type=CameraType.STATIC,
        camera_action=None,
        objects=[caption],
        animation_sequence=[
            ManimAction(action="Write", target="caption", run_time=1.5),
            ManimAction(action="wait", target=None, run_time=0.0, duration=0.5),
        ],
    )


def _manim_spec_for(
    segment: ScriptSegment,
    index: int,
    llm: LLMClient,
) -> ManimSpec:
    if llm.mock:
        return _mock_manim_spec(segment, index)
    fallback = _mock_manim_spec(segment, index).model_dump()
    data = llm.complete_json(_MANIM_SYSTEM, segment.narration, mock_fallback=fallback)
    try:
        spec = ManimSpec(**data)
        # Guarantee a usable class name even if the model omitted it.
        if not spec.scene_class:
            spec.scene_class = _scene_class_name(index)
        return spec
    except Exception:
        return _mock_manim_spec(segment, index)


def _pixverse_spec_for(segment: ScriptSegment) -> PixVerseSpec:
    return PixVerseSpec(
        prompt=segment.pixverse_object or "photorealistic abstract scene, no text",
        duration_s=4.0,
        motion="subtle",
    )


def _music_cue_for(segment: ScriptSegment) -> MusicCue:
    if segment.insight_moment:
        return MusicCue(type="revelation", transition="crescendo_then_settle", volume_relative=0.15)
    if segment.pacing == Pacing.FAST:
        return MusicCue(type="buildup", transition="rising", volume_relative=0.2)
    return MusicCue(type="ambient", transition=None, volume_relative=0.2)


def run(
    intent: Intent,
    script: Script,
    llm: Optional[LLMClient] = None,
) -> SceneSpec:
    """Compile ``script`` into an enriched :class:`SceneSpec`."""
    llm = llm or LLMClient()
    beats = []
    for i, segment in enumerate(script.segments):
        duration = estimate_duration_s(segment.narration, segment.pacing)
        wait_after = 1.5 if segment.insight_moment else 0.3

        manim_spec = None
        pixverse_spec = None
        if segment.visual_type in (VisualType.MANIM, VisualType.HYBRID):
            manim_spec = _manim_spec_for(segment, i, llm)
        if segment.visual_type in (VisualType.PIXVERSE, VisualType.HYBRID):
            pixverse_spec = _pixverse_spec_for(segment)

        beats.append(
            SceneBeat(
                scene_id=f"scene_{i:02d}",
                timestamp_start_s=0.0,
                narration=segment.narration,
                narration_duration_s=duration,
                pacing=segment.pacing,
                insight_moment=segment.insight_moment,
                wait_after_s=wait_after,
                visual_type=segment.visual_type,
                manim=manim_spec,
                pixverse=pixverse_spec,
                tts=TTSSpec(text=segment.narration, pause_before_s=0.3, pause_after_s=0.5),
                music_cue=_music_cue_for(segment),
            )
        )

    spec = SceneSpec(beats=beats)
    spec.recompute_timeline()
    return spec
