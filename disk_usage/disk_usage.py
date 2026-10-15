#!/usr/bin/env python3
"""Show filesystem capacity and the largest immediate children of a path."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def human(size):
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def measure(path):
    # One du invocation avoids recounting every subtree for each child.
    result = subprocess.run(
        ["du", "-a", "-x", "-B1", "--max-depth=1", "--null", "--", str(path)],
        capture_output=True, check=False,
    )
    sizes = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        size, name = record.split(b"\t", 1)
        sizes[Path(name.decode(sys.getfilesystemencoding(), errors="surrogateescape"))] = int(size)
    if path not in sizes:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(message or "du 未返回目标路径的占用")
    children = [{"path": str(name), "bytes": size}
                for name, size in sizes.items() if name != path]
    children.sort(key=lambda item: item["bytes"], reverse=True)
    warning = result.stderr.decode(errors="replace").strip()
    return sizes[path], children, warning


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.home(),
                        help="要检查的文件或目录（默认：用户主目录）")
    parser.add_argument("--top", type=int, default=15,
                        help="显示最大的前 N 项；0 表示全部（默认：15）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top 不能为负数")
    path = args.path.expanduser().resolve()
    if not path.exists():
        parser.error(f"路径不存在：{path}")
    try:
        size, children, warning = measure(path)
        filesystem = shutil.disk_usage(path)
    except (OSError, RuntimeError) as exc:
        parser.error(str(exc))
    data = {
        "path": str(path), "bytes": size,
        "filesystem": {"total": filesystem.total, "used": filesystem.used,
                       "free": filesystem.free},
        "children": children[:args.top] if args.top else children,
        "warning": warning or None,
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    fs = data["filesystem"]
    print(f"文件系统：已用 {human(fs['used'])} / {human(fs['total'])}，可用 {human(fs['free'])}")
    print(f"目标占用：{human(size)}  {path}")
    if children:
        print("\n当前目录下占用最大的项目：")
        for item in data["children"]:
            print(f"  {human(item['bytes']):>10}  {item['path']}")
    if warning:
        print(f"\n注意：部分项目未能读取，结果可能不完整：\n{warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
