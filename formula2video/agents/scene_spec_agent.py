"""WP5 — Scene Spec Agent (唯一信源生成者)。

把带标签的 Script 编译成机器可执行的 Enriched Scene Spec:
- 为每个场景估算旁白时长 (后续会被 TTS 真实时长校正)
- 为 manim 场景生成 ManimSpec (对象 + 动画序列)
- 为 pixverse 场景生成 PixVerseSpec
- 设置 music_cue, 重算自洽时间轴
"""

from __future__ import annotations

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import (
    Intent,
    ManimAction,
    ManimObject,
    ManimSpec,
    MusicCue,
    PixVerseSpec,
    Pacing,
    Script,
    SceneBeat,
    SceneSpec,
    TTSSpec,
    VisualType,
)

# 中文朗读速度约 4.5 字/秒; insight/slow 放慢
_BASE_CPS = 4.5


def estimate_duration_s(text: str, pacing: Pacing) -> float:
    """根据旁白长度与节奏估算时长(秒)。"""
    chars = max(len(text), 1)
    base = chars / _BASE_CPS
    factor = {Pacing.FAST: 0.85, Pacing.NORMAL: 1.0, Pacing.SLOW: 1.25}[pacing]
    return round(max(base * factor, 1.5), 2)


def _music_for(insight: bool, pacing: Pacing) -> MusicCue:
    if insight:
        return MusicCue(type="revelation", transition="crescendo_then_settle",
                        volume_relative=0.15)
    if pacing == Pacing.FAST:
        return MusicCue(type="buildup", transition="rising", volume_relative=0.2)
    return MusicCue(type="ambient", transition="none", volume_relative=0.2)


SYSTEM = """你把一句旁白 + 视觉意图, 编译成 Manim 动画规格。输出 JSON:
{
  "scene_class": "大驼峰类名",
  "camera_type": "Scene" | "MovingCameraScene" | "ThreeDScene",
  "camera_action": "运镜描述或 null",
  "objects": [{"id":"...","type":"MathTex|Text|Axes|Arrow|...","content":"LaTeX或文本","color":"Manim颜色常量"}],
  "animation_sequence": [{"action":"Write|Create|Transform|FadeIn|wait","target":"对象id或null","run_time":数字,"duration":wait时填}]
}
约束: 坐标隐含在 [-7,7]x[-4,4]; 颜色全程语义一致; 只输出 JSON。"""


def _manim_spec_for(
    segment_idx: int,
    narration: str,
    llm: LLMClient,
) -> ManimSpec:
    cls = f"Scene{segment_idx:02d}"
    mock = {
        "scene_class": cls,
        "camera_type": "Scene",
        "camera_action": None,
        "objects": [
            {"id": "caption", "type": "Text", "content": narration[:30], "color": "WHITE"}
        ],
        "animation_sequence": [
            {"action": "Write", "target": "caption", "run_time": 1.5, "duration": None}
        ],
    }
    data = llm.complete_json(SYSTEM, f"旁白: {narration}", mock_fallback=mock)
    return ManimSpec(
        scene_class=data.get("scene_class", cls),
        camera_type=data.get("camera_type", "Scene"),
        camera_action=data.get("camera_action"),
        objects=[ManimObject(**o) for o in data.get("objects", [])],
        animation_sequence=[ManimAction(**a) for a in data.get("animation_sequence", [])],
    )


def run(intent: Intent, script: Script, llm: LLMClient | None = None) -> SceneSpec:
    """把 Script 编译为 Enriched Scene Spec。"""
    llm = llm or LLMClient()
    beats: list[SceneBeat] = []

    for i, seg in enumerate(script.segments):
        dur = estimate_duration_s(seg.narration, seg.pacing)
        wait_after = 1.5 if seg.insight_moment else 0.3

        manim_spec = None
        pixverse_spec = None
        if seg.visual_type in (VisualType.MANIM, VisualType.HYBRID):
            manim_spec = _manim_spec_for(i, seg.narration, llm)
        if seg.visual_type in (VisualType.PIXVERSE, VisualType.HYBRID):
            pixverse_spec = PixVerseSpec(
                object_prompt=seg.pixverse_object or "abstract concept illustration",
                motion_prompt="subtle natural motion",
                duration_s=min(max(dur, 1.0), 15.0),
            )

        beats.append(
            SceneBeat(
                scene_id=f"scene_{i:02d}",
                timestamp_start_s=0.0,  # 由 recompute_timeline 填
                narration=seg.narration,
                narration_duration_s=dur,
                pacing=seg.pacing,
                insight_moment=seg.insight_moment,
                wait_after_s=wait_after,
                visual_type=seg.visual_type,
                manim=manim_spec,
                pixverse=pixverse_spec,
                tts=TTSSpec(text=seg.narration, pause_after_s=0.3),
                music_cue=_music_for(seg.insight_moment, seg.pacing),
            )
        )

    spec = SceneSpec(title=script.title, scenes=beats)
    return spec.recompute_timeline()
