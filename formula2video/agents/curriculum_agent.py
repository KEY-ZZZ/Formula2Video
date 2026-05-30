"""Curriculum Agent (WP2) - build a minimal just-in-time teaching plan."""
from __future__ import annotations

from typing import Optional

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Curriculum, InlinePrerequisite, Intent

_SYSTEM = (
    "你是课程设计助手，遵守极简即时原则：只识别理解本公式绝对必需的前置概念"
    "（通常 <= 3 个），每个前置概念只用一句话内联解释，禁止生成独立的前置章节。"
    "如果某概念观众大概率已知，直接跳过。"
    "输出 JSON：core_concept(str), inline_prerequisites([{concept, one_liner}]), "
    "teaching_order([str])。只输出 JSON。"
)


def run(intent: Intent, llm: Optional[LLMClient] = None) -> Curriculum:
    """Produce a :class:`Curriculum` from an :class:`Intent`."""
    llm = llm or LLMClient()
    fallback = {
        "core_concept": intent.topic or f"理解 {intent.formula_latex}",
        "inline_prerequisites": [],
        "teaching_order": ["引入类比", "展示公式", "几何直觉", "总结"],
    }
    user = (
        f"公式: {intent.formula_latex}\n主题: {intent.topic}\n"
        f"受众: {intent.audience_level}\n目标: {intent.learning_goal}"
    )
    data = llm.complete_json(_SYSTEM, user, mock_fallback=fallback)
    prereqs = [InlinePrerequisite(**p) for p in data.get("inline_prerequisites", [])]
    # Enforce the minimal principle: at most 3 inline prerequisites.
    prereqs = prereqs[:3]
    return Curriculum(
        core_concept=data.get("core_concept", fallback["core_concept"]),
        inline_prerequisites=prereqs,
        teaching_order=data.get("teaching_order") or fallback["teaching_order"],
    )
