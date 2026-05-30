"""Manim Agent (WP6) - deterministically compile ManimSpec into Manim code.

The LLM never writes code here. We translate the structured ``ManimSpec``
into a single ``Scene`` subclass per beat. The emitted module always starts
with ``from manim import *`` and is guaranteed to be valid Python (it is
checked with ``compile()`` before being returned).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional

from formula2video.config import config
from formula2video.schemas.contracts import ManimSpec, SceneSpec

_INDENT = " " * 8

# Manim color names we pass through verbatim; everything else becomes a string.
_KNOWN_COLORS = {
    "WHITE", "BLACK", "RED", "GREEN", "BLUE", "YELLOW", "ORANGE",
    "PURPLE", "PINK", "TEAL", "GOLD", "MAROON", "GRAY", "GREY",
}


def _color_literal(color: Optional[str]) -> Optional[str]:
    """Render a color as a Manim constant or a hex string literal."""
    if not color:
        return None
    c = color.strip()
    if c.upper() in _KNOWN_COLORS:
        return c.upper()
    return repr(c)  # e.g. '#FF0000'


def _object_line(obj) -> str:
    """Emit a single mobject construction line, e.g. ``caption = Text(...)``."""
    color = _color_literal(obj.color)
    args = [repr(obj.content)]
    if color:
        args.append(f"color={color}")
    return f"{_INDENT}{obj.id} = {obj.type}({', '.join(args)})"


def _action_line(action, object_ids) -> str:
    """Emit a single animation/wait line."""
    if action.action == "wait":
        duration = action.duration if action.duration is not None else 0.5
        return f"{_INDENT}self.wait({float(duration)})"
    if action.target and action.target in object_ids:
        return (
            f"{_INDENT}self.play({action.action}({action.target}), "
            f"run_time={float(action.run_time)})"
        )
    # Action with no valid target: still emit a harmless wait to stay valid.
    return f"{_INDENT}self.wait({float(action.run_time) or 0.5})"


def generate_scene_code(spec: ManimSpec, bg_color: str) -> str:
    """Generate the source for one ``Scene`` subclass from a ManimSpec."""
    base = spec.camera_type.value if spec.camera_type else "Scene"
    lines = [f"class {spec.scene_class}({base}):", "    def construct(self):"]
    lines.append(f"{_INDENT}self.camera.background_color = {repr(bg_color)}")

    object_ids = {o.id for o in spec.objects}
    if spec.objects:
        for obj in spec.objects:
            lines.append(_object_line(obj))
    else:
        # Always have at least one mobject so the scene is non-empty.
        object_ids = {"placeholder"}
        lines.append(f"{_INDENT}placeholder = Text('...')")

    if spec.animation_sequence:
        for action in spec.animation_sequence:
            lines.append(_action_line(action, object_ids))
    else:
        first = next(iter(object_ids))
        lines.append(f"{_INDENT}self.play(Write({first}), run_time=1.5)")
        lines.append(f"{_INDENT}self.wait(0.5)")

    return "\n".join(lines)


def generate_module(scene_spec: SceneSpec, bg_color: Optional[str] = None) -> str:
    """Generate a full Manim module: one Scene class per manim-bearing beat."""
    bg_color = bg_color if bg_color is not None else config.bg_color
    parts = [
        '"""Auto-generated Manim scenes for Formula2Video. Do not edit by hand."""',
        "from manim import *",
        "",
    ]
    for beat in scene_spec.beats:
        if beat.manim is None:
            continue
        parts.append(generate_scene_code(beat.manim, bg_color))
        parts.append("")

    module = "\n".join(parts)
    # Hard guarantee: the emitted code must be valid Python.
    compile(module, "<generated_scenes>", "exec")
    return module


def render_scene(
    module_path: Path,
    scene_class: str,
    output_dir: Path,
    quality: str = "l",
) -> Optional[Path]:
    """Render one scene via the Manim CLI with a transparent background.

    Returns the produced ``.mov``/``.mp4`` path, or ``None`` when Manim is
    not installed or rendering fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "manim", "render",
        f"-q{quality}",
        "-t",  # transparent background
        "--media_dir", str(output_dir),
        str(module_path),
        scene_class,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    # Locate the rendered movie (transparent renders are .mov).
    for ext in ("*.mov", "*.mp4"):
        matches = sorted(output_dir.rglob(ext))
        for m in matches:
            if scene_class in m.name or m.stem == scene_class:
                return m
        if matches:
            return matches[-1]
    return None


def run(scene_spec: SceneSpec, work_dir: Optional[Path] = None) -> Dict[str, Optional[Path]]:
    """Compile and render every manim-bearing beat.

    Always writes ``scenes.py`` to ``work_dir`` (code lands on disk even when
    no Manim environment is present). Returns a mapping of scene_id -> rendered
    video path (or ``None`` when rendering was skipped/failed).
    """
    work_dir = Path(work_dir) if work_dir is not None else config.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    module_src = generate_module(scene_spec)
    module_path = work_dir / "scenes.py"
    module_path.write_text(module_src, encoding="utf-8")

    rendered: Dict[str, Optional[Path]] = {}
    for beat in scene_spec.beats:
        if beat.manim is None:
            continue
        rendered[beat.scene_id] = render_scene(
            module_path, beat.manim.scene_class, work_dir / "render"
        )
    return rendered
