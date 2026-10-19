"""対象ファイルの列挙、テストコードなどの除外、git の差分。"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
from dataclasses import dataclass, field

from . import globs

LANG_BY_EXT = {".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript", ".py": "python"}
EXCLUDED_DIRS = {
    "node_modules", ".git", ".venv", "venv", ".tox", "dist", "build", "out", "generated", "migrations",
    "__pycache__", ".next", ".nuxt", "coverage", ".mypy_cache", ".pytest_cache", ".turbo", "vendor",
    "site-packages", ".claude",
}
TEST_DIRS = {"tests", "test", "__tests__"}
_TEST_FILE = re.compile(r"(\.(spec|test)\.[cm]?[tj]sx?$)|(^test_.*\.py$)|(_test\.py$)|(^conftest\.py$)")


def language_of(path: str) -> str | None:
    if path.endswith(".d.ts"):
        return None
    return LANG_BY_EXT.get(os.path.splitext(path)[1])


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    if any(p in TEST_DIRS for p in parts[:-1]):
        return True
    return bool(_TEST_FILE.search(parts[-1]))


def is_excluded(path: str, extra: list[str]) -> bool:
    parts = path.split("/")
    if any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return True
    return globs.match_any(path, extra) if extra else False


def _git(root: pathlib.Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def is_git_repo(root: pathlib.Path) -> bool:
    return _git(root, "rev-parse", "--is-inside-work-tree") is not None


def list_source_files(root: pathlib.Path, exclude: list[str]) -> list[str]:
    """解析対象になりうるソースファイル（テストコードを含む）。パスはルートからの相対・スラッシュ区切り。"""
    listed = None
    if is_git_repo(root):
        out = _git(root, "ls-files", "--cached", "--others", "--exclude-standard")
        if out is not None:
            listed = [p for p in out.splitlines() if p and (root / p).is_file()]
    if listed is None:
        listed = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith("."))
            rel_dir = os.path.relpath(dirpath, root)
            for name in sorted(filenames):
                rel = name if rel_dir == "." else f"{rel_dir}/{name}".replace(os.sep, "/")
                listed.append(rel)
    return sorted(p for p in listed if language_of(p) and not is_excluded(p, exclude))


@dataclass
class DiffInfo:
    base: str
    merge_base: str
    changed: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    """ファイル → 変更行の範囲（新しい側の行番号）。新規ファイルは全体"""

    def touches(self, path: str, start: int, end: int) -> bool:
        for a, b in self.changed.get(path, []):
            if a <= end and start <= b:
                return True
        return False


class BaseNotFound(Exception):
    """明示した比較先とのマージベースが取れない。黙って全体に広げると、CI で既存の違反まで拾ってしまう。"""


def resolve_base(root: pathlib.Path, base: str | None) -> str | None:
    candidates = [base] if base else ["main", "origin/main", "master", "origin/master"]
    for ref in candidates:
        if _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") is not None:
            return ref
    return None


def git_diff(root: pathlib.Path, base: str | None) -> DiffInfo | None:
    ref = resolve_base(root, base)
    if ref is None:
        return None
    mb = (_git(root, "merge-base", "HEAD", ref) or "").strip()
    if not mb:
        return None
    info = DiffInfo(base=ref, merge_base=mb)
    out = _git(root, "diff", "--relative", "--unified=0", "--no-color", "--no-ext-diff", mb) or ""
    current = None
    for line in out.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
            if current is not None:
                info.changed.setdefault(current, [])
        elif line.startswith("@@") and current is not None:
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                if count > 0:
                    info.changed[current].append((start, start + count - 1))
    untracked = _git(root, "ls-files", "--others", "--exclude-standard") or ""
    for path in untracked.splitlines():
        if path:
            info.changed[path] = [(1, 10**9)]
    info.changed = {k: v for k, v in info.changed.items() if v}
    return info


def churn(root: pathlib.Path, days: int = 90) -> dict[str, int]:
    """直近 days 日のファイルごとの変更回数（コミット数）。"""
    out = _git(root, "log", f"--since={days}.days", "--name-only", "--format=", "--relative", "--no-renames")
    counts: dict[str, int] = {}
    for line in (out or "").splitlines():
        line = line.strip()
        if line:
            counts[line] = counts.get(line, 0) + 1
    return counts
