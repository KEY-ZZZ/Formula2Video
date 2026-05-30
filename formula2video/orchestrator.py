"""Pipeline Orchestrator (WP0) - serially drive the M1 agent chain.

The orchestrator only schedules; it makes no content decisions. It calls each
agent in turn, persists every intermediate contract to ``work_dir`` for
traceability, and writes a ``summary.json``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

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
from formula2video.schemas.contracts import (
    Curriculum,
    Intent,
    SceneSpec,
    Script,
)


@dataclass
class PipelineResult:
    """Aggregated outputs of one pipeline run."""

    intent: Intent
    curriculum: Curriculum
    script: Script
    scene_spec: SceneSpec
    rendered: Dict[str, Optional[Path]]
    final_video: Optional[Path]


def run(user_input: str, llm: Optional[LLMClient] = None) -> PipelineResult:
    """Run the full M1 pipeline for ``user_input``."""
    llm = llm or LLMClient()
    work_dir = Path(config.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Stage A: understanding & planning (serial).
    intent = intent_agent.run(user_input, llm=llm)
    curriculum = curriculum_agent.run(intent, llm=llm)
    script = script_agent.run(intent, curriculum, llm=llm)
    scene_spec = scene_spec_agent.run(intent, script, llm=llm)

    # Persist intermediate contracts for traceability.
    (work_dir / "intent.json").write_text(intent.model_dump_json(indent=2), encoding="utf-8")
    (work_dir / "curriculum.json").write_text(curriculum.model_dump_json(indent=2), encoding="utf-8")
    (work_dir / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
    (work_dir / "scene_spec.json").write_text(scene_spec.model_dump_json(indent=2), encoding="utf-8")

    # Stage B (M1): Manim code generation + rendering.
    rendered = manim_agent.run(scene_spec, work_dir=work_dir)

    # Stage C (M1): assembly (concat only).
    final_video = assembly_agent.run(scene_spec, rendered)

    summary = {
        "user_input": user_input,
        "mock_mode": llm.mock,
        "num_beats": len(scene_spec.beats),
        "total_duration_s": scene_spec.total_duration_s,
        "num_rendered": sum(1 for v in rendered.values() if v is not None),
        "final_video": str(final_video) if final_video else None,
    }
    (work_dir / "summary.json").write_text(
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
