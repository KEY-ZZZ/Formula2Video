"""Intent Agent (WP1) - parse the user's formula into a structured Intent."""
from __future__ import annotations

from typing import Optional

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Intent

_SYSTEM = (
    "你是数学公式解析助手。给定用户输入（公式或自然语言），"
    "输出一个 JSON，字段为：formula_latex, topic, audience_level, "
    "learning_goal, estimated_duration_s。只输出 JSON。"
)


def run(user_input: str, llm: Optional[LLMClient] = None) -> Intent:
    """Parse ``user_input`` into an :class:`Intent`.

    In mock mode the input is echoed into ``formula_latex`` with sensible
    defaults for the remaining fields.
    """
    llm = llm or LLMClient()
    fallback = {
        "formula_latex": user_input.strip(),
        "topic": "公式可视化讲解",
        "audience_level": "本科生",
        "learning_goal": f"理解 {user_input.strip()} 的直觉",
        "estimated_duration_s": 60.0,
    }
    data = llm.complete_json(_SYSTEM, user_input, mock_fallback=fallback)
    return Intent(**data)
