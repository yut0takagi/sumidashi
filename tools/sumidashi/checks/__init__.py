"""static チェックの登録簿と、チェックが受け取る文脈。

チェックは checks.yml の detection.implementation の名前で登録する。
判定規則は docs/static-checks.md に従う。
"""

from __future__ import annotations

import hashlib
import pathlib
import re
from dataclasses import dataclass, field
from typing import Callable

from ..frameworks import Ledger
from ..graph import Graph
from ..layers import LayerMap
from ..model import Module
from .common import DomainModel

REGISTRY: dict[str, Callable[["Ctx"], list[dict]]] = {}


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn

    return deco


@dataclass
class Ctx:
    root: pathlib.Path
    modules: dict[str, Module]
    layer_map: LayerMap
    ledger: Ledger
    graph: Graph
    domain: DomainModel
    checks: dict[str, dict] = field(default_factory=dict)
    """チェックID → checks.yml の定義"""

    def modules_in(self, *layers: str) -> list[Module]:
        return [m for p, m in sorted(self.modules.items()) if self.layer_map.layer_of(p) in layers]


def fingerprint(check_id: str, file: str, line_text: str) -> str:
    norm = re.sub(r"\s+", " ", line_text).strip()
    return hashlib.sha1(f"{check_id}|{file}|{norm}".encode("utf-8")).hexdigest()[:12]


def finding(
    ctx: Ctx,
    check_id: str,
    mod: Module,
    start: int,
    end: int | None = None,
    *,
    verdict: str = "violation",
    summary: str,
    facts: list[str] | None = None,
    suggestion: str | None = None,
    diff: str | None = None,
    fix_cost: str,
    impact: str,
    files_to_change: int = 1,
    severity_hint: dict | None = None,
    touches: list[tuple[str, int, int]] | None = None,
) -> dict:
    """static の指摘1件。重大度は checks.yml の既定値で、調整は finalize がかける。"""
    end = end or start
    check = ctx.checks.get(check_id, {})
    sev = (check.get("severity") or {}).get("default", "Medium")
    out = {
        "id": check_id,
        "philosophy": check.get("_philosophy"),
        "name": check.get("name"),
        "severity": sev,
        "location": {"file": mod.path, "start_line": start, "end_line": end},
        "evidence": {"summary": summary, "snippet": mod.snippet(start, end), "facts": facts or []},
        "principle": check.get("principle", ""),
        "suggestion": {"summary": suggestion or (check.get("fix_patterns") or [""])[0]},
        "verdict": verdict,
        "detection": "static",
        "tradeoff": {"fix_cost": fix_cost, "impact_if_ignored": impact, "files_to_change": files_to_change},
        "fingerprint": fingerprint(check_id, mod.path, mod.line_text(start)),
    }
    if diff:
        out["suggestion"]["diff"] = diff
    if severity_hint:
        out["severity_hint"] = severity_hint
    if touches:
        out["touches"] = [{"file": f, "start_line": a, "end_line": b} for f, a, b in touches]
    return out


def run_checks(ctx: Ctx, implementations: list[str]) -> tuple[list[dict], list[str]]:
    """(指摘, 実装が見つからなかった名前)"""
    # 登録のために各モジュールを読み込む
    from . import ca_bnd, ca_dep, ddd_ent, ddd_evt, ddd_rep, ddd_vo  # noqa: F401

    findings: list[dict] = []
    missing: list[str] = []
    for name in implementations:
        fn = REGISTRY.get(name)
        if fn is None:
            missing.append(name)
            continue
        findings.extend(fn(ctx))
    return findings, missing
