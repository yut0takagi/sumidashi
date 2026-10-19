"""カバレッジの読み込み（lcov と Cobertura XML）。行ごとの実行回数を返す。"""

from __future__ import annotations

import os
import pathlib
import xml.etree.ElementTree as ET

AUTO_PATHS = ("coverage/lcov.info", "lcov.info", "coverage.xml", "coverage/cobertura-coverage.xml")


def _rel(root: pathlib.Path, path: str, base: pathlib.Path | None = None) -> str:
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = (base or root) / p
    try:
        return os.path.relpath(p.resolve(), root.resolve()).replace(os.sep, "/")
    except ValueError:
        return path


def _lcov(root: pathlib.Path, text: str) -> dict[str, dict[int, int]]:
    out: dict[str, dict[int, int]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = out.setdefault(_rel(root, line[3:].strip()), {})
        elif line.startswith("DA:") and current is not None:
            parts = line[3:].split(",")
            try:
                current[int(parts[0])] = current.get(int(parts[0]), 0) + int(float(parts[1]))
            except (IndexError, ValueError):
                continue
        elif line.startswith("end_of_record"):
            current = None
    return out


def _cobertura(root: pathlib.Path, text: str) -> dict[str, dict[int, int]]:
    out: dict[str, dict[int, int]] = {}
    tree = ET.fromstring(text)
    sources = [s.text.strip() for s in tree.iter("source") if s.text and s.text.strip()]
    for cls in tree.iter("class"):
        filename = cls.get("filename")
        if not filename:
            continue
        rel = None
        for src in sources or [str(root)]:
            cand = _rel(root, filename, pathlib.Path(src) if os.path.isabs(src) else root / src)
            if (root / cand).exists():
                rel = cand
                break
        rel = rel or _rel(root, filename)
        lines = out.setdefault(rel, {})
        for ln in cls.iter("line"):
            try:
                n, hits = int(ln.get("number")), int(ln.get("hits"))
            except (TypeError, ValueError):
                continue
            lines[n] = lines.get(n, 0) + hits
    return out


def load_coverage(root: pathlib.Path, configured: str | None) -> tuple[str | None, dict[str, dict[int, int]]]:
    paths = [configured] if configured else list(AUTO_PATHS)
    for p in paths:
        f = root / p
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            if text.lstrip().startswith("<"):
                return p, _cobertura(root, text)
            return p, _lcov(root, text)
        except (OSError, ET.ParseError):
            return p, {}
    return None, {}


def never_executed(cov: dict[str, dict[int, int]], file: str, start: int, end: int) -> bool:
    """範囲の中に計測対象の行があり、どれも一度も実行されていなければ True。ファイルが計測にないときは False。"""
    lines = cov.get(file)
    if not lines:
        return False
    measured = [lines[n] for n in range(start, end + 1) if n in lines]
    return bool(measured) and all(h == 0 for h in measured)
