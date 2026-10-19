"""report.json を Markdown にする。順番は 総評 → 指摘一覧 → 要確認 → 衝突により保留 → 採点。"""

from __future__ import annotations

from . import catalog

_MODE_JA = {"full": "すべてのチェック", "dep-only": "CA-DEP 系のみ", "ent-vo-only": "ENT・VO 系のみ", "off": "適用しない"}
_TARGET_JA = {"diff": "差分", "all": "リポジトリ全体", "paths": "指定したパス"}
_SEV_ORDER = ("High", "Medium", "Low", "Info")


def _loc(f: dict) -> str:
    loc = f["location"]
    if loc["start_line"] == loc["end_line"]:
        return f"{loc['file']}:{loc['start_line']}"
    return f"{loc['file']}:{loc['start_line']}-{loc['end_line']}"


def _fence(text: str, lang: str = "") -> list[str]:
    tick = "````" if "```" in text else "```"
    return [f"{tick}{lang}", text.rstrip("\n"), tick]


def _finding_block(f: dict, checks: dict) -> list[str]:
    c = checks.get(f["id"], {})
    out = [f"### [{f['severity']}] {f['id']} {f.get('name') or c.get('name', '')}", ""]
    out.append(f"- 場所: `{_loc(f)}`")
    out.append(f"- エビデンス: {f['evidence']['summary']}")
    for fact in f["evidence"].get("facts") or []:
        out.append(f"  - {fact}")
    source = c.get("source")
    out.append(f"- 原則: {f['principle']}" + (f"（出典: {source}）" if source else ""))
    out.append(f"- 修正方針: {f['suggestion']['summary']}")
    if f["suggestion"].get("placement"):
        out.append(f"  - 置き場所の判定: {f['suggestion']['placement']}")
    out.append(f"- 判定方式: {f['detection']}" + ("（要確認）" if f["verdict"] == "borderline" else ""))
    t = f["tradeoff"]
    files_n = t.get("files_to_change")
    out.append(
        f"- トレードオフ: 直すコストは{t['fix_cost']}。直さない場合は、{t['impact_if_ignored']}"
        + (f"（変更ファイル数の目安: {files_n}）" if files_n else "")
    )
    for tr in f.get("severity_trace") or []:
        out.append(f"- 重大度の調整: {tr['from']} → {tr['to']}（{tr['rule']}: {tr.get('reason', '')}）")
    if f.get("adr"):
        out.append(f"- 例外: {f['adr']} の scope と exempts に当たる")
    snippet = f["evidence"].get("snippet")
    if snippet:
        out += ["", *_fence(snippet)]
    if f["suggestion"].get("diff"):
        out += ["", "差分案:", "", *_fence(f["suggestion"]["diff"], "diff")]
    out.append("")
    return out


def render_markdown(report: dict, min_severity: str | None = None) -> str:
    index = catalog.load_index()
    checks = index["checks"]
    keep = set(_SEV_ORDER[: _SEV_ORDER.index(min_severity) + 1]) if min_severity in _SEV_ORDER else set(_SEV_ORDER)
    fs = report["findings"]
    reported = [f for f in fs if f["status"] == "reported" and f["severity"] in keep]
    review = [f for f in fs if f["status"] == "needs_review" and f["severity"] in keep]
    held = [f for f in fs if f["status"] == "held"]
    counts = report["summary"]["counts"]

    lines = ["# sumidashi レビュー", "", "## 総評", ""]
    if counts.get("High"):
        lines.append(f"**High が {counts['High']} 件あります。**")
        lines.append("")
        for f in fs:
            if f["status"] in ("reported", "aggregated") and f["severity"] == "High":
                lines.append(f"- {f['id']} `{_loc(f)}` {f['evidence']['summary']}")
        lines.append("")
    target = report.get("target") or {}
    tdesc = _TARGET_JA.get(target.get("mode"), target.get("mode", ""))
    if target.get("mode") == "diff":
        tdesc += f"（{target.get('base')} とのマージベース {str(target.get('merge_base', ''))[:8]} から）"
    lines.append(f"- 対象: {tdesc}、{len(target.get('files') or [])} ファイル")
    lm = report.get("layer_map") or {}
    lines.append(
        f"- 層マップ: {'設定' if lm.get('source') == 'config' else '設定と推定' if lm.get('source') == 'config+estimated' else '推定'}"
        f"（{'推定できた' if lm.get('estimable') else '推定できない'}）"
    )
    applied, not_applied, idle = [], [], []
    active_n = report.get("active_by_philosophy") or {}
    for pid, app in sorted((report.get("applicability") or {}).items()):
        reason = "。".join(app.get("reasons") or [])
        if app["mode"] == "off":
            not_applied.append(f"{pid}（{reason}）")
        elif active_n.get(pid, 1) == 0:
            idle.append(pid)
        else:
            applied.append(f"{pid}（{_MODE_JA.get(app['mode'], app['mode'])}）")
    if applied:
        lines.append(f"- 適用した思想: {'、'.join(applied)}")
    if not_applied:
        lines.append(f"- 適用しなかった思想: {'、'.join(not_applied)}")
    if idle:
        lines.append(f"- 走らせるチェックがなかった思想: {'、'.join(idle)}（draft のチェックは設定の experimental: true で走る）")
    for pid, app in sorted((report.get("applicability") or {}).items()):
        if app["mode"] not in ("full", "off"):
            lines.append(f"  - {pid}: {'。'.join(app.get('reasons') or [])}")
    by_status = report["summary"].get("by_status") or {}
    lines.append(
        "- 件数: " + " / ".join(f"{s} {counts.get(s, 0)}" for s in _SEV_ORDER)
        + f"、要確認 {by_status.get('needs_review', 0)}、保留 {by_status.get('held', 0)}"
    )
    lines.append("")

    lines += ["## 指摘一覧", ""]
    if not reported:
        lines += ["指摘はありません。", ""]
    for f in reported:
        lines += _finding_block(f, checks)
    for agg in report.get("aggregated") or []:
        sample = "、".join(agg["locations"][:5]) + ("ほか" if len(agg["locations"]) > 5 else "")
        lines += [f"- {agg['id']}: 同種の違反がほかに {agg['count']} 件（{sample}）", ""]

    lines += ["## 要確認", ""]
    if not review:
        lines += ["ありません。", ""]
    shown: dict[str, int] = {}
    for f in review:
        shown[f["id"]] = shown.get(f["id"], 0) + 1
        if shown[f["id"]] > 5:
            continue
        lines.append(f"- [{f['severity']}] {f['id']} `{_loc(f)}` {f['evidence']['summary']}")
        if shown[f["id"]] == 1:
            crit = (checks.get(f["id"], {}).get("criteria") or {}).get("borderline", "")
            if crit:
                lines.append(f"  - 確かめること: {' '.join(crit.split())}")
    for cid, n in shown.items():
        if n > 5:
            lines.append(f"- {cid}: 同じ種類の要確認がほかに {n - 5} 件（report.json の findings に全件ある）")
    lines.append("")

    if held:
        lines += ["## 衝突により保留", ""]
        for f in held:
            hb = f.get("held_by") or {}
            lines.append(f"- {f['id']} `{_loc(f)}` {f['evidence']['summary']}（{hb.get('id')} を {hb.get('ruling')} で採った）")
        lines.append("")

    if report.get("scores"):
        lines += ["## 採点", "", "| 思想 | 点数 | 減点の件数 |", "| --- | --- | --- |"]
        for pid, s in report["scores"].items():
            lines.append(f"| {pid} | {s['score']} / 10 | {len(s['deductions'])} |")
        lines.append("")
        for pid, s in report["scores"].items():
            steps = s["improvements"]
            if not steps:
                continue
            lines.append(f"{pid} を重い順に直したときの点数:")
            lines.append("")
            # 下限0点に張りついている間の指摘は1行にまとめる
            stuck = 0
            while stuck < len(steps) and steps[stuck]["score_after"] <= s["score"]:
                stuck += 1
            if stuck:
                head = steps[: stuck + 1] if stuck < len(steps) else steps
                by_sev = {}
                for g in head:
                    by_sev[g["severity"]] = by_sev.get(g["severity"], 0) + 1
                kinds = "・".join(f"{k} {v} 件" for k, v in by_sev.items())
                lines.append(f"- 減点の合計は {s.get('total_deduction', '?')} 点。上から {len(head)} 件（{kinds}）を直すと"
                             f" {head[-1]['score_after']} 点")
                steps = steps[len(head):]
            for g in steps[: 5 if not stuck else 4]:
                lines.append(f"- {g['id']} `{g['file']}:{g['line']}`（{g['severity']}）を直すと {g['score_after']} 点")
            lines.append("")

    if report.get("notes"):
        lines += ["## 補足", ""]
        lines += [f"- {n}" for n in report["notes"]]
        lines.append("")
    return "\n".join(lines)
