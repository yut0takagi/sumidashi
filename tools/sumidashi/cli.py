"""sumidashi の CLI。サブコマンドの一覧は docs/architecture.md「解析器の CLI」。"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import VERSION

_SEVERITIES = ("High", "Medium", "Low", "Info")


def _write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_apply(values: list[str] | None) -> dict[str, str]:
    from .analyze import APPLY_MODES

    out = {}
    for v in values or []:
        pid, _, mode = v.partition("=")
        mode = {"on": "full"}.get(mode, mode)
        allowed = APPLY_MODES.get(pid, ("full", "off"))
        if mode not in allowed:
            raise SystemExit(f"--apply {v}: {pid} に指定できるのは {', '.join(allowed)}（on は full と同じ）")
        out[pid] = mode
    return out


def _add_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("paths", nargs="*", help="対象のパス（省略すると差分）")
    p.add_argument("--base", help="差分の比較先（既定は main、なければ master）")
    p.add_argument("--all", action="store_true", help="リポジトリ全体を対象にする")
    p.add_argument("--philosophy", help="この思想のチェックだけを走らせる")
    p.add_argument("--checks", help="走らせるチェックID（カンマ区切り）")
    p.add_argument("--apply", action="append", metavar="PHILO=MODE",
                   help="適用判定を上書きする（例: ddd-tactical=on、clean-architecture=dep-only）")


def _collect(args) -> dict:
    from .analyze import collect
    from .files import BaseNotFound

    try:
        return collect(
            pathlib.Path(args.root),
            paths=args.paths or None,
            base=args.base,
            all_files=args.all,
            philosophy=args.philosophy,
            checks=[c.strip() for c in args.checks.split(",") if c.strip()] if args.checks else None,
            overrides=_parse_apply(args.apply),
        )
    except BaseNotFound as e:
        # --fail-on の終了コード 1 と区別できるよう 2 で終わる
        print(f"sumidashi: {e}", file=sys.stderr)
        raise SystemExit(2) from None


def cmd_collect(args) -> int:
    facts = _collect(args)
    if args.out:
        out = pathlib.Path(args.out) / "facts.json"
        _write_json(out, facts)
        llm = sorted({a["philosophy"] for a in facts["active_checks"] if a["detection"] != "static"})
        print(f"facts: {out}")
        print(f"対象 {len(facts['target']['files'])} ファイル、static の指摘 {len(facts['findings'])} 件、"
              f"LLM に回す思想: {', '.join(llm) or 'なし'}")
    else:
        print(json.dumps(facts, ensure_ascii=False, indent=2))
    return 0


def _load_llm(paths: list[str] | None) -> list[dict]:
    out: list[dict] = []
    for p in paths or []:
        try:
            data = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"警告: {p} を読めなかった（{exc}）", file=sys.stderr)
            continue
        if isinstance(data, dict):
            data = data.get("findings") or []
        out.extend(x for x in data if isinstance(x, dict))
    return out


def _emit_report(report: dict, out_dir: str | None, fmt: str, min_severity: str | None) -> None:
    from .render import render_markdown

    md = render_markdown(report, min_severity=min_severity)
    if out_dir:
        d = pathlib.Path(out_dir)
        _write_json(d / "report.json", report)
        (d / "report.md").write_text(md, encoding="utf-8")
        print(f"report: {d / 'report.md'} / {d / 'report.json'}")
    elif fmt == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(md)


def cmd_finalize(args) -> int:
    from .finalize import finalize

    facts = json.loads(pathlib.Path(args.facts).read_text(encoding="utf-8"))
    report = finalize(facts, _load_llm(args.llm))
    _emit_report(report, args.out, args.format, args.min_severity)
    return 0


def cmd_review(args) -> int:
    from .finalize import finalize

    facts = _collect(args)
    if args.out:
        _write_json(pathlib.Path(args.out) / "facts.json", facts)
    report = finalize(facts)
    _emit_report(report, args.out, args.format, args.min_severity)
    if args.fail_on:
        limit = _SEVERITIES.index(args.fail_on)
        bad = [f for f in report["findings"]
               if f["status"] in ("reported", "aggregated") and _SEVERITIES.index(f["severity"]) <= limit]
        return 1 if bad else 0
    return 0


def cmd_layers(args) -> int:
    from .analyze import collect

    facts = collect(pathlib.Path(args.root), all_files=True, ignore_gate=True, checks=["__none__"])
    lm, scale, app = facts["layer_map"], facts["scale"], facts["applicability"]
    if args.write_config:
        import yaml

        dirs: dict[str, str] = {}
        for path, layer in sorted(lm["files"].items()):
            parts = path.split("/")
            d = "/".join(parts[:-1])
            if d:
                # 同じ層のディレクトリはいちばん浅いものにまとめる
                if not any(d == k or d.startswith(k + "/") for k, v in dirs.items() if v == layer):
                    dirs[d] = layer
        draft = {
            "philosophies": {"clean-architecture": "auto", "ddd-tactical": "auto"},
            "strictness": "standard",
            "layers": {f"{d}/**": layer for d, layer in sorted(dirs.items())},
            "exclude": [],
        }
        out = pathlib.Path(args.write_config)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# sumidashi layers --write-config が推定から書いた下書き。確かめてから使う\n"
                       + yaml.safe_dump(draft, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"設定の下書きを書いた: {out}")
        return 0
    if args.format == "json":
        print(json.dumps({"layer_map": lm, "scale": scale, "applicability": app}, ensure_ascii=False, indent=2))
        return 0
    print(f"層マップ: {lm['source']}（{'推定できた' if lm['estimable'] else '推定できない'}）")
    for layer, n in lm["counts"].items():
        if n:
            print(f"  {layer:<15} {n:>4} ファイル  {scale['loc_by_layer'].get(layer, 0):>6} 行")
    print(f"  {'unmapped':<15} {lm['unmapped_count']:>4} ファイル  {scale['loc_by_layer'].get('unmapped', 0):>6} 行")
    print(f"ドメイン層の行数の割合: {scale['domain_ratio']:.1%}")
    print(f"エンティティ {len(scale['entities'])}、値オブジェクト {len(scale['value_objects'])}、"
          f"集約らしき型 {len(scale['aggregate_candidates'])}")
    print("適用判定:")
    for pid, a in sorted(app.items()):
        print(f"  {pid:<20} {a['mode']:<12} {'。'.join(a['reasons'])}")
    if args.verbose:
        print("ファイルごとの層:")
        for path, layer in sorted(lm["files"].items()):
            print(f"  {layer:<15} {path}")
        for path in lm["unmapped"]:
            print(f"  {'(unmapped)':<15} {path}")
    return 0


def cmd_explain(args) -> int:
    from . import adr, catalog
    from .config import load_config

    index = catalog.load_index()
    cid = args.id.upper()
    c = index["checks"].get(cid)
    if c is None:
        print(f"チェック {cid} はない", file=sys.stderr)
        return 1
    results = catalog.load_results()
    g = catalog.gate(results, cid)
    root = pathlib.Path(args.root)
    _, adrs = adr.load_adrs(root, load_config(root).adr_path)
    exempting = [a for a in adrs if cid in a["exempts"]]
    if args.format == "json":
        print(json.dumps({"check": c, "principles": [index["principles"].get(p) for p in c.get("principles", [])],
                          "eval": g, "adrs": exempting}, ensure_ascii=False, indent=2))
        return 0
    print(f"{cid} {c['name']}（{c['_philosophy']}、{c['detection']['type']}、{c['status']}、既定 {c['severity']['default']}）")
    print(f"原則: {c['principle']}")
    for pid in c.get("principles", []):
        p = index["principles"].get(pid)
        if p:
            srcs = ", ".join(index["sources"].get(s, {}).get("title", s) for s in p.get("sources", []))
            print(f"  - {pid}: {p['statement']}（{srcs}）")
    print(f"出典: {c.get('source', '')}")
    print(f"場所の決め方: {c.get('location', '')}")
    for k, label in (("violation", "違反"), ("borderline", "要確認"), ("not_violation", "違反でない")):
        print(f"{label}: {' '.join(str(c['criteria'].get(k, '')).split())}")
    if c["severity"].get("escalate"):
        print(f"上げる条件: {c['severity']['escalate']}")
    if c["severity"].get("deescalate"):
        print(f"下げる条件: {c['severity']['deescalate']}")
    print("直し方:")
    for fp in c.get("fix_patterns", []):
        print(f"  - {fp}")
    fx = c.get("fixtures") or {}
    if any(fx.values()):
        print("評価ケース: " + "、".join(f"{k} {len(v)}" for k, v in fx.items() if v))
        for k, v in fx.items():
            for case in v:
                print(f"  - evals/fixtures/{case}（{k}）")
    if g:
        print(f"評価: 適合率 {g['precision']:.2f}・再現率 {g['recall']:.2f}（{g['gate_split']}）"
              f" → 出荷ゲート{'通過' if g['passed'] else '未通過'}")
    if exempting:
        print("このリポジトリでこのチェックを例外にしている ADR:")
        for a in exempting:
            print(f"  - {a['id']} {a['title']}（{a['status']}、scope: {', '.join(a['scope']) or 'なし'}）")
    return 0


def cmd_catalog(args) -> int:
    from . import catalog

    index = catalog.load_index()
    results = catalog.load_results()
    rows = []
    for cid, c in sorted(index["checks"].items()):
        if args.philosophy and c["_philosophy"] != args.philosophy:
            continue
        g = catalog.gate(results, cid) or {}
        rows.append({
            "id": cid, "philosophy": c["_philosophy"], "name": c["name"], "detection": c["detection"]["type"],
            "status": c["status"], "release": c.get("release"), "severity": c["severity"]["default"],
            "precision": g.get("precision"), "recall": g.get("recall"), "passed": g.get("passed"),
        })
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print("| ID | 思想 | 名前 | 判定 | 状態 | 重大度 | 適合率 | 再現率 | ゲート |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        p = "-" if r["precision"] is None else f"{r['precision']:.2f}"
        rc = "-" if r["recall"] is None else f"{r['recall']:.2f}"
        gate = "-" if r["passed"] is None else ("通過" if r["passed"] else "未通過")
        print(f"| {r['id']} | {r['philosophy']} | {r['name']} | {r['detection']} | {r['status']} | "
              f"{r['severity']} | {p} | {rc} | {gate} |")
    return 0


def cmd_adr(args) -> int:
    from . import adr
    from .config import load_config

    root = pathlib.Path(args.root)
    d, adrs = adr.load_adrs(root, load_config(root).adr_path)
    if args.format == "json":
        print(json.dumps({"dir": d, "adrs": adrs}, ensure_ascii=False, indent=2))
        return 0
    if d is None:
        print("ADR のディレクトリが見つからない（設定の adr.path か docs/adr）")
        return 0
    print(f"ADR: {d}（{len(adrs)} 件）")
    for a in adrs:
        flag = "例外に使う" if a["usable_for_exemption"] else "例外に使わない"
        print(f"- {a['id']} {a['title']}")
        print(f"    status: {a['status']}（{a['status_text'] or '記載なし'}）、形式: {a['format']}、{flag}")
        if a["scope"]:
            print(f"    scope: {', '.join(a['scope'])}")
        if a["exempts"]:
            print(f"    exempts: {', '.join(a['exempts'])}")
        if a["supersedes"] or a["superseded_by"]:
            print(f"    supersedes: {', '.join(a['supersedes']) or '-'} / superseded_by: {', '.join(a['superseded_by']) or '-'}")
        for prob in a["problems"]:
            print(f"    注意: {prob}")
    return 0


def cmd_export(args) -> int:
    from . import export
    from .config import load_config
    from .files import is_test_path, list_source_files
    from .layers import build_layer_map

    root = pathlib.Path(args.root)
    cfg = load_config(root)
    files_ = [p for p in list_source_files(root, cfg.exclude) if not is_test_path(p)]
    lm = build_layer_map(files_, cfg.layers)
    if args.tool == "depcruise":
        print(export.depcruise(lm), end="")
    else:
        print(export.importlinter(lm, cfg.source_roots), end="")
    return 0


def cmd_hook(args) -> int:
    from . import hook

    if args.event != "pre-pr":
        return 0
    return hook.main()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sumidashi", description="設計思想のチェックの解析器")
    ap.add_argument("--version", action="version", version=f"sumidashi {VERSION}")
    sub = ap.add_subparsers(dest="command", required=True)

    def add(name: str, help_: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        p.add_argument("--root", default=".", help="対象リポジトリのルート（既定はカレントディレクトリ）")
        return p

    p = add("collect", "静的解析して facts.json を書く")
    _add_target_args(p)
    p.add_argument("--out", help="facts.json を書くディレクトリ（省略すると標準出力）")
    p.set_defaults(func=cmd_collect)

    p = add("finalize", "facts と LLM の指摘をまとめて report を書く")
    p.add_argument("--facts", required=True)
    p.add_argument("--llm", nargs="*", help="principle-reviewer が書いた指摘の JSON")
    p.add_argument("--out", help="report.json と report.md を書くディレクトリ（省略すると標準出力）")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--min-severity", choices=_SEVERITIES)
    p.set_defaults(func=cmd_finalize)

    p = add("review", "collect と finalize を続けて実行する（static のチェックだけ）")
    _add_target_args(p)
    p.add_argument("--out")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--min-severity", choices=_SEVERITIES)
    p.add_argument("--fail-on", choices=_SEVERITIES, help="この重大度以上の指摘があれば終了コード 1（CI 用）")
    p.set_defaults(func=cmd_review)

    p = add("layers", "層マップ・規模・適用判定を表示する")
    p.add_argument("--write-config", metavar="FILE", help="設定ファイルの下書きを書く")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--verbose", "-v", action="store_true", help="ファイルごとの層も表示する")
    p.set_defaults(func=cmd_layers)

    p = add("explain", "チェックの定義・原則・出典・評価・例外の ADR を表示する")
    p.add_argument("id")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=cmd_explain)

    p = add("catalog", "チェックの一覧と出荷ゲートの状態を表示する")
    p.add_argument("--philosophy")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.set_defaults(func=cmd_catalog)

    p = add("adr", "ADR の読み込み結果を表示する")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=cmd_adr)

    p = add("export", "層マップから dependency-cruiser・import-linter の設定を出す")
    p.add_argument("tool", choices=("depcruise", "importlinter"))
    p.set_defaults(func=cmd_export)

    p = add("hook", "Claude Code の hook から呼ぶ")
    p.add_argument("event", choices=("pre-pr",))
    p.set_defaults(func=cmd_hook)

    args = ap.parse_args(argv)
    return args.func(args)
