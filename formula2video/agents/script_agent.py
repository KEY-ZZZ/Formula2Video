"""Script Agent (WP3) - write a tagged 3B1B-style script."""
from __future__ import annotations

from typing import Optional

from formula2video.agents.style import THREE_B1B_STYLE_SKILL
from formula2video.llm import LLMClient
from formula2video.schemas.contracts import (
    Curriculum,
    Intent,
    Pacing,
    Script,
    ScriptSegment,
    VisualType,
)

_SYSTEM = (
    THREE_B1B_STYLE_SKILL
    + "\n\n根据教学顺序撰写脚本。输出 JSON：{\"segments\": [{narration, "
    "visual_type(manim|pixverse|hybrid), insight_moment(bool), "
    "pacing(fast|normal|slow), pixverse_object(可空)}]}。"
    "记住：公式/符号一律 visual_type=manim；只有写实物体类比才用 pixverse 并填写 "
    "pixverse_object。只输出 JSON。"
)


def _mock_script(intent: Intent, curriculum: Curriculum) -> Script:
    """Skeleton script following the teaching order; last beat is the insight."""
    order = curriculum.teaching_order or ["展示公式"]
    segments = []
    last = len(order) - 1
    for i, step in enumerate(order):
        is_insight = i == last
        segments.append(
            ScriptSegment(
                narration=f"{step}：{intent.formula_latex}",
                visual_type=VisualType.MANIM,
                insight_moment=is_insight,
                pacing=Pacing.SLOW if is_insight else Pacing.NORMAL,
                pixverse_object=None,
            )
        )
    return Script(segments=segments)


def run(
    intent: Intent,
    curriculum: Curriculum,
    llm: Optional[LLMClient] = None,
) -> Script:
    """Produce a tagged :class:`Script`."""
    llm = llm or LLMClient()
    if llm.mock:
        return _mock_script(intent, curriculum)

    user = (
        f"公式: {intent.formula_latex}\n核心概念: {curriculum.core_concept}\n"
        f"教学顺序: {curriculum.teaching_order}\n"
        f"前置: {[p.model_dump() for p in curriculum.inline_prerequisites]}"
    )
    fallback = _mock_script(intent, curriculum).model_dump()
    data = llm.complete_json(_SYSTEM, user, mock_fallback=fallback)
    segments = [ScriptSegment(**s) for s in data.get("segments", [])]
    if not segments:
        return _mock_script(intent, curriculum)
    return Script(segments=segments)
