#!/usr/bin/env python3
"""Read-only disk and cache inventory for a Linux home directory."""

import argparse
import glob
import json
from pathlib import Path
import shutil
import subprocess


# These are exact cache locations, not whole application profiles.
RULES = (
    ("pip 下载缓存", ".cache/pip", "可清理", "python -m pip cache purge"),
    ("npm 包缓存", ".npm/_cacache", "可清理", "npm cache clean --force"),
    ("浏览器磁盘缓存", ".cache/google-chrome/Default/Cache", "可清理", "关闭 Chrome 后清理"),
    ("缩略图", ".cache/thumbnails", "可清理", "删除后会按需重建"),
    ("VS Code 扩展下载缓存", ".config/Code/CachedExtensionVSIXs", "可清理", "关闭 VS Code 后清理"),
    ("C/C++ 扩展索引", ".cache/vscode-cpptools", "可清理", "关闭 VS Code 后清理；重建索引耗时"),
    ("飞书普通缓存", ".cache/LarkShell", "可清理", "退出飞书后清理；会重新下载"),
    ("文件搜索索引", ".cache/tracker3", "需确认", "重建耗时；建议先检查索引服务"),
    ("Codex 运行时缓存", ".cache/codex-runtimes", "需确认", "可能触发重新安装或下载"),
    ("飞书离线网页缓存", ".config/LarkShell/aha/users/*/profile_explorer/Service Worker/CacheStorage", "需确认", "可能含离线内容；先在飞书内检查"),
)


def allocated_bytes(path):
    """Use du's allocated size; stay on one filesystem and do not follow links."""
    result = subprocess.run(
        ["du", "-s", "-x", "-B1", "--", str(path)],
        capture_output=True, text=True, check=True,
    )
    return int(result.stdout.split("\t", 1)[0])


def human(size):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024


def audit(home, top):
    usage = shutil.disk_usage(home)
    entries = []
    for label, pattern, status, note in RULES:
        for name in glob.glob(str(home / pattern)):
            path = Path(name)
            if path.is_symlink() or not path.is_dir():
                continue
            try:
                size = allocated_bytes(path)
            except (OSError, subprocess.CalledProcessError):
                continue
            entries.append({"name": label, "path": str(path), "bytes": size,
                            "status": status, "note": note})
    entries.sort(key=lambda item: item["bytes"], reverse=True)
    largest = []
    for path in home.iterdir():
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            size = allocated_bytes(path)
        except (OSError, subprocess.CalledProcessError):
            continue
        largest.append({"path": str(path), "bytes": size})
    largest.sort(key=lambda item: item["bytes"], reverse=True)
    return {"home": str(home), "filesystem": {"total": usage.total,
            "used": usage.used, "free": usage.free},
            "largest_home_directories": largest[:top], "cache_candidates": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="要检查的用户目录（默认：当前用户主目录）")
    parser.add_argument("--top", type=int, default=10, help="显示最大的目录数（默认：10）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    if not home.is_dir() or args.top < 0:
        parser.error("--home 必须是目录，--top 必须为非负数")
    data = audit(home, args.top)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    fs = data["filesystem"]
    print(f"磁盘：已用 {human(fs['used'])} / {human(fs['total'])}；可用 {human(fs['free'])}")
    print("\n用户目录占用：")
    for item in data["largest_home_directories"]:
        print(f"  {human(item['bytes']):>10}  {item['path']}")
    print("\n缓存候选（只读；大小为已分配空间估计，不能简单相加为实际可回收量）：")
    for item in data["cache_candidates"]:
        print(f"  {human(item['bytes']):>10}  [{item['status']}] {item['path']}")
        print(f"              {item['note']}")


if __name__ == "__main__":
    main()
