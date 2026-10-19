"""ADR の読み込み。フロントマター、Nygard 形式、MADR、日本語の見出しを読む。"""

from __future__ import annotations

import pathlib
import re

import yaml

from . import globs

FALLBACK_DIRS = ("docs/adr", "doc/adr", "docs/architecture/decisions", "docs/decisions", "adr", "architecture/decisions")
_SKIP = re.compile(r"^(readme|index|template.*|adr-template.*|_.*)\.md$", re.IGNORECASE)
_CHECK_ID = re.compile(r"^[A-Z]+(-[A-Z]+)?-[0-9]{2}$")

_STATUS_WORDS = [
    ("superseded", ("superseded", "置き換え", "置換", "上書き")),
    ("deprecated", ("deprecated", "非推奨", "廃止")),
    ("rejected", ("rejected", "却下", "不採用")),
    ("accepted", ("accepted", "承認", "採用", "決定", "approved")),
    ("proposed", ("proposed", "提案", "draft", "検討中", "下書き")),
]
_SECTIONS = {
    "status": ("status", "ステータス", "状態"),
    "context": ("context", "context and problem statement", "背景", "コンテキスト", "文脈", "経緯"),
    "decision": ("decision", "decision outcome", "決定", "決定事項", "結論"),
    "consequences": ("consequences", "結果", "影響", "帰結"),
    "options": ("considered options", "options", "代替案", "検討した選択肢", "選択肢"),
}


def normalize_status(text: str | None) -> str:
    if not text:
        return "unknown"
    low = text.strip().lower()
    for status, words in _STATUS_WORDS:
        if any(low.startswith(w) or w in low.split()[:2] for w in words):
            return status
    for status, words in _STATUS_WORDS:
        if any(w in low for w in words):
            return status
    return "unknown"


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[,\n]", value) if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def _adr_id(path: pathlib.Path) -> str:
    m = re.match(r"^(?:adr[-_]?)?(\d+)", path.stem, re.IGNORECASE)
    return f"ADR-{int(m.group(1)):04d}" if m else path.stem


def _ref_ids(values: list[str]) -> list[str]:
    out = []
    for v in values:
        m = re.search(r"(\d+)", v)
        out.append(f"ADR-{int(m.group(1)):04d}" if m else v)
    return out


def _split_frontmatter(text: str) -> tuple[dict, str, bool]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                data = yaml.safe_load(text[3:end]) or {}
            except yaml.YAMLError:
                data = {}
            if isinstance(data, dict):
                body = text[end + 4 :]
                return {str(k).lower(): v for k, v in data.items()}, body.lstrip("\n"), True
    return {}, text, False


def _sections(body: str) -> dict[str, str]:
    """見出し（## か ###）ごとの本文。キーは _SECTIONS の名前。"""
    out: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            if current:
                out.setdefault(current, "\n".join(buf).strip())
            heading = re.sub(r"^\d+[.)]\s*", "", m.group(1)).strip().lower()
            current = next((k for k, names in _SECTIONS.items() if heading in names), None)
            buf = []
        elif current:
            buf.append(line)
    if current:
        out.setdefault(current, "\n".join(buf).strip())
    return out


def parse_adr(path: pathlib.Path, rel: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body, has_fm = _split_frontmatter(text)
    title_m = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    sections = _sections(body)
    status_text = meta.get("status")
    if not status_text and "status" in sections:
        status_text = next((ln.strip(" *-_") for ln in sections["status"].splitlines() if ln.strip()), None)
    if not status_text:
        m = re.search(r"^\s*[*-]?\s*(?:status|ステータス|状態)\s*[:：]\s*(.+)$", body, re.MULTILINE | re.IGNORECASE)
        status_text = m.group(1) if m else None
    status = normalize_status(str(status_text) if status_text else None)
    superseded_by = _ref_ids(_as_list(meta.get("superseded_by") or meta.get("superseded-by")))
    if status == "superseded" and not superseded_by and status_text:
        superseded_by = _ref_ids(re.findall(r"(?:ADR[-_ ]?)?\d{1,4}", str(status_text))[:1])
    if "options" in sections or "decision outcome" in body.lower():
        fmt = "madr"
    elif {"context", "decision"} <= set(sections):
        fmt = "nygard"
    elif has_fm and status != "unknown":
        fmt = "frontmatter"
    else:
        fmt = "unknown"
    scope = _as_list(meta.get("scope"))
    exempts = [e for e in _as_list(meta.get("exempts")) if e]
    problems = []
    bad = [e for e in exempts if not _CHECK_ID.match(e)]
    if bad:
        problems.append(f"exempts にチェックIDの形でないものがある: {', '.join(bad)}")
    if exempts and not scope:
        problems.append("exempts があるが scope がないため、例外には使わない")
    for key in ("context", "decision", "consequences"):
        if key not in sections or not sections[key].strip():
            problems.append(f"{key} の節がないか空")
    date = meta.get("date")
    return {
        "id": _adr_id(path),
        "file": rel,
        "title": title_m.group(1) if title_m else path.stem,
        "status": status,
        "status_text": str(status_text) if status_text else None,
        "date": str(date) if date else None,
        "format": fmt,
        "scope": scope,
        "exempts": [e for e in exempts if _CHECK_ID.match(e)],
        "supersedes": _ref_ids(_as_list(meta.get("supersedes"))),
        "superseded_by": superseded_by,
        "decision": (sections.get("decision") or "")[:2000],
        "usable_for_exemption": status == "accepted" and bool(scope) and bool(exempts),
        "problems": problems,
    }


def find_adr_dir(root: pathlib.Path, configured: str) -> str | None:
    if (root / configured).is_dir():
        return configured
    if configured != "docs/adr":
        return None
    for d in FALLBACK_DIRS:
        if (root / d).is_dir():
            return d
    return None


def load_adrs(root: pathlib.Path, configured: str) -> tuple[str | None, list[dict]]:
    d = find_adr_dir(root, configured)
    if d is None:
        return None, []
    out = []
    for p in sorted((root / d).rglob("*.md")):
        if _SKIP.match(p.name):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            out.append(parse_adr(p, rel))
        except OSError:
            continue
    return d, out


def exemption_for(adrs: list[dict], check_id: str, file: str) -> dict | None:
    """指摘を例外にする Accepted の ADR。複数当たれば番号の大きい（新しい）もの。"""
    hits = [
        a for a in adrs
        if a["usable_for_exemption"] and check_id in a["exempts"] and globs.match_any(file, a["scope"])
    ]
    return max(hits, key=lambda a: a["id"]) if hits else None
