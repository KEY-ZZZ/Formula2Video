# Formula2Video

输入一段数学公式，自动输出一段 3Blue1Brown 风格的可视化解释视频。

技术路线：Manim（数学层）+ PixVerse（写实层，可选）+ AI 多 Agent 流水线，
以 `Enriched Scene Spec` 为唯一信源（Single Source of Truth）。完整规划见
[`PROJECT_PLAN.md`](./PROJECT_PLAN.md)。

## 里程碑状态

**M1（最小闭环 MVP）已实现并验证**：

```
Intent -> Curriculum -> Script -> Scene Spec -> Manim (代码生成 + 渲染) -> Assembly (拼接)
```

## 安装

```bash
pip install -r requirements.txt   # 核心仅需 pydantic + pytest
```

`anthropic` / `openai` / `manim` 为可选依赖：未安装时流水线自动进入 **mock 模式**，
可离线跑通整条链路（不渲染真实视频）。

## 用法

```bash
python -m formula2video.cli "f(x)=x^2"
```

mock 模式下会打印场景数、估算总时长、已渲染场景数与最终视频路径，并把所有中间
产物（intent/curriculum/script/scene_spec/scenes.py/summary.json）落盘到工作目录。

设置环境变量启用真实 LLM 与输出目录：

```bash
export ANTHROPIC_API_KEY=...        # 或 OPENAI_API_KEY，并设 F2V_LLM_PROVIDER=openai
export F2V_WORK_DIR=./.f2v_work
export F2V_OUTPUT_DIR=./output
```

## 测试

```bash
python -m pytest tests/ -q
```
