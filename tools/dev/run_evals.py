"""static チェックの評価。evals/fixtures のケースに解析器をかけ、期待値と突き合わせる。

使い方:
  uv run --no-project --with-requirements tools/requirements.txt python tools/dev/run_evals.py [--runs 5] [--check] [--write]

--write で evals/results/latest.json を書く（出荷ゲートの判定に使う）。
--check で、出荷ゲートを通らない ready のチェックか、外れた適用判定のケースがあれば終了コード 1 を返す。
突き合わせの規則は evals/README.md と docs/architecture.md「評価」の節。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from sumidashi import VERSION, catalog  # noqa: E402
from sumidashi.analyze import collect  # noqa: E402
from sumidashi.finalize import finalize  # noqa: E402

FIXTURES = ROOT / "evals" / "fixtures"
EXPECTED = ROOT / "evals" / "expected"
RESULTS = ROOT / "evals" / "results" / "latest.json"
GATE = 0.85


def _overlap(a: dict, b: dict) -> bool:
    return a["file"] == b["file"] and a["start_line"] <= b["end_line"] and b["start_line"] <= a["end_line"]


def _loc(f: dict) -> dict:
    if "location" in f:
        return f["location"]
    return {"file": f["file"], "start_line": f["start_line"], "end_line": f["end_line"]}


def _match(expected: list[dict], actual: list[dict]) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    """期待1件に指摘1件まで。(一致の組, 外れた期待, 余った指摘)"""
    pairs, used = [], set()
    unmatched_exp = []
    for e in sorted(expected, key=lambda e: (e["file"], e["start_line"])):
        hit = next(
            (i for i, a in enumerate(actual) if i not in used and _overlap(_loc(e), _loc(a))),
            None,
        )
        if hit is None:
            unmatched_exp.append(e)
        else:
            used.add(hit)
            pairs.append((e, actual[hit]))
    rest = [a for i, a in enumerate(actual) if i not in used]
    return pairs, unmatched_exp, rest


def _run_case(case_dir: pathlib.Path, check_id: str, runs: int) -> tuple[list[dict], float]:
    """(指摘, High・Medium の指摘集合の Jaccard 係数の平均)"""
    sets = []
    findings: list[dict] = []
    for _ in range(max(1, runs)):
        facts = collect(case_dir, all_files=True, eval_mode=True, checks=[check_id])
        findings = facts["findings"]
        sets.append({(f["id"], f["location"]["file"], f["location"]["start_line"], f["verdict"])
                     for f in findings if f["severity"] in ("High", "Medium")})
    base = sets[0]
    scores = []
    for s in sets[1:]:
        union = base | s
        scores.append(len(base & s) / len(union) if union else 1.0)
    return findings, (sum(scores) / len(scores) if scores else 1.0)


def _ratio(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def evaluate_checks(runs: int) -> dict:
    out: dict[str, dict] = {}
    for exp_file in sorted(EXPECTED.glob("*/*.json")):
        if exp_file.parent.name.startswith("_"):
            continue
        exp = json.loads(exp_file.read_text(encoding="utf-8"))
        cid = exp["check"]
        case_dir = FIXTURES / exp["case"]
        rec = out.setdefault(cid, {
            "cases": 0,
            "dev": {"tp": 0, "fp": 0, "fn": 0},
            "holdout": {"tp": 0, "fp": 0, "fn": 0},
            "has_holdout": False,
            "borderline": {"expected": 0, "matched": 0},
            "borderline_noise": 0,
            "jaccard": [],
            "failures": [],
        })
        rec["cases"] += 1
        if not case_dir.is_dir():
            rec["failures"].append({"case": exp["case"], "kind": "missing_fixture"})
            continue
        actual, jac = _run_case(case_dir, cid, runs)
        rec["jaccard"].append(jac)
        actual = [f for f in actual if f["id"] == cid]
        act_v = [f for f in actual if f["verdict"] == "violation"]
        act_b = [f for f in actual if f["verdict"] == "borderline"]
        exp_v = [e for e in exp["findings"] if e["id"] == cid and e["verdict"] == "violation"]
        exp_b = [e for e in exp["findings"] if e["id"] == cid and e["verdict"] == "borderline"]
        split = "holdout" if exp.get("split") == "holdout" else "dev"
        if split == "holdout":
            rec["has_holdout"] = True
        bucket = rec[split]

        _, miss_b, _ = _match(exp_b, act_b)
        rec["borderline"]["expected"] += len(exp_b)
        rec["borderline"]["matched"] += len(exp_b) - len(miss_b)
        for e in miss_b:
            rec["failures"].append({"case": exp["case"], "kind": "borderline_missed", "file": e["file"], "line": e["start_line"]})

        if exp["label"] == "borderline":
            continue  # 適合率・再現率に数えない
        if exp["label"] == "not_violation":
            bucket["fp"] += len(act_v)
            rec["borderline_noise"] += len(act_b)
            for a in act_v:
                rec["failures"].append({"case": exp["case"], "kind": "FP", "file": a["location"]["file"],
                                        "line": a["location"]["start_line"], "summary": a["evidence"]["summary"]})
            continue
        pairs, miss_v, extra_v = _match(exp_v, act_v)
        bucket["tp"] += len(pairs)
        bucket["fn"] += len(miss_v)
        bucket["fp"] += len(extra_v)
        for e in miss_v:
            rec["failures"].append({"case": exp["case"], "kind": "FN", "file": e["file"], "line": e["start_line"]})
        for a in extra_v:
            rec["failures"].append({"case": exp["case"], "kind": "FP", "file": a["location"]["file"],
                                    "line": a["location"]["start_line"], "summary": a["evidence"]["summary"]})
        _, _, extra_b = _match(exp_b, act_b)
        _, _, noise = _match(exp_v, extra_b)
        rec["borderline_noise"] += len(noise)

    for cid, rec in out.items():
        for split in ("dev", "holdout"):
            b = rec[split]
            b["precision"] = _ratio(b["tp"], b["tp"] + b["fp"])
            b["recall"] = _ratio(b["tp"], b["tp"] + b["fn"])
        allb = {k: rec["dev"][k] + rec["holdout"][k] for k in ("tp", "fp", "fn")}
        rec["all"] = {**allb, "precision": _ratio(allb["tp"], allb["tp"] + allb["fp"]),
                      "recall": _ratio(allb["tp"], allb["tp"] + allb["fn"])}
        gate_split = "holdout" if rec["has_holdout"] else "all"
        g = rec[gate_split]
        # 何も出さず何も期待しない場合は適合率を 1 とみなす
        precision = g["precision"] if g["precision"] is not None else (1.0 if g["fp"] == 0 else 0.0)
        recall = g["recall"] if g["recall"] is not None else 1.0
        rec["gate_split"] = gate_split
        rec["precision"] = precision
        rec["recall"] = recall
        bl = rec["borderline"]
        bl["agreement"] = _ratio(bl["matched"], bl["expected"])
        rec["jaccard"] = round(sum(rec["jaccard"]) / len(rec["jaccard"]), 4) if rec["jaccard"] else None
        rec["passed"] = precision >= GATE and recall >= GATE and not any(
            f["kind"] == "missing_fixture" for f in rec["failures"]
        )
    return out


def evaluate_applicability() -> dict:
    cases, failures = 0, []
    for exp_file in sorted((EXPECTED / "_applicability").glob("*.json")):
        exp = json.loads(exp_file.read_text(encoding="utf-8"))
        cases += 1
        case_dir = FIXTURES / exp["case"]
        facts = collect(case_dir, all_files=True, ignore_gate=True)
        report = finalize(facts)
        for pid, want in exp["expect"].items():
            app = facts["applicability"].get(pid, {})
            got_findings = [f for f in report["findings"] if f.get("philosophy") == pid]
            if "applied" in want and (app.get("mode") != "off") != want["applied"]:
                failures.append({"case": exp["case"], "philosophy": pid, "field": "applied",
                                 "expected": want["applied"], "actual": app.get("mode")})
            if "mode" in want and app.get("mode") != want["mode"]:
                failures.append({"case": exp["case"], "philosophy": pid, "field": "mode",
                                 "expected": want["mode"], "actual": app.get("mode")})
            if "severity_shift" in want and app.get("severity_shift", 0) != want["severity_shift"]:
                failures.append({"case": exp["case"], "philosophy": pid, "field": "severity_shift",
                                 "expected": want["severity_shift"], "actual": app.get("severity_shift")})
            if "max_findings" in want and len(got_findings) > want["max_findings"]:
                failures.append({"case": exp["case"], "philosophy": pid, "field": "max_findings",
                                 "expected": want["max_findings"], "actual": len(got_findings)})
    return {"cases": cases, "failed": len({f["case"] for f in failures}), "failures": failures}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=5, help="再現性を測るための繰り返し回数（既定 5）")
    ap.add_argument("--write", action="store_true", help="evals/results/latest.json を書く")
    ap.add_argument("--check", action="store_true", help="ゲートを通らないものがあれば終了コード 1")
    ap.add_argument("--verbose", "-v", action="store_true", help="外れたケースを表示する")
    args = ap.parse_args(argv)

    checks = evaluate_checks(args.runs)
    appl = evaluate_applicability()
    index = catalog.build_index()
    status = {cid: c["status"] for cid, c in index["checks"].items()}

    print(f"{'check':<12} {'status':<6} {'P':>6} {'R':>6} {'split':<8} {'BL':>6} {'Jac':>5}  gate")
    for cid, rec in sorted(checks.items()):
        bl = rec["borderline"]["agreement"]
        print(f"{cid:<12} {status.get(cid, '?'):<6} {rec['precision']:>6.2f} {rec['recall']:>6.2f} "
              f"{rec['gate_split']:<8} {('-' if bl is None else f'{bl:.2f}'):>6} {rec['jaccard'] or 0:>5.2f}  "
              f"{'pass' if rec['passed'] else 'FAIL'}")
        if args.verbose:
            for f in rec["failures"]:
                print(f"    {f['kind']:<18} {f['case']}  {f.get('file', '')}:{f.get('line', '')}  {f.get('summary', '')}")
    print(f"適用判定: {appl['cases'] - appl['failed']}/{appl['cases']} ケースが期待どおり")
    if args.verbose:
        for f in appl["failures"]:
            print(f"    {f['case']} {f['philosophy']}.{f['field']}: 期待 {f['expected']} / 実際 {f['actual']}")

    if args.write:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "tool_version": VERSION,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "gate": {"precision": GATE, "recall": GATE},
            "runs": args.runs,
            "checks": checks,
            "applicability": appl,
        }
        RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"書いた: {RESULTS.relative_to(ROOT)}")

    failed_ready = [cid for cid, rec in checks.items() if status.get(cid) == "ready" and not rec["passed"]]
    # 実行時はコミット済みの latest.json のゲート結果でチェックを有効にするので、今回の結果と食い違えば古い
    stale = []
    if args.check and not args.write:
        recorded = (catalog.load_results() or {}).get("checks") or {}
        stale = sorted(cid for cid in set(checks) | set(recorded)
                       if (recorded.get(cid) or {}).get("passed") != (checks.get(cid) or {}).get("passed"))
        for cid in stale:
            print(f"latest.json が古い: {cid} の記録は {(recorded.get(cid) or {}).get('passed')}、"
                  f"今回は {(checks.get(cid) or {}).get('passed')}（--write を付けて実行し、コミットする）")
    if args.check and (failed_ready or appl["failed"] or stale):
        print(f"ゲート未通過: {', '.join(failed_ready) or 'なし'} / 適用判定の不一致: {appl['failed']} ケース"
              f" / latest.json との食い違い: {len(stale)} 件")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
