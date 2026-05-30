"""Tests for the core data contracts."""
from __future__ import annotations

from formula2video.schemas.contracts import (
    CameraType,
    Curriculum,
    InlinePrerequisite,
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


def test_intent_defaults():
    intent = Intent(formula_latex="f(x)=x^2")
    assert intent.formula_latex == "f(x)=x^2"
    assert intent.estimated_duration_s > 0


def test_curriculum_roundtrip():
    cur = Curriculum(
        core_concept="平方函数",
        inline_prerequisites=[InlinePrerequisite(concept="x", one_liner="自变量")],
        teaching_order=["引入", "展示", "总结"],
    )
    data = cur.model_dump()
    assert Curriculum(**data) == cur


def test_script_segment_tags():
    seg = ScriptSegment(
        narration="想象一辆车",
        visual_type=VisualType.PIXVERSE,
        insight_moment=False,
        pacing=Pacing.NORMAL,
        pixverse_object="photorealistic car",
    )
    assert seg.visual_type == VisualType.PIXVERSE
    assert seg.pixverse_object == "photorealistic car"
    Script(segments=[seg])


def test_manim_spec_construction():
    spec = ManimSpec(
        scene_class="DemoScene",
        camera_type=CameraType.MOVING,
        objects=[ManimObject(id="f", type="MathTex", content="x^2", color="YELLOW")],
        animation_sequence=[ManimAction(action="Write", target="f", run_time=2.0)],
    )
    assert spec.camera_type == CameraType.MOVING
    assert spec.objects[0].id == "f"


def test_recompute_timeline_is_self_consistent():
    spec = SceneSpec(
        beats=[
            SceneBeat(scene_id="s0", narration_duration_s=4.0, wait_after_s=0.3),
            SceneBeat(scene_id="s1", narration_duration_s=2.0, wait_after_s=1.5),
            SceneBeat(scene_id="s2", narration_duration_s=3.0, wait_after_s=0.3),
        ]
    )
    spec.recompute_timeline()
    assert spec.beats[0].timestamp_start_s == 0.0
    # Each beat starts where the previous one (duration + wait) ended.
    assert spec.beats[1].timestamp_start_s == 4.3
    assert spec.beats[2].timestamp_start_s == 4.3 + 2.0 + 1.5
    # Total = last beat start + its own duration + trailing wait.
    assert spec.total_duration_s == round(
        spec.beats[2].timestamp_start_s + 3.0 + 0.3, 3
    )


def test_subspecs_construct():
    PixVerseSpec(prompt="a scene")
    TTSSpec(text="hello")
    MusicCue(type="revelation", transition="crescendo_then_settle", volume_relative=0.15)
