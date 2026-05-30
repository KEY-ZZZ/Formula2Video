"""WP3 — Script Agent (3B1B 风格)。

把 Curriculum 转为带协同标签的脚本。M1 阶段产出基础 Script;
后续里程碑会丰富 PixVerse 标签与更细的视觉提示。
"""

from __future__ import annotations

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

SYSTEM = f"""你是 3Blue1Brown 风格的数学讲解脚本作者。

{THREE_B1B_STYLE_SKILL}

给定公式主题、教学目标和教学顺序, 输出 JSON:
{{
  "title": "视频标题",
  "segments": [
    {{
      "narration": "这一句旁白 (口语化, 一句话)",
      "visual_type": "manim" | "pixverse" | "hybrid",
      "insight_moment": true/false,
      "pacing": "fast" | "normal" | "slow",
      "pixverse_object": "若 visual_type 含 pixverse, 描述要生成的写实物体, 否则 null"
    }}
  ]
}}

规则:
- 公式、符号、图表一律 visual_type=manim (PixVerse 渲染不出文字)。
- 只有需要写实物体类比时才用 pixverse/hybrid。
- 关键洞见的那一两句设 insight_moment=true 且 pacing=slow。
只输出 JSON。"""


def run(
    intent: Intent,
    curriculum: Curriculum,
    llm: LLMClient | None = None,
) -> Script:
    """生成 3B1B 风格脚本。"""
    llm = llm or LLMClient()

    prereq_text = "; ".join(
        f"{p.concept}({p.one_liner})" for p in curriculum.inline_prerequisites
    ) or "无"

    user = (
        f"公式: {intent.formula_latex}\n"
        f"主题: {intent.topic}\n"
        f"教学目标: {intent.learning_goal}\n"
        f"核心概念: {curriculum.core_concept}\n"
        f"内联前置: {prereq_text}\n"
        f"教学顺序: {' -> '.join(curriculum.teaching_order)}\n"
        f"目标时长: {intent.estimated_duration_s} 秒"
    )

    # mock 占位: 用教学顺序生成简单脚本骨架
    mock = {
        "title": f"理解 {intent.topic}",
        "segments": [
            {
                "narration": f"(mock) {step}",
                "visual_type": "manim",
                "insight_moment": (i == len(curriculum.teaching_order) - 1),
                "pacing": "slow" if i == len(curriculum.teaching_order) - 1 else "normal",
                "pixverse_object": None,
            }
            for i, step in enumerate(curriculum.teaching_order)
        ],
    }

    data = llm.complete_json(SYSTEM, user, mock_fallback=mock)
    segments = [
        ScriptSegment(
            narration=s["narration"],
            visual_type=VisualType(s.get("visual_type", "manim")),
            insight_moment=bool(s.get("insight_moment", False)),
            pacing=Pacing(s.get("pacing", "normal")),
            pixverse_object=s.get("pixverse_object"),
        )
        for s in data["segments"]
    ]
    return Script(title=data["title"], segments=segments)
