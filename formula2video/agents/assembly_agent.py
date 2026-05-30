"""WP10 — Assembly Agent (M1 版: 仅拼接)。

M1 阶段只把各 manim 场景视频按顺序拼接成最终视频。
后续里程碑会扩展为分层合成 (PixVerse 底层 + Manim 中层 + 旁白/音乐音轨 + 字幕)。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from formula2video.config import config
from formula2video.schemas.contracts import SceneSpec


def concat_videos(clips: list[Path], output_path: Path) -> Path | None:
    """用 ffmpeg concat demuxer 拼接视频片段。失败返回 None。"""
    if not clips:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{c.resolve()}'" for c in clips), encoding="utf-8"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return output_path if output_path.exists() else None


def run(
    spec: SceneSpec,
    rendered: dict[str, Path | None],
    output_path: Path | None = None,
) -> Path | None:
    """按 scene 顺序拼接已渲染的片段。"""
    output_path = output_path or (config.output_dir / "final.mp4")
    clips = [
        rendered[beat.scene_id]
        for beat in spec.scenes
        if rendered.get(beat.scene_id) is not None
    ]
    return concat_videos([c for c in clips if c is not None], output_path)
