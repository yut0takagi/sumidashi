"""finalize: static と LLM の指摘をまとめ、重大度の調整・統合・衝突裁定・厳しさ・採点をかける。

処理順は docs/architecture.md「finalize の処理順」のとおり。
"""

from __future__ import annotations

import copy
import datetime as dt
import math
import pathlib

from . import VERSION, adr, catalog, coverage, files
from .checks import fingerprint

SEVERITIES = ("Info", "Low", "Medium", "High")
WEIGHTS = {"High": 3.0, "Medium": 1.5, "Low": 0.5, "Info": 0.0}
CORRECTNESS_CHECKS = {"DDD-AGG-01", "DDD-AGG-02", "DDD-VO-01"}
AGGREGATE_LIMIT = 5
CHURN_DAYS = 90
CHURN_TOP = 0.10
_REQUIRED = ("id", "severity", "location", "evidence", "principle", "suggestion", "verdict", "detection", "tradeoff")


def _rank(sev: str) -> int:
    return SEVERITIES.index(sev) if sev in SEVERITIES else 2


def _shift(f: dict, steps: int, rule: str, reason: str, cap: str = "High", floor: str = "Info") -> None:
    cur = f["severity"]
    new_rank = max(_rank(floor), min(_rank(cap), _rank(cur) + steps))
    new = SEVERITIES[new_rank]
    if new != cur:
        f.setdefault("severity_trace", []).append({"rule": rule, "from": cur, "to": new, "reason": reason})
        f["severity"] = new


def _set(f: dict, sev: str, rule: str, reason: str) -> None:
    if f["severity"] != sev:
        f.setdefault("severity_trace", []).append({"rule": rule, "from": f["severity"], "to": sev, "reason": reason})
        f["severity"] = sev


def _overlap(a: dict, b: dict) -> bool:
    la, lb = a["location"], b["location"]
    return la["file"] == lb["file"] and la["start_line"] <= lb["end_line"] and lb["start_line"] <= la["end_line"]


def _status(f: dict, status: str, reason: str) -> None:
    f["status"] = status
    f["status_reason"] = reason


# ------------------------------------------------------------------ LLM の指摘の受け入れ
def _normalize_llm(f: dict, index: dict, active: dict[str, dict], candidates: dict, root: pathlib.Path) -> tuple[dict | None, str | None]:
    missing = [k for k in _REQUIRED if k not in f]
    if missing:
        return None, f"必須の項目がない（{', '.join(missing)}）"
    cid = f["id"]
    if cid not in active:
        return None, f"{cid} は今回走らせたチェックではない"
    check = index["checks"].get(cid, {})
    a = active[cid]
    if a["detection"] == "static":
        return None, f"{cid} は static のチェックで、解析器が確定する"
    if f.get("detection") != a["detection"]:
        f["detection"] = a["detection"]
    if a["detection"] == "hybrid":
        cands = candidates.get(cid) or []
        if not any(_overlap(f, {"location": c["location"]}) for c in cands if "location" in c):
            return None, f"{cid} は hybrid で、facts.json の候補にない箇所を指している"
    if f["severity"] not in SEVERITIES:
        f["severity"] = check.get("severity", {}).get("default", "Medium")
    if f["verdict"] not in ("violation", "borderline"):
        return None, f"verdict が {f['verdict']!r}"
    loc = f["location"]
    try:
        loc["start_line"] = int(loc["start_line"])
        loc["end_line"] = int(loc.get("end_line") or loc["start_line"])
    except (KeyError, TypeError, ValueError):
        return None, "location の行番号が読めない"
    f.setdefault("philosophy", check.get("_philosophy"))
    f.setdefault("name", check.get("name"))
    if not f.get("fingerprint"):
        try:
            lines = (root / loc["file"]).read_text(encoding="utf-8", errors="replace").splitlines()
            text = lines[loc["start_line"] - 1] if 0 < loc["start_line"] <= len(lines) else ""
        except OSError:
            text = ""
        f["fingerprint"] = fingerprint(cid, loc["file"], text)
    return f, None


def _in_target(f: dict, target: dict) -> bool:
    loc = f["location"]
    if target.get("mode") == "diff":
        ranges = (target.get("changed_lines") or {}).get(loc["file"], [])
        return any(a <= loc["end_line"] and loc["start_line"] <= b for a, b in ranges)
    if target.get("mode") == "paths":
        return any(p in (".", "") or loc["file"] == p or loc["file"].startswith(p + "/") for p in target["paths"])
    return True


# ------------------------------------------------------------------ 変更頻度
def _churn_hot(root: pathlib.Path) -> set[str]:
    counts = files.churn(root, CHURN_DAYS)
    if not counts:
        return set()
    values = sorted(counts.values(), reverse=True)
    k = max(1, math.ceil(len(values) * CHURN_TOP))
    threshold = max(values[k - 1], 2)
    return {p for p, n in counts.items() if n >= threshold}


# ------------------------------------------------------------------ 衝突裁定
def _rule_decides(rule: str, a: dict, b: dict) -> int:
    """a が勝てば 1、b が勝てば -1、決まらなければ 0。"""
    if rule == "R1-HIGH":
        return (_rank(a["severity"]) > _rank(b["severity"])) - (_rank(a["severity"]) < _rank(b["severity"]))
    if rule == "R2-DEPENDENCY":
        da, db = a["id"].startswith("CA-DEP-"), b["id"].startswith("CA-DEP-")
        structural = ("DDD-AGG-", "MDL-")
        if da and b["id"].startswith(structural):
            return 1
        if db and a["id"].startswith(structural):
            return -1
        return 0
    if rule == "R3-FEWER-FILES":
        fa = a["tradeoff"].get("files_to_change")
        fb = b["tradeoff"].get("files_to_change")
        if fa is None or fb is None or fa == fb:
            return 0
        return 1 if fa < fb else -1
    return 0


def finalize(facts: dict, llm_findings: list[dict] | None = None, *, today: dt.date | None = None) -> dict:
    root = pathlib.Path(facts["root"])
    index = catalog.load_index()
    cfg = facts.get("config") or {}
    target = facts.get("target") or {"mode": "all"}
    active = {a["id"]: a for a in facts.get("active_checks", [])}
    applicability = facts.get("applicability") or {}
    notes: list[str] = []

    findings: list[dict] = []
    for f in facts.get("findings", []):
        f = copy.deepcopy(f)
        f["severity_default"] = f["severity"]
        findings.append(f)
    rejected = 0
    for f in llm_findings or []:
        f = copy.deepcopy(f)
        f, why = _normalize_llm(f, index, active, facts.get("candidates") or {}, root)
        if f is None:
            rejected += 1
            notes.append(f"LLM の指摘を1件受け入れなかった: {why}")
            continue
        if not _in_target(f, target):
            continue
        f["severity_default"] = (index["checks"].get(f["id"], {}).get("severity") or {}).get("default", f["severity"])
        if target.get("mode") == "diff":
            f["in_diff"] = True
        findings.append(f)
    for f in findings:
        f.setdefault("severity_trace", [])
        f["status"] = "reported"

    # 1. 適用判定
    kept = []
    for f in findings:
        app = applicability.get(f.get("philosophy") or "", {"mode": "full", "severity_shift": 0})
        if app["mode"] == "off":
            continue
        if app["mode"] == "dep-only" and not f["id"].startswith("CA-DEP-"):
            continue
        if app["mode"] == "ent-vo-only" and not f["id"].startswith(("DDD-ENT-", "DDD-VO-")):
            continue
        kept.append(f)
    findings = kept

    # 2. チェック固有の escalate・deescalate（static は解析器が条件を確かめて severity_hint に残す）
    #    適用判定の「1段下げる」は相対の調整なので、固有ルールで決まった重大度に後から掛ける
    for f in findings:
        hint = f.pop("severity_hint", None)
        if hint:
            _set(f, hint["to"], f"check:{hint['rule']}", hint.get("reason", ""))
        shift = applicability.get(f.get("philosophy") or "", {}).get("severity_shift")
        if shift:
            _shift(f, shift, "applicability", "層マップが推定できないため1段下げる")

    # 3. ADR による例外
    adrs = facts.get("adrs") or []
    for f in findings:
        a = adr.exemption_for(adrs, f["id"], f["location"]["file"])
        if a is None:
            continue
        f["adr"] = a["id"]
        if f["id"] in CORRECTNESS_CHECKS:
            if _rank(f["severity"]) > _rank("Low"):
                _set(f, "Low", "adr", f"{a['id']} で例外（正しさに関わるチェックのため Low に留める）")
        else:
            _set(f, "Info", "adr", f"{a['id']} で例外")

    # 4. business 台帳（v1.5）: v0.1 では何もしない

    # 5. 変更頻度とカバレッジ
    hot = _churn_hot(root) if files.is_git_repo(root) else set()
    cov_path, cov = coverage.load_coverage(root, cfg.get("coverage_path"))
    for f in findings:
        if f.get("adr"):
            continue
        loc = f["location"]
        if loc["file"] in hot:
            _shift(f, 1, "churn", f"直近{CHURN_DAYS}日の変更回数が上位{int(CHURN_TOP * 100)}%のファイル")
        if cov and coverage.never_executed(cov, loc["file"], loc["start_line"], loc["end_line"]):
            _shift(f, 1, "coverage", f"該当行がテストで一度も実行されていない（{cov_path}）")

    # 6. also_accept による重複の統合
    for f in findings:
        if f["status"] != "reported":
            continue
        also = set(index["checks"].get(f["id"], {}).get("also_accept") or [])
        if not also:
            continue
        primary = next(
            (g for g in findings if g is not f and g["status"] == "reported" and g["id"] in also and _overlap(f, g)), None
        )
        if primary is not None:
            _status(f, "merged", f"{primary['id']} と同じ箇所の指摘のため {primary['id']} にまとめた")

    # 7. 衝突裁定
    pairs = {}
    for c in index.get("conflicts") or []:
        a, b = c["checks"]
        pairs[frozenset((a, b))] = c.get("ruling")
    for i, a in enumerate(findings):
        for b in findings[i + 1 :]:
            if a["status"] != "reported" or b["status"] != "reported":
                continue
            conflicts = set(index["checks"].get(a["id"], {}).get("conflicts_with") or [])
            if b["id"] not in conflicts or not _overlap(a, b):
                continue
            decided, rule_used = 0, None
            for rule in ("R1-HIGH", "R2-DEPENDENCY", "R3-FEWER-FILES"):
                decided = _rule_decides(rule, a, b)
                if decided:
                    rule_used = rule
                    break
            if not decided:
                notes.append(f"{a['id']} と {b['id']}（{a['location']['file']}）の衝突は裁定できず、両方を残した")
                continue
            winner, loser = (a, b) if decided > 0 else (b, a)
            _status(loser, "held", f"{winner['id']} と衝突し、{rule_used} で {winner['id']} を採った")
            loser["held_by"] = {"id": winner["id"], "fingerprint": winner.get("fingerprint"), "ruling": rule_used}

    # 8. borderline は要確認へ（strict なら指摘一覧）
    strictness = cfg.get("effective_strictness") or cfg.get("strictness") or "standard"
    for f in findings:
        if f["status"] == "reported" and f["verdict"] == "borderline" and strictness != "strict":
            _status(f, "needs_review", "判定に必要な情報がコードの外にある（borderline）")

    # 9. 厳しさ
    if strictness == "lenient":
        for f in findings:
            if f["status"] == "reported" and f["severity"] in ("Low", "Info"):
                _status(f, "filtered", "strictness が lenient のため Low・Info を出さない")

    # 10. 同種の違反のまとめ
    by_id: dict[str, list[dict]] = {}
    for f in findings:
        if f["status"] == "reported":
            by_id.setdefault(f["id"], []).append(f)
    aggregated = []
    for cid, group in sorted(by_id.items()):
        group.sort(key=lambda f: (-_rank(f["severity"]), f["location"]["file"], f["location"]["start_line"]))
        if len(group) > AGGREGATE_LIMIT:
            rest = group[AGGREGATE_LIMIT:]
            for f in rest:
                _status(f, "aggregated", f"{cid} の同種の違反をまとめた")
            aggregated.append({
                "id": cid,
                "count": len(rest),
                "locations": [f"{f['location']['file']}:{f['location']['start_line']}" for f in rest],
            })

    # 11. 採点
    scores = {}
    for pid, app in sorted(applicability.items()):
        if app["mode"] == "off":
            continue
        # 走らせたチェックがない思想は、見ていないので点を付けない（満点に見えてしまう）
        if not any(a["philosophy"] == pid for a in active.values()) and not any(
                f.get("philosophy") == pid for f in findings):
            continue
        counted = [f for f in findings if f.get("philosophy") == pid and f["status"] in ("reported", "aggregated")]
        deductions = sorted(
            ({"id": f["id"], "file": f["location"]["file"], "line": f["location"]["start_line"],
              "severity": f["severity"], "weight": WEIGHTS[f["severity"]]} for f in counted if WEIGHTS[f["severity"]]),
            key=lambda d: (-d["weight"], d["file"], d["line"]),
        )
        total = sum(d["weight"] for d in deductions)
        score = max(0.0, 10.0 - total)
        # gain はその1件だけを直したときに上がる点。直しても減点が10点以上残るなら下限0点のままで 0 になるので、
        # 重い順に直していったときの点数（score_after）も添える。点が動き始めてから10件までを残す
        gains, rest, first_up = [], total, None
        for i, d in enumerate(deductions):
            rest -= d["weight"]
            after = round(max(0.0, 10.0 - rest), 1)
            if first_up is None and after > score:
                first_up = i
            gains.append({**d, "gain": round(max(0.0, 10.0 - (total - d["weight"])) - score, 2), "score_after": after})
        keep = (first_up if first_up is not None else 0) + 10
        scores[pid] = {"score": round(score, 1), "total_deduction": round(total, 1), "deductions": deductions,
                       "improvements": gains[:keep]}

    findings.sort(key=lambda f: (-_rank(f["severity"]), f["location"]["file"], f["location"]["start_line"], f["id"]))
    counts = {s: 0 for s in reversed(SEVERITIES)}
    for f in findings:
        if f["status"] in ("reported", "aggregated"):
            counts[f["severity"]] += 1
    by_status: dict[str, int] = {}
    for f in findings:
        by_status[f["status"]] = by_status.get(f["status"], 0) + 1
    if rejected:
        notes.insert(0, f"LLM の指摘のうち {rejected} 件を受け入れなかった")
    return {
        "schema_version": 1,
        "tool": {"name": "sumidashi", "version": VERSION},
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "root": facts["root"],
        "target": {k: v for k, v in target.items() if k != "changed_lines"},
        "strictness": strictness,
        "layer_map": {k: v for k, v in (facts.get("layer_map") or {}).items() if k not in ("files", "unmapped")},
        "applicability": applicability,
        "active_by_philosophy": {
            pid: sum(1 for a in active.values() if a["philosophy"] == pid) for pid in applicability
        },
        "summary": {
            "counts": counts,
            "by_status": by_status,
            "headline": f"High が {counts['High']} 件" if counts["High"] else "",
        },
        "findings": findings,
        "aggregated": aggregated,
        "scores": scores if cfg.get("report_scores", True) else None,
        "checks_run": sorted(active),
        "checks_skipped": facts.get("skipped_checks") or [],
        "adrs_used": sorted({f["adr"] for f in findings if f.get("adr")}),
        "notes": (facts.get("notes") or []) + notes,
    }
