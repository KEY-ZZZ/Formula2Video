"""M1 流水线在 mock 模式下的端到端逻辑测试 (不依赖 API key / Manim)。"""

from formula2video.agents import manim_agent, scene_spec_agent
from formula2video.agents.scene_spec_agent import estimate_duration_s
from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Pacing
from formula2video.orchestrator import run


def _mock_llm() -> LLMClient:
    llm = LLMClient(provider="anthropic")
    llm.mock = True  # 强制 mock, 不依赖环境
    return llm


def test_duration_estimate_respects_pacing():
    text = "这是一段用来测试时长估算的旁白文字"
    fast = estimate_duration_s(text, Pacing.FAST)
    slow = estimate_duration_s(text, Pacing.SLOW)
    assert slow > fast
    assert fast >= 1.5  # 最小时长下限


def test_pipeline_mock_produces_valid_spec(tmp_path, monkeypatch):
    from formula2video import config as cfg_mod

    monkeypatch.setattr(cfg_mod.config, "work_dir", tmp_path / "work")
    monkeypatch.setattr(cfg_mod.config, "output_dir", tmp_path / "out")

    result = run("f: \\mathbb{R}^n \\to \\mathbb{R}", llm=_mock_llm())

    # Scene Spec 时间轴自洽 (构造时已校验)
    assert len(result.scene_spec.scenes) > 0
    assert result.scene_spec.total_duration_s > 0

    # 中间产物落盘
    assert (tmp_path / "work" / "scene_spec.json").exists()
    assert (tmp_path / "work" / "scenes.py").exists()


def test_manim_code_generation_is_valid_python():
    spec = scene_spec_agent.run(
        intent=_intent(), script=_script(), llm=_mock_llm()
    )
    code = manim_agent.generate_module(spec)
    # 生成的代码必须能被 Python 解析
    compile(code, "<generated>", "exec")
    assert "from manim import *" in code
    assert "class " in code


# --- 辅助构造 ---
def _intent():
    from formula2video.schemas.contracts import Intent

    return Intent(
        formula_latex="f(x)=x^2",
        topic="二次函数",
        learning_goal="理解抛物线",
        estimated_duration_s=30,
    )


def _script():
    from formula2video.schemas.contracts import Script, ScriptSegment

    return Script(
        title="测试",
        segments=[
            ScriptSegment(narration="第一句"),
            ScriptSegment(narration="关键洞见", insight_moment=True, pacing=Pacing.SLOW),
        ],
    )
