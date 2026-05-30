"""WP0 — Pipeline Orchestrator。

纯调度: 按顺序调用各 Agent, 传递产物, 落盘可追溯的中间文件。
不做任何内容决策。

M1 链路: Intent -> Curriculum -> Script -> Scene Spec -> Manim -> Assembly
后续里程碑会在 Scene Spec 之后并行调度 TTS / Music / PixVerse。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from formula2video.agents import (
    assembly_agent,
    curriculum_agent,
    intent_agent,
    manim_agent,
    scene_spec_agent,
    script_agent,
)
from formula2video.config import config
from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Curriculum, Intent, Script, SceneSpec


@dataclass
class PipelineResult:
    intent: Intent
    curriculum: Curriculum
    script: Script
    scene_spec: SceneSpec
    rendered: dict[str, Path | None]
    final_video: Path | None


def _dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        obj.model_dump_json(indent=2),  # type: ignore[attr-defined]
        encoding="utf-8",
    )


def run(user_input: str, llm: LLMClient | None = None) -> PipelineResult:
    """跑通 M1 全链路。"""
    llm = llm or LLMClient()
    config.ensure_dirs()
    work = config.work_dir

    # 阶段 A: 理解与规划 (串行)
    intent = intent_agent.run(user_input, llm)
    _dump(intent, work / "intent.json")

    curriculum = curriculum_agent.run(intent, llm)
    _dump(curriculum, work / "curriculum.json")

    script = script_agent.run(intent, curriculum, llm)
    _dump(script, work / "script.json")

    scene_spec = scene_spec_agent.run(intent, script, llm)
    _dump(scene_spec, work / "scene_spec.json")

    # 阶段 B (M1 仅 Manim) + 阶段 C
    rendered = manim_agent.run(scene_spec, work)
    final_video = assembly_agent.run(scene_spec, rendered)

    # 落一份运行摘要
    summary = {
        "title": scene_spec.title,
        "total_duration_s": scene_spec.total_duration_s,
        "scenes": len(scene_spec.scenes),
        "rendered": {k: (str(v) if v else None) for k, v in rendered.items()},
        "final_video": str(final_video) if final_video else None,
        "llm_mock_mode": llm.mock,
    }
    (work / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return PipelineResult(
        intent=intent,
        curriculum=curriculum,
        script=script,
        scene_spec=scene_spec,
        rendered=rendered,
        final_video=final_video,
    )
