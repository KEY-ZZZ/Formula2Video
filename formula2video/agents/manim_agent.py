"""WP6 — Manim Agent。

把结构化的 ManimSpec 确定性地编译成 Manim Python 代码, 再调用 manim 渲染。

设计选择: M1 用"确定性代码生成"而非 LLM 直接写代码。
因为 ManimSpec 已经是结构化的 (对象 + 动画序列), 直接模板化生成
比让 LLM 写整段代码更可靠 (避免语法/数学幻觉)。
后续 M5 再叠加 LLM + RAG + 自修复来处理复杂场景。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from formula2video.config import config
from formula2video.schemas.contracts import ManimAction, ManimObject, ManimSpec, SceneSpec

# 对象类型 -> Manim 构造代码的映射
_OBJECT_TEMPLATES = {
    "MathTex": 'MathTex(r"{content}", color={color})',
    "Tex": 'Tex(r"{content}", color={color})',
    "Text": 'Text("{content}", color={color})',
    "Arrow": "Arrow(LEFT, RIGHT, color={color})",
    "Axes": "Axes()",
    "Dot": "Dot(color={color})",
    "Circle": "Circle(color={color})",
}


def _obj_code(obj: ManimObject) -> str:
    """生成单个 Mobject 的构造代码。"""
    template = _OBJECT_TEMPLATES.get(obj.type, 'Text("{content}", color={color})')
    safe_content = obj.content.replace('"', '\\"')
    return template.format(content=safe_content, color=obj.color)


def _action_code(action: ManimAction, known_ids: set[str]) -> str:
    """生成单个动画动作的代码。"""
    if action.action == "wait":
        return f"self.wait({action.duration or action.run_time})"
    if action.target and action.target in known_ids:
        return (
            f"self.play({action.action}(self.{action.target}), "
            f"run_time={action.run_time})"
        )
    # 无明确 target 的兜底
    return f"self.wait({action.run_time})"


def generate_scene_code(spec: ManimSpec, bg_color: str) -> str:
    """把一个 ManimSpec 编译成一段 Scene 类代码。"""
    known_ids = {o.id for o in spec.objects}
    lines: list[str] = []
    lines.append(f"class {spec.scene_class}({spec.camera_type.value}):")
    lines.append("    def construct(self):")
    lines.append(f'        self.camera.background_color = "{bg_color}"')

    # 构造并放置对象
    for i, obj in enumerate(spec.objects):
        lines.append(f"        self.{obj.id} = {_obj_code(obj)}")
        if i > 0:
            # 简单纵向排布, 避免重叠
            prev = spec.objects[i - 1].id
            lines.append(f"        self.{obj.id}.next_to(self.{prev}, DOWN, buff=0.5)")

    # 动画序列
    if spec.animation_sequence:
        for action in spec.animation_sequence:
            lines.append(f"        {_action_code(action, known_ids)}")
    else:
        lines.append("        self.wait(1)")

    return "\n".join(lines)


def generate_module(spec: SceneSpec) -> str:
    """把整个 SceneSpec 里所有 manim 场景生成为一个 .py 模块。"""
    parts = ["from manim import *", ""]
    for beat in spec.scenes:
        if beat.manim is not None:
            parts.append(generate_scene_code(beat.manim, config.background_color))
            parts.append("")
    return "\n".join(parts)


def render_scene(
    module_path: Path,
    scene_class: str,
    out_dir: Path,
    quality: str | None = None,
    transparent: bool = True,
) -> Path | None:
    """调用 manim CLI 渲染单个场景, 返回输出视频路径 (失败返回 None)。"""
    quality = quality or config.manim_quality
    cmd = [
        "manim",
        f"-q{quality}",
        "--media_dir", str(out_dir),
        str(module_path),
        scene_class,
    ]
    if transparent:
        cmd.insert(1, "-t")  # 透明背景, 便于与 PixVerse 层叠加
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    # manim 输出路径约定
    hits = list(out_dir.rglob(f"{scene_class}.mp4")) + list(
        out_dir.rglob(f"{scene_class}.mov")
    )
    return hits[0] if hits else None


def run(spec: SceneSpec, work_dir: Path | None = None) -> dict[str, Path | None]:
    """生成代码并渲染所有 manim 场景。

    返回 {scene_id: 渲染视频路径或 None}。
    无 manim 环境时, 代码仍会落盘, 视频路径为 None。
    """
    work_dir = work_dir or config.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    module_code = generate_module(spec)
    module_path = work_dir / "scenes.py"
    module_path.write_text(module_code, encoding="utf-8")

    results: dict[str, Path | None] = {}
    for beat in spec.scenes:
        if beat.manim is None:
            results[beat.scene_id] = None
            continue
        results[beat.scene_id] = render_scene(
            module_path, beat.manim.scene_class, work_dir
        )
    return results
