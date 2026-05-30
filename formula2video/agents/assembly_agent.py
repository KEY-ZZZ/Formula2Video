"""Assembly Agent (WP10) - concatenate rendered clips into the final video.

M1 only stitches the Manim clips together (no audio/PixVerse layering yet).
Uses the ffmpeg concat demuxer. Returns ``None`` when ffmpeg is missing,
when there is nothing to stitch, or when concatenation fails.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from formula2video.config import config
from formula2video.schemas.contracts import SceneSpec


def concat_videos(clips: List[Path], output_path: Path) -> Optional[Path]:
    """Concatenate ``clips`` (in order) into ``output_path`` via ffmpeg."""
    clips = [Path(c) for c in clips if c is not None]
    if not clips:
        return None
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = output_path.parent / "concat_list.txt"
    list_file.write_text(
        "".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not output_path.exists():
        return None
    return output_path


def run(
    scene_spec: SceneSpec,
    rendered: Dict[str, Optional[Path]],
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """Stitch rendered manim clips, ordered by the scene spec timeline."""
    if output_path is None:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = config.output_dir / "final.mp4"

    ordered: List[Path] = []
    for beat in scene_spec.beats:
        clip = rendered.get(beat.scene_id)
        if clip is not None:
            ordered.append(Path(clip))

    return concat_videos(ordered, Path(output_path))
