"""WP2 — Prerequisite + Curriculum Agent。

构建最小知识依赖并排序。严格遵守极简即时原则: 前置概念 <= 3 个, 每个一句话。
"""

from __future__ import annotations

from formula2video.llm import LLMClient
from formula2video.schemas.contracts import Curriculum, InlinePrerequisite, Intent

SYSTEM = """你负责规划数学讲解视频的教学路径, 严格遵守"极简即时原则":
- 只识别理解本公式绝对必需的前置概念, 通常 <= 3 个。
- 每个前置概念只用一句话内联解释, 禁止展开成章节。
- 观众大概率已知的概念直接省略。

输出 JSON:
{
  "core_concept": "用一句话概括公式的核心含义",
  "inline_prerequisites": [{"concept": "概念名", "one_liner": "一句话解释"}],
  "teaching_order": ["步骤1", "步骤2", ...]
}
只输出 JSON。"""


def run(intent: Intent, llm: LLMClient | None = None) -> Curriculum:
    """生成教学路径。"""
    llm = llm or LLMClient()

    user = (
        f"公式: {intent.formula_latex}\n"
        f"主题: {intent.topic}\n"
        f"教学目标: {intent.learning_goal}\n"
        f"受众: {intent.audience_level}"
    )

    mock = {
        "core_concept": f"(mock) {intent.topic} 的核心思想",
        "inline_prerequisites": [],
        "teaching_order": ["引入直觉", "展示公式", "几何解释", "总结洞见"],
    }

    data = llm.complete_json(SYSTEM, user, mock_fallback=mock)
    return Curriculum(
        core_concept=data["core_concept"],
        inline_prerequisites=[
            InlinePrerequisite(**p) for p in data.get("inline_prerequisites", [])
        ],
        teaching_order=data["teaching_order"],
    )
