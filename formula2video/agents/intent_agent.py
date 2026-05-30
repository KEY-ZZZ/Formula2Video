"""WP1 — Intent Agent。

解析用户输入 (公式 / 自然语言), 产出 Intent: 公式语义、受众、教学目标。
"""

from __future__ import annotations

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Intent

SYSTEM = """你是一个数学教育内容策划。给定用户的公式或描述, 输出一个 JSON 对象, 字段:
- formula_latex: 公式的 LaTeX 表示 (字符串)
- topic: 公式所属的数学主题 (字符串)
- audience_level: 目标受众水平 (默认 "本科生")
- learning_goal: 一句话说明希望观众理解什么 (字符串)
- estimated_duration_s: 建议视频时长(秒), 整数, 10-600

只输出 JSON。"""


def run(user_input: str, llm: LLMClient | None = None) -> Intent:
    """解析用户输入为 Intent。"""
    llm = llm or LLMClient()

    # mock 占位: 直接回显输入, 便于离线跑通链路
    mock = {
        "formula_latex": user_input.strip(),
        "topic": "(mock) 未指定主题",
        "audience_level": "本科生",
        "learning_goal": f"(mock) 理解 {user_input.strip()} 的几何直觉",
        "estimated_duration_s": 60,
    }

    data = llm.complete_json(SYSTEM, f"用户输入:\n{user_input}", mock_fallback=mock)
    return Intent.model_validate(data)
