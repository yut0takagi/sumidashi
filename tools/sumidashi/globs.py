"""`**` を扱える glob の照合。ADR の scope と設定の layers・exclude で使う。"""

from __future__ import annotations

import functools
import re


def _norm(pattern: str) -> str:
    pattern = pattern.strip()
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return pattern


@functools.lru_cache(maxsize=512)
def _compile(pattern: str) -> re.Pattern:
    pattern = _norm(pattern)
    if pattern.endswith("/"):
        pattern += "**"
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i : i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern[i : i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{":
            end = pattern.find("}", i)
            if end == -1:
                out.append(re.escape(c))
            else:
                out.append("(?:" + "|".join(re.escape(x) for x in pattern[i + 1 : end].split(",")) + ")")
                i = end
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def match(path: str, pattern: str) -> bool:
    """パスが glob に当たるか。ディレクトリを指す glob（末尾が / か、ワイルドカードなし）は配下も含む。"""
    if _compile(pattern).match(path):
        return True
    plain = _norm(pattern).rstrip("/")
    if plain and not any(ch in plain for ch in "*?{"):
        return path == plain or path.startswith(plain + "/")
    return False


def match_any(path: str, patterns: list[str]) -> bool:
    return any(match(path, p) for p in patterns)
