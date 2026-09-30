#!/usr/bin/env python3
"""从摄像头采集指定张数的照片。"""

import argparse
from datetime import datetime
import math
from pathlib import Path
import sys
import time


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def nonnegative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是非负整数") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return number


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是大于 0 的数") from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("必须是大于 0 的有限数")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用 OpenCV 从摄像头拍照或按帧率连续采集")
    parser.add_argument("--camera", type=nonnegative_int, default=0, help="摄像头编号，默认 0")
    parser.add_argument("--count", type=positive_int, default=1, help="保存张数，默认 1")
    parser.add_argument("--fps", type=positive_float, default=1.0, help="采集目标帧率，默认 1 帧/秒")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="保存目录，默认工具目录下的 output")
    return parser.parse_args()


def capture(args: argparse.Namespace) -> int:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("缺少 OpenCV，请先安装：python3 -m pip install opencv-python") from exc

    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(f"无法打开摄像头 {args.camera}，请检查编号、连接和访问权限")

    saved = 0
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        start = time.monotonic()
        for index in range(args.count):
            delay = start + index / args.fps - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError(f"读取第 {index + 1} 帧失败，已保存 {saved} 张")

            target = args.output / f"capture_{run_id}_{index + 1:04d}.jpg"
            if target.exists():
                raise RuntimeError(f"文件已存在，停止以避免覆盖：{target}")
            if not cv2.imwrite(str(target), frame):
                raise RuntimeError(f"保存失败：{target}")
            saved += 1
            print(f"[{saved}/{args.count}] {target}", flush=True)
    finally:
        camera.release()

    return saved


def main() -> int:
    args = parse_args()
    try:
        saved = capture(args)
    except (OSError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已中断拍摄。", file=sys.stderr)
        return 130
    print(f"完成：保存 {saved} 张到 {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
