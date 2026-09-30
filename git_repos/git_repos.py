#!/usr/bin/env python3
"""Scan directory trees for Git repositories and report local worktree status."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def find_repositories(roots: list[Path]):
    seen: set[Path] = set()
    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            print(f"警告：目录不存在，跳过：{root}", file=sys.stderr)
            continue
        if root.is_file():
            print(f"警告：不是目录，跳过：{root}", file=sys.stderr)
            continue
        for current, dirs, _files in os.walk(root, topdown=True, followlinks=False):
            path = Path(current)
            marker = path / ".git"
            if marker.is_dir() or marker.is_file():
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
                # A repository may contain nested repositories; continue walking.
                # Prune Git internals so object stores are never traversed.
                dirs[:] = [d for d in dirs if d != ".git"]
            else:
                dirs[:] = [d for d in dirs if d != ".git"]


def inspect(repo: Path) -> dict[str, str | int]:
    branch_result = git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    branch = branch_result.stdout.strip() or "(detached)"
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    if status.returncode:
        return {"branch": branch, "error": status.stderr.strip() or "git status 失败"}

    entries = status.stdout.splitlines()
    untracked = sum(1 for line in entries if line.startswith("??"))
    tracked = len(entries) - untracked
    staged = sum(1 for line in entries if line[0] in "MADRCU")
    unstaged = sum(1 for line in entries if len(line) > 1 and line[1] in "MADRCU")
    return {
        "branch": branch,
        "changed": len(entries),
        "tracked": tracked,
        "untracked": untracked,
        "staged": staged,
        "unstaged": unstaged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="扫描指定目录树中的 Git 仓库，并汇总未提交内容。"
    )
    parser.add_argument(
        "roots", nargs="*", type=Path,
        help="要扫描的目录；默认扫描当前用户主目录。",
    )
    args = parser.parse_args()
    roots = args.roots or [Path.home()]
    try:
        repos = sorted(find_repositories(roots), key=lambda p: os.fspath(p).casefold())
    except OSError as exc:
        print(f"扫描失败：{exc}", file=sys.stderr)
        return 2

    dirty_repos = 0
    print(f"{'仓库路径':<60} {'分支':<24} {'未提交':>6} {'已跟踪':>7} {'未跟踪':>7} {'暂存':>6} {'未暂存':>7}")
    print("-" * 126)
    for repo in repos:
        info = inspect(repo)
        label = os.fspath(repo)
        if "error" in info:
            print(f"{label:<60} {info['branch']:<24} 状态读取失败：{info['error']}")
            continue
        changed = int(info["changed"])
        dirty_repos += changed > 0
        print(
            f"{label:<60} {str(info['branch']):<24} {changed:>6} "
            f"{int(info['tracked']):>7} {int(info['untracked']):>7} {int(info['staged']):>6} "
            f"{int(info['unstaged']):>7}"
        )
    print(f"\n共发现 {len(repos)} 个仓库，其中 {dirty_repos} 个有未提交内容。")
    print("未提交数量按 porcelain 条目计数；暂存列是已暂存条目数。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
