import copy

from sumidashi.adr import exemption_for, normalize_status, parse_adr
from sumidashi.finalize import finalize


def F(cid, file="src/domain/a.ts", line=1, severity="Medium", verdict="violation", philosophy=None,
      detection="static", files_to_change=1, **extra):
    philosophy = philosophy or {
        "CA": "clean-architecture", "DDD": "ddd-tactical", "MDL": "model-commonality", "GLO": "glossary",
    }[cid.split("-")[0]]
    f = {
        "id": cid, "philosophy": philosophy, "severity": severity,
        "location": {"file": file, "start_line": line, "end_line": line},
        "evidence": {"summary": f"{cid} の指摘", "facts": []},
        "principle": "p", "suggestion": {"summary": "s"}, "verdict": verdict, "detection": detection,
        "tradeoff": {"fix_cost": "小", "impact_if_ignored": "x", "files_to_change": files_to_change},
        "fingerprint": f"{cid}-{file}-{line}",
    }
    f.update(extra)
    return f


def facts(tmp_path, findings, *, applicability=None, adrs=None, strictness="standard", active=None, candidates=None):
    app = applicability or {
        p: {"mode": "full", "reasons": [], "severity_shift": 0}
        for p in ("clean-architecture", "ddd-tactical", "model-commonality", "glossary")
    }
    return {
        "root": str(tmp_path),
        "target": {"mode": "all", "files": []},
        "config": {"effective_strictness": strictness, "report_scores": True},
        "applicability": app,
        "active_checks": active or [],
        "findings": copy.deepcopy(findings),
        "candidates": candidates or {},
        "adrs": adrs or [],
    }


def by_id(report, cid):
    return [f for f in report["findings"] if f["id"] == cid]


def test_severity_hint_and_applicability_shift(tmp_path):
    fs = [F("CA-DEP-02", severity="High", severity_hint={"to": "Medium", "rule": "deescalate", "reason": "型だけ"}),
          F("CA-DEP-01", severity="High", line=5)]
    app = {"clean-architecture": {"mode": "dep-only", "reasons": [], "severity_shift": -1}}
    r = finalize(facts(tmp_path, fs, applicability=app))
    dep02 = by_id(r, "CA-DEP-02")[0]
    # 固有ルールで Medium に決まってから、適用判定で1段下げる
    assert dep02["severity"] == "Low"
    assert [t["rule"] for t in dep02["severity_trace"]] == ["check:deescalate", "applicability"]
    assert by_id(r, "CA-DEP-01")[0]["severity"] == "Medium"


def test_mode_drops_other_checks(tmp_path):
    fs = [F("DDD-ENT-03"), F("DDD-REP-02", line=3)]
    app = {"ddd-tactical": {"mode": "ent-vo-only", "reasons": [], "severity_shift": 0}}
    r = finalize(facts(tmp_path, fs, applicability=app))
    assert [f["id"] for f in r["findings"]] == ["DDD-ENT-03"]


def test_adr_exemption(tmp_path):
    adr = {"id": "ADR-0007", "usable_for_exemption": True, "exempts": ["CA-DEP-02", "DDD-VO-01"],
           "scope": ["src/reporting/**"]}
    fs = [F("CA-DEP-02", file="src/reporting/a.ts", severity="High"),
          F("CA-DEP-02", file="src/domain/a.ts", severity="High"),
          F("DDD-VO-01", file="src/reporting/b.ts", severity="High", detection="hybrid")]
    r = finalize(facts(tmp_path, fs, adrs=[adr]))
    sev = {(f["id"], f["location"]["file"]): (f["severity"], f.get("adr")) for f in r["findings"]}
    assert sev[("CA-DEP-02", "src/reporting/a.ts")] == ("Info", "ADR-0007")
    assert sev[("CA-DEP-02", "src/domain/a.ts")] == ("High", None)
    assert sev[("DDD-VO-01", "src/reporting/b.ts")] == ("Low", "ADR-0007")


def test_borderline_strictness_and_aggregation(tmp_path):
    fs = [F("DDD-ENT-03", line=i, severity="Medium") for i in range(1, 8)]
    fs += [F("DDD-VO-02", line=20, verdict="borderline"), F("DDD-EVT-01", line=30, severity="Low")]
    r = finalize(facts(tmp_path, fs))
    statuses = [f["status"] for f in by_id(r, "DDD-ENT-03")]
    assert statuses.count("reported") == 5 and statuses.count("aggregated") == 2
    assert r["aggregated"][0]["count"] == 2
    assert by_id(r, "DDD-VO-02")[0]["status"] == "needs_review"
    # 採点: Medium 7件（集約した分も引く）と Low 1件。要確認は引かない
    assert r["scores"]["ddd-tactical"]["score"] == 0.0
    strict = finalize(facts(tmp_path, fs, strictness="strict"))
    assert by_id(strict, "DDD-VO-02")[0]["status"] == "reported"
    lenient = finalize(facts(tmp_path, fs, strictness="lenient"))
    assert by_id(lenient, "DDD-EVT-01")[0]["status"] == "filtered"


def test_scores_and_gain(tmp_path):
    r = finalize(facts(tmp_path, [F("CA-DEP-01", severity="High"), F("CA-BND-02", line=9)]))
    s = r["scores"]["clean-architecture"]
    assert s["score"] == 5.5
    assert [g["gain"] for g in s["improvements"]] == [3.0, 1.5]
    assert [g["score_after"] for g in s["improvements"]] == [8.5, 10.0]


def test_score_below_floor_still_shows_what_to_fix(tmp_path):
    from sumidashi.render import render_markdown

    fs = [F("CA-DEP-01", severity="High", line=i) for i in range(1, 5)] + [F("CA-BND-02", line=9)]
    r = finalize(facts(tmp_path, fs))
    s = r["scores"]["clean-architecture"]
    assert s["score"] == 0.0 and s["total_deduction"] == 13.5
    assert all(g["gain"] == 0.0 for g in s["improvements"])
    assert [g["score_after"] for g in s["improvements"]] == [0.0, 2.5, 5.5, 8.5, 10.0]
    md = render_markdown(r)
    assert "上から 2 件（High 2 件）を直すと 2.5 点" in md


def test_also_accept_merge(tmp_path):
    fs = [F("GLO-04", severity="Medium"), F("DDD-AGG-04", severity="Medium", detection="hybrid")]
    r = finalize(facts(tmp_path, fs))
    assert by_id(r, "GLO-04")[0]["status"] == "merged"
    assert by_id(r, "DDD-AGG-04")[0]["status"] == "reported"


def test_conflict_rulings(tmp_path):
    # R1: 重大度の高いほう
    r = finalize(facts(tmp_path, [F("CA-DEP-01", severity="High"), F("MDL-01", detection="hybrid")]))
    assert by_id(r, "MDL-01")[0]["status"] == "held"
    assert by_id(r, "MDL-01")[0]["held_by"]["ruling"] == "R1-HIGH"
    # R2: 同じ重大度なら CA-DEP を採る
    r = finalize(facts(tmp_path, [F("CA-DEP-01", severity="High"), F("MDL-01", severity="High", detection="hybrid")]))
    assert by_id(r, "MDL-01")[0]["held_by"]["ruling"] == "R2-DEPENDENCY"
    # R3: 変更ファイル数の少ないほう
    r = finalize(facts(tmp_path, [F("MDL-01", files_to_change=3, detection="hybrid"),
                                  F("MDL-05", files_to_change=1, detection="llm")]))
    assert by_id(r, "MDL-01")[0]["status"] == "held"
    assert by_id(r, "MDL-05")[0]["status"] == "reported"
    # 場所が重ならなければ衝突しない
    r = finalize(facts(tmp_path, [F("CA-DEP-01", severity="High"), F("MDL-01", line=40, detection="hybrid")]))
    assert {f["status"] for f in r["findings"]} == {"reported"}


def test_llm_findings_are_validated(tmp_path):
    active = [{"id": "DDD-AGG-01", "philosophy": "ddd-tactical", "detection": "hybrid"},
              {"id": "DDD-AGG-02", "philosophy": "ddd-tactical", "detection": "llm"}]
    llm = [F("DDD-AGG-01", detection="hybrid", severity="High"),
           F("DDD-AGG-02", detection="llm", severity="High", line=7),
           F("DDD-ENT-02", detection="llm")]
    base = facts(tmp_path, [], active=active)
    r = finalize(base, llm)
    assert [f["id"] for f in r["findings"]] == ["DDD-AGG-02"]
    assert any("候補にない" in n for n in r["notes"])
    with_cand = facts(tmp_path, [], active=active, candidates={"DDD-AGG-01": [
        {"location": {"file": "src/domain/a.ts", "start_line": 1, "end_line": 3}}]})
    r = finalize(with_cand, llm)
    assert sorted(f["id"] for f in r["findings"]) == ["DDD-AGG-01", "DDD-AGG-02"]


def test_adr_parsing(tmp_path):
    p = tmp_path / "0007-reporting.md"
    p.write_text(
        "---\nstatus: accepted\nscope: [src/reporting/**]\nexempts: [CA-BND-01, bad]\n---\n"
        "# 0007. 集計系は ORM を直接使う\n\n## 背景\n集計が重い。\n\n## 決定\n直接使う。\n\n## 結果\n速い。\n",
        encoding="utf-8",
    )
    a = parse_adr(p, "docs/adr/0007-reporting.md")
    assert a["id"] == "ADR-0007" and a["status"] == "accepted" and a["format"] == "nygard"
    assert a["exempts"] == ["CA-BND-01"] and a["usable_for_exemption"]
    assert any("bad" in prob for prob in a["problems"])
    assert exemption_for([a], "CA-BND-01", "src/reporting/x.ts")["id"] == "ADR-0007"
    assert exemption_for([a], "CA-BND-01", "src/other/x.ts") is None

    n = tmp_path / "0002-db.md"
    n.write_text("# 2. DB\n\n## Status\n\nSuperseded by ADR-0009\n\n## Context\nx\n\n## Decision\ny\n\n## Consequences\nz\n")
    b = parse_adr(n, "docs/adr/0002-db.md")
    assert b["status"] == "superseded" and b["superseded_by"] == ["ADR-0009"] and not b["usable_for_exemption"]
    assert normalize_status("承認済み") == "accepted"
    assert normalize_status("Proposed") == "proposed"
