"""Command-line entry point: ``python -m formula2video.cli \"<formula>\"``."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from formula2video import orchestrator


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="formula2video",
        description="Turn a math formula into a 3B1B-style explainer video.",
    )
    parser.add_argument("formula", help="The formula or natural-language input.")
    args = parser.parse_args(argv)

    result = orchestrator.run(args.formula)

    spec = result.scene_spec
    num_rendered = sum(1 for v in result.rendered.values() if v is not None)
    print(f"输入        : {args.formula}")
    print(f"场景数      : {len(spec.beats)}")
    print(f"总时长 (s)  : {spec.total_duration_s}")
    print(f"已渲染场景  : {num_rendered} / {len(result.rendered)}")
    print(f"最终视频    : {result.final_video if result.final_video else '（未生成）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
