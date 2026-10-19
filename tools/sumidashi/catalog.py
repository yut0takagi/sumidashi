"""チェックの索引。generated/index.json を読み、なければ（古ければ）checks.yml から組み立てる。

索引の組み立ては tools/dev/build_knowledge.py もこのモジュールの build_index を使う。
"""

from __future__ import annotations

import json
import pathlib

import yaml

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX_PATH = PLUGIN_ROOT / "generated" / "index.json"
RESULTS_PATH = PLUGIN_ROOT / "evals" / "results" / "latest.json"
CONFLICTS_PATH = PLUGIN_ROOT / "skills" / "design-router" / "conflicts.yml"

PHILOSOPHY_ORDER = (
    "clean-architecture", "ddd-tactical", "adr", "glossary", "model-commonality", "business", "logic-placement",
)


def _sources() -> list[pathlib.Path]:
    files = sorted(PLUGIN_ROOT.glob("skills/*/checks.yml"))
    if CONFLICTS_PATH.is_file():
        files.append(CONFLICTS_PATH)
    return files


def build_index(plugin_root: pathlib.Path = PLUGIN_ROOT) -> dict:
    philosophies: dict[str, dict] = {}
    checks: dict[str, dict] = {}
    principles: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    for f in sorted(plugin_root.glob("skills/*/checks.yml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        ph = dict(data.get("philosophy") or {})
        pid = ph.get("id") or f.parent.name
        ph["skill"] = f.parent.name
        ph["file"] = f.relative_to(plugin_root).as_posix()
        ph["check_ids"] = []
        philosophies[pid] = ph
        for s in data.get("sources") or []:
            sources[s["id"]] = s
        for p in data.get("principles") or []:
            principles[p["id"]] = {**p, "philosophy": pid}
        for c in data.get("checks") or []:
            c = dict(c)
            c["_philosophy"] = pid
            checks[c["id"]] = c
            ph["check_ids"].append(c["id"])
    conflicts = {"rulings": [], "conflicts": []}
    cpath = plugin_root / "skills" / "design-router" / "conflicts.yml"
    if cpath.is_file():
        conflicts = yaml.safe_load(cpath.read_text(encoding="utf-8")) or conflicts
    # conflicts_with は対称にする（conflicts.yml の組と checks.yml の記載の和）
    for c in checks.values():
        c["conflicts_with"] = list(c.get("conflicts_with") or [])
    for pair in conflicts.get("conflicts") or []:
        a, b = pair["checks"]
        for x, y in ((a, b), (b, a)):
            if x in checks and y not in checks[x]["conflicts_with"]:
                checks[x]["conflicts_with"].append(y)
    for c in list(checks.values()):
        for other in c["conflicts_with"]:
            if other in checks and c["id"] not in checks[other]["conflicts_with"]:
                checks[other]["conflicts_with"].append(c["id"])
    return {
        "schema_version": 1,
        "philosophies": philosophies,
        "checks": checks,
        "principles": principles,
        "sources": sources,
        "rulings": conflicts.get("rulings") or [],
        "conflicts": conflicts.get("conflicts") or [],
    }


def load_index() -> dict:
    if INDEX_PATH.is_file():
        mtime = INDEX_PATH.stat().st_mtime
        if all(f.stat().st_mtime <= mtime for f in _sources()):
            try:
                return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return build_index()


def load_results() -> dict:
    """評価結果。checks.<ID> に precision・recall・passed などがある。"""
    if not RESULTS_PATH.is_file():
        return {}
    try:
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def gate(results: dict, check_id: str) -> dict | None:
    return (results.get("checks") or {}).get(check_id)
