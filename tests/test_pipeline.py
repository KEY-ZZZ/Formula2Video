"""End-to-end M1 pipeline tests, all in mock mode (no network/API keys)."""
from __future__ import annotations

from formula2video import orchestrator
from formula2video.agents import manim_agent
from formula2video.agents.scene_spec_agent import estimate_duration_s
from formula2video.config import config
from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Pacing


def _mock_llm() -> LLMClient:
    llm = LLMClient()
    llm.mock = True
    return llm


def test_estimate_duration_pacing_and_floor():
    text = "这是一段用来测试时长估计的中文旁白文本内容"
    fast = estimate_duration_s(text, Pacing.FAST)
    slow = estimate_duration_s(text, Pacing.SLOW)
    assert slow > fast
    # The minimum floor applies to short text.
    assert estimate_duration_s("短", Pacing.FAST) >= 1.5
    assert fast >= 1.5
    assert slow >= 1.5


def test_orchestrator_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "work_dir", tmp_path / "work")
    monkeypatch.setattr(config, "output_dir", tmp_path / "out")

    result = orchestrator.run("f(x)=x^2", llm=_mock_llm())

    assert result.scene_spec.beats, "scene_spec should not be empty"
    assert result.scene_spec.total_duration_s > 0

    # Intermediate contracts and generated code must land on disk.
    assert (tmp_path / "work" / "scene_spec.json").exists()
    assert (tmp_path / "work" / "scenes.py").exists()

    # The last beat is the insight moment in mock mode.
    assert result.scene_spec.beats[-1].insight_moment is True


def test_generate_module_compiles(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "work_dir", tmp_path / "work")
    monkeypatch.setattr(config, "output_dir", tmp_path / "out")

    result = orchestrator.run("E=mc^2", llm=_mock_llm())
    module_src = manim_agent.generate_module(result.scene_spec)

    assert "from manim import *" in module_src
    # Must be syntactically valid Python.
    compile(module_src, "<test_scenes>", "exec")
