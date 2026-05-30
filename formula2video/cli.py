"""命令行入口。

用法:
    python -m formula2video.cli "f: \\mathbb{R}^n \\to \\mathbb{R}"
"""

from __future__ import annotations

import sys

from formula2video.orchestrator import run


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print('用法: python -m formula2video.cli "<公式或描述>"')
        return 1

    user_input = " ".join(argv)
    result = run(user_input)

    print(f"标题: {result.scene_spec.title}")
    print(f"场景数: {len(result.scene_spec.scenes)}")
    print(f"总时长(估): {result.scene_spec.total_duration_s}s")
    rendered_ok = sum(1 for v in result.rendered.values() if v)
    print(f"已渲染场景: {rendered_ok}/{len(result.scene_spec.scenes)}")
    if result.final_video:
        print(f"最终视频: {result.final_video}")
    else:
        print("最终视频: 未生成 (Manim/ffmpeg 不可用时正常, 代码与中间产物已落盘)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
