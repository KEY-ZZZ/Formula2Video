# Formula2Video 项目规划文档

**项目目标**：输入一段数学公式，自动输出一段 3B1B 风格的可视化解释视频，帮助理解公式。

**核心技术路线**：Manim（数学层）+ PixVerse（写实层，可选）+ AI 多 Agent 流水线。

**协同核心**：以 `Enriched Scene Spec` 为唯一信源（Single Source of Truth），上游打标签、下游各取所需，由轻量 Orchestrator 调度。

---

## 一、系统架构总览

```
                          用户输入：公式 / 自然语言
                                    │
        ╔═══════════════════════════▼═══════════════════════════╗
        ║  阶段 A：理解与规划层（串行）                          ║
        ║  Intent → Prerequisite → Curriculum → Script          ║
        ║                          → Storyboard → Scene Spec    ║
        ╚═══════════════════════════╤═══════════════════════════╝
                                    │ 产出 enriched_scene_spec.json
        ╔═══════════════════════════▼═══════════════════════════╗
        ║  阶段 B：素材生成层（并行）                            ║
        ║  Manim │ TTS │ Music │ PixVerse                        ║
        ╚═══════════════════════════╤═══════════════════════════╝
                                    │
        ╔═══════════════════════════▼═══════════════════════════╗
        ║  阶段 C：合成与审核层（串行）                          ║
        ║  FFmpeg Assembly → QA Review → Output                  ║
        ╚═══════════════════════════════════════════════════════╝

        贯穿全程：Pipeline Orchestrator（调度，不做内容决策）
```

---

## 二、模块拆解（10 个工作包）

每个模块 = 一个独立工作包（Work Package, WP），可独立开发、独立测试。

### 模块清单总表

| WP | 模块名 | 类型 | 输入 | 输出 | 关键技术 |
|----|--------|------|------|------|---------|
| WP1 | Intent Agent | LLM | 用户公式 | `intent.json` | GPT-4.1/Claude |
| WP2 | Prerequisite + Curriculum Agent | LLM | `intent.json` | `curriculum.json` | LLM + 极简即时原则 |
| WP3 | Script Agent（3B1B风格）| LLM | `curriculum.json` | `script.md`（带标签）| LLM + 风格 Skill |
| WP4 | Storyboard Agent | LLM | `script.md` | `storyboard.json` | LLM |
| WP5 | Scene Spec Agent | LLM | `storyboard.json` | `enriched_scene_spec.json` | LLM + Schema 校验 |
| WP6 | Manim Agent | LLM+渲染 | scene_spec.manim | `*.mp4`(透明背景) | Manim + RAG + 自修复 |
| WP7 | TTS Agent | API | scene_spec.tts | `*.wav` | ElevenLabs |
| WP8 | Music Agent | API | scene_spec.music_cue | `music.wav` | ElevenLabs Music/Suno |
| WP9 | PixVerse Agent | API | scene_spec.pixverse | `*.mp4` | 图生/文生视频 |
| WP10 | Assembly + QA Agent | 工具 | 所有素材 | `final.mp4` | FFmpeg + LLM 审核 |
| WP0 | Pipeline Orchestrator | 框架 | — | 调度全流程 | Python 异步框架 |

---

## 三、各模块详细规格

### WP1 — Intent Agent
**职责**：解析用户输入，明确公式语义、目标受众、教学目标。
**输入**：用户的公式字符串 / 自然语言。
**输出**：`intent.json`
```json
{
  "formula_latex": "f: \\mathbb{R}^n \\to \\mathbb{R}",
  "topic": "凸优化中的代价函数",
  "audience_level": "本科生",
  "learning_goal": "理解代价函数的几何直觉",
  "estimated_duration_s": 90
}
```
**验收标准**：能正确识别公式类型，输出合法 JSON。

---

### WP2 — Prerequisite + Curriculum Agent
**职责**：构建最小知识依赖，按教学顺序排列。
**核心约束（极简即时原则）**：
```
Prompt 硬约束：
"只识别理解本公式绝对必需的前置概念（通常 ≤3 个）。
 每个前置概念只允许用一句话内联解释，
 禁止生成独立的前置知识章节。
 如果某概念观众大概率已知，直接跳过。"
```
**输出**：`curriculum.json`
```json
{
  "core_concept": "代价函数把 n 维输入映射到一个标量",
  "inline_prerequisites": [
    {"concept": "ℝⁿ 表示 n 维空间", "one_liner": "就是有 n 个坐标的点"}
  ],
  "teaching_order": ["引入类比", "展示公式", "几何直觉", "总结"]
}
```

---

### WP3 — Script Agent（3B1B 风格蒸馏）★核心模块
**职责**：撰写带标签的脚本，是整个协同机制的起点。
**风格 Skill（作为 System Prompt 注入）**：

```markdown
## 3B1B Script Style Skill

S1 反直觉钩子：开头抛出意外问题，禁止"今天我们学习X"
S2 问题先于答案："如果你来设计，你会怎么做？"
S3 具体先于抽象：先用具体数字，再上升到符号
S4 视觉-语言同步：每句话配一个画面动作
S5 颜色语义化：每个变量全程固定一种颜色
S6 慢在关键：洞见处放慢，加停顿
S7 定义放最后：先建直觉，最后给正式定义
S8 禁用"显然/可证明"，必须展示"为什么"
```

**关键产出：内联标签**（这是协同的根基）：
```markdown
[PIXVERSE: object="photorealistic car on curved road"]
想象一辆车沿弯路行驶。
[MANIM]
我们用 f(x) 表示走这条路的总代价——
[INSIGHT]
最优路径不是最短的，而是让 f(x) 最小的。
[MANIM]
f: ℝⁿ → ℝ。
```

**输出**：`script.md`（含 `[MANIM]` / `[PIXVERSE]` / `[INSIGHT]` / `[HYBRID]` 标签）。

---

### WP4 — Storyboard Agent
**职责**：把脚本切分为场景节拍，每个节拍写高层视觉描述。
**输出**：`storyboard.json`
```json
{
  "scenes": [
    {
      "scene_id": "scene_01",
      "narration": "想象一辆车沿弯路行驶。",
      "visual_high_level": "写实汽车沿曲线公路移动",
      "visual_type": "pixverse",
      "pacing": "normal"
    }
  ]
}
```

---

### WP5 — Scene Spec Agent ★唯一信源生成者
**职责**：把高层分镜编译成机器可执行的精确规格，是所有下游 Agent 的共同语言。
**输出**：`enriched_scene_spec.json`（完整 Schema 见第四节）。
**关键机制**：输出必须通过 JSON Schema 校验，时间戳必须自洽（`timestamp_start_s` 累加 = 上一段时长）。

---

### WP6 — Manim Agent ★技术难点
**职责**：把 `scene_spec.manim` 编译成 Manim 代码并渲染。
**关键保障机制（三层）**：
1. **RAG**：从"黄金集"向量库检索相似的高质量 Manim 代码作为参考。
2. **静态审查**：AST 解析 + LaTeX 词项保留检查，渲染前拦截错误。
3. **自修复循环**：渲染失败 → 把报错回喂 LLM → 重新生成（最多 3 次）。

**Manim 代码必须遵守的规则**：
```
□ 每个 scene_id → 一个 Scene 类
□ 需要运镜 → 继承 MovingCameraScene
□ 坐标在 [-7,7]×[-4,4] 内
□ 每个 play() 的 run_time = scene_spec 里的 duration
□ wait_after_s → self.wait()
□ 变量颜色 = scene_spec 里指定的 color
□ 透明背景渲染（-t 参数），便于与 PixVerse 层叠加
```
**输出**：每个场景一个透明背景 `.mp4`。

---

### WP7 — TTS Agent
**职责**：按场景生成旁白音频。
**关键约束**：每段音频时长必须接近 `narration_duration_s`，否则反馈给 Scene Spec 调整 `run_time`（同步契约）。
**风格**：选一个沉稳、温和的声线（3B1B 风格不浮夸）。
**输出**：每场景一个 `.wav` + 实际时长元数据。

---

### WP8 — Music Agent
**职责**：生成**带时间轴标记**的整段配乐（不是单一循环背景乐）。
**输入**：通读全部 scene_spec 的 `music_cue` + `pacing` + `insight_moment` + `timestamp_start_s`。
**输出**：`music.wav` + 时间轴标记
```
00:00-00:12 calm    | 00:42-00:48 crescendo (INSIGHT) | 00:48+ settle
```
**混音规则**：相对旁白音量 15-25%。

---

### WP9 — PixVerse Agent
**职责**：仅处理 `visual_type == "pixverse"` 的场景。
**流程**：AI 生成静态图（Flux/MJ）→ PixVerse 图生视频 → 输出片段。
**硬约束**：**绝不放任何文字/公式**（PixVerse 文字会乱码）。文字一律走 Manim 叠加层。
**输出**：写实运动片段 `.mp4`。

---

### WP10 — Assembly + QA Agent
**职责**：按 `timestamp_start_s` 对齐所有素材，分层合成，再做质量审核。
**合成层次**：
```
底层：PixVerse 写实片段
中层：Manim 透明背景数学层（叠加）
音轨：旁白(100%) + 音乐(15-25%)
字幕：narration 文本
```
**QA 审核项**：数学准确性、音画同步偏差(±0.5s)、LaTeX 保真度、时长。
**输出**：`final.mp4`。

---

### WP0 — Pipeline Orchestrator
**职责**：纯调度，不做内容决策。
```
1. 串行跑 阶段A（WP1→WP5）
2. Scene Spec 完成后，并行启动 WP6/7/8/9
3. 全部完成 → 串行跑 WP10
4. 失败重试（指数退避，最多3次）
5. 全程产出可追溯的中间文件
```

---

## 四、核心数据契约：Enriched Scene Spec

这是整个项目的**接口标准**，所有人必须遵守。一个场景节拍：

```json
{
  "scene_id": "scene_04",
  "timestamp_start_s": 42.0,
  "narration": "最优路径不是最短的，而是让代价最小的。",
  "narration_duration_s": 4.0,

  "pacing": "slow",
  "insight_moment": true,
  "wait_after_s": 2.0,

  "visual_type": "manim",
  "pixverse": null,

  "manim": {
    "scene_class": "CostFunctionReveal",
    "camera_type": "MovingCameraScene",
    "camera_action": "zoom_in to formula",
    "objects": [
      {"id": "formula", "type": "MathTex",
       "content": "f: \\mathbb{R}^n \\to \\mathbb{R}", "color": "YELLOW"}
    ],
    "animation_sequence": [
      {"action": "Write", "target": "formula", "run_time": 2.0},
      {"action": "wait", "duration": 2.0}
    ]
  },

  "tts": {"text": "...", "pause_before_s": 0.3, "pause_after_s": 0.5},
  "music_cue": {"type": "revelation", "transition": "crescendo_then_settle",
                "volume_relative": 0.15}
}
```

**字段归属（谁读谁）**：

| 字段 | 归属 Agent |
|------|-----------|
| `manim.*`, `wait_after_s` | WP6 Manim |
| `tts.*`, `narration_duration_s` | WP7 TTS |
| `music_cue.*`, `pacing`, `insight_moment` | WP8 Music |
| `pixverse.*` | WP9 PixVerse |
| `timestamp_start_s` | WP10 Assembly |

---

## 五、分工建议（按技能分组）

| 分工角色 | 负责工作包 | 所需技能 | 工作量占比 |
|---------|-----------|---------|-----------|
| **Prompt/LLM 工程师 A** | WP1, WP2, WP3 | LLM Prompt 工程、3B1B 风格研究 | 25% |
| **Prompt/LLM 工程师 B** | WP4, WP5 | 结构化输出、Schema 设计 | 15% |
| **Manim 工程师** | WP6 | Python、Manim、RAG、AST | 25%（最难）|
| **音视频工程师** | WP7, WP8, WP10 | 音频 API、FFmpeg、混音 | 20% |
| **AI 视频工程师** | WP9 | 图像/视频生成 API、合成 | 5% |
| **架构/后端工程师** | WP0 + 数据契约 | 异步框架、流水线、测试 | 10% |

> **如果是单人/小团队**：按下面的里程碑顺序串行做，先打通 MVP 再加分支。

---

## 六、里程碑（建议开发顺序）

### M1 — 最小闭环 MVP（验证核心可行性）
```
WP1 → WP3（简化版，不打标签）→ WP6（纯Manim）→ WP10（仅拼接）
目标：给一个简单公式，能出一段纯 Manim 无声视频
```

### M2 — 加入声音
```
+ WP7 TTS + 音画同步契约
目标：视频有旁白，且音画对齐
```

### M3 — 风格与协同
```
+ WP3 完整 3B1B 风格 Skill + 标签
+ WP4 + WP5 完整 Enriched Scene Spec
+ WP0 Orchestrator 并行调度
目标：3B1B 风格、Spec 驱动、并行生成
```

### M4 — 全功能
```
+ WP8 Music + WP9 PixVerse + WP10 分层合成 + QA
目标：完整流程，含写实层和配乐
```

### M5 — 质量加固
```
+ WP6 RAG + 自修复循环
+ 全流程错误处理、重试、可追溯
目标：稳定、可规模化
```

---

## 七、技术栈

| 层 | 选型 |
|----|------|
| LLM | GPT-4.1 / Claude Sonnet 4 |
| 数学动画 | Manim Community Edition |
| TTS | ElevenLabs |
| 音乐 | ElevenLabs Music / Suno |
| 写实视频 | PixVerse（图生视频）+ Flux/MJ（出图）|
| 合成 | FFmpeg |
| 编排 | Python（asyncio / LangGraph / 自研 Orchestrator）|
| 数据契约 | JSON + Pydantic Schema 校验 |
| 向量库(RAG) | Chroma / FAISS（存 Manim 黄金集）|

---

## 八、关键风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Manim 代码生成出错/数学幻觉 | 高 | RAG + 静态审查 + 自修复（WP6 三层机制）|
| 音画不同步 | 高 | 同步契约：TTS 时长反馈调整 run_time |
| PixVerse 把公式渲染成乱码 | 中 | 硬约束：文字只走 Manim 层 |
| Scene Spec 时间戳不自洽 | 中 | Schema 校验 + 时间戳累加断言 |
| 引入 PixVerse 使复杂度暴涨 | 中 | M1-M3 不碰 PixVerse，最后才加 |

---

## 九、一句话总结

> 把项目拆成 **10 个工作包**，所有协同收敛到一份 **Enriched Scene Spec** 契约：**Script 阶段打标签**决定 PixVerse 与节奏，**Scene Spec 阶段固化**为结构化字段，**素材层并行**各取所需，**Orchestrator 只调度不决策**。先做 M1 纯 Manim 闭环，再逐步加声音、风格、写实层。
