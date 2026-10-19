"""設計知識のビルド。checks.yml と conflicts.yml から生成物を作る。

  generated/index.json     実行時に読む索引（tools/sumidashi/catalog.py）
  generated/knowledge.ttl  SHACL で検証する RDF（ontology/vocabulary.ttl の語彙）
  docs/check-catalog.md    チェックの一覧（評価結果つき）

使い方:
  uv run --no-project --with-requirements tools/requirements.txt --with rdflib --with jsonschema \
      python tools/dev/build_knowledge.py [--check]

--check は書き込まずに、生成物が最新か、checks.yml がスキーマと参照の規則を満たすかだけを確かめる（CI 用）。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from sumidashi import catalog  # noqa: E402

INDEX = ROOT / "generated" / "index.json"
KNOWLEDGE = ROOT / "generated" / "knowledge.ttl"
CATALOG_MD = ROOT / "docs" / "check-catalog.md"
SCHEMA = ROOT / "schemas" / "checks-file.schema.json"
VOCAB = "urn:sumidashi:vocab#"


def validate_sources() -> list[str]:
    """スキーマと、ファイルをまたぐ参照の確認。問題の一覧を返す。"""
    import jsonschema

    errors: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    seen: dict[str, str] = {}
    principles: set[str] = set()
    sources: set[str] = set()
    data_by_file = {}
    for f in sorted(ROOT.glob("skills/*/checks.yml")):
        rel = f.relative_to(ROOT).as_posix()
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        data_by_file[rel] = data
        for err in validator.iter_errors(data):
            path = "/".join(str(p) for p in err.absolute_path)
            errors.append(f"{rel}: {path}: {err.message}")
        prefixes = tuple(p + "-" for p in (data.get("philosophy") or {}).get("id_prefixes") or [])
        for c in data.get("checks") or []:
            cid = c.get("id", "?")
            if cid in seen:
                errors.append(f"{rel}: チェックID {cid} が {seen[cid]} と重複")
            seen[cid] = rel
            if prefixes and not cid.startswith(prefixes):
                errors.append(f"{rel}: {cid} の接頭辞が id_prefixes {list(prefixes)} に合わない")
        principles |= {p["id"] for p in data.get("principles") or [] if "id" in p}
        sources |= {s["id"] for s in data.get("sources") or [] if "id" in s}
    for rel, data in data_by_file.items():
        for p in data.get("principles") or []:
            for s in p.get("sources") or []:
                if s not in sources:
                    errors.append(f"{rel}: 原則 {p['id']} の出典 {s} が定義されていない")
        for c in data.get("checks") or []:
            cid = c.get("id", "?")
            for p in c.get("principles") or []:
                if p not in principles:
                    errors.append(f"{rel}: {cid} の原則 {p} が定義されていない")
            for key in ("related", "also_accept", "conflicts_with"):
                for other in c.get(key) or []:
                    if other not in seen:
                        errors.append(f"{rel}: {cid} の {key} にある {other} が存在しない")
            impl = (c.get("detection") or {}).get("implementation")
            if impl and c["detection"].get("type") == "llm":
                errors.append(f"{rel}: {cid} は llm なのに implementation がある")
            for label, cases in (c.get("fixtures") or {}).items():
                for case in cases or []:
                    if not (ROOT / "evals" / "fixtures" / case).is_dir():
                        errors.append(f"{rel}: {cid} の評価ケース {case} のディレクトリがない")
                    exp = ROOT / "evals" / "expected" / f"{case}.json"
                    if not exp.is_file():
                        errors.append(f"{rel}: {cid} の評価ケース {case} の期待値がない")
                        continue
                    e = json.loads(exp.read_text(encoding="utf-8"))
                    if e.get("check") != cid:
                        errors.append(f"{exp.relative_to(ROOT)}: check が {e.get('check')}（{cid} のはず）")
                    want = "violation" if label == "violation" else label
                    if e.get("label") != want:
                        errors.append(f"{exp.relative_to(ROOT)}: label が {e.get('label')}（{want} のはず）")
    conflicts = yaml.safe_load(catalog.CONFLICTS_PATH.read_text(encoding="utf-8")) if catalog.CONFLICTS_PATH.is_file() else {}
    rulings = {r["id"] for r in (conflicts or {}).get("rulings") or []}
    for pair in (conflicts or {}).get("conflicts") or []:
        for cid in pair.get("checks") or []:
            if cid not in seen:
                errors.append(f"conflicts.yml: {cid} が存在しない")
        if pair.get("ruling") not in rulings:
            errors.append(f"conflicts.yml: 裁定 {pair.get('ruling')} が rulings にない")
    return errors


def build_graph(index: dict):
    from rdflib import RDF, Graph, Literal, Namespace, URIRef

    sd = Namespace(VOCAB)
    g = Graph()
    g.bind("sd", sd)

    def iri(kind: str, ident: str) -> URIRef:
        return URIRef(f"urn:sumidashi:{kind}:{ident}")

    for sid, s in sorted(index["sources"].items()):
        node = iri("source", sid)
        g.add((node, RDF.type, sd.Source))
        g.add((node, sd.identifier, Literal(sid)))
        g.add((node, sd.name, Literal(s.get("title", ""))))
    for pid, ph in sorted(index["philosophies"].items()):
        node = iri("philosophy", pid)
        g.add((node, RDF.type, sd.Philosophy))
        g.add((node, sd.identifier, Literal(pid)))
        g.add((node, sd.name, Literal(ph.get("name", pid))))
        if ph.get("release"):
            g.add((node, sd.release, Literal(ph["release"])))
    for pid, p in sorted(index["principles"].items()):
        node = iri("principle", pid)
        g.add((node, RDF.type, sd.Principle))
        g.add((node, sd.identifier, Literal(pid)))
        g.add((node, sd.statement, Literal(p.get("statement", ""))))
        for s in p.get("sources") or []:
            g.add((node, sd.citedFrom, iri("source", s)))
    for cid, c in sorted(index["checks"].items()):
        node = iri("check", cid)
        g.add((node, RDF.type, sd.Check))
        g.add((node, sd.identifier, Literal(cid)))
        g.add((node, sd.name, Literal(c.get("name", ""))))
        g.add((node, sd.belongsTo, iri("philosophy", c["_philosophy"])))
        g.add((node, sd.status, Literal(c["status"])))
        g.add((node, sd.detection, Literal(c["detection"]["type"])))
        g.add((node, sd.defaultSeverity, Literal(c["severity"]["default"])))
        if c.get("release"):
            g.add((node, sd.release, Literal(c["release"])))
        for p in c.get("principles") or []:
            g.add((node, sd.basedOn, iri("principle", p)))
        for key, prop in (("related", sd.related), ("also_accept", sd.alsoAccept), ("conflicts_with", sd.conflictsWith)):
            for other in c.get(key) or []:
                g.add((node, prop, iri("check", other)))
        for label, cases in (c.get("fixtures") or {}).items():
            for case in cases or []:
                fx = iri("fixture", case)
                g.add((fx, RDF.type, sd.Fixture))
                g.add((fx, sd.label, Literal(label)))
                g.add((fx, sd.path, Literal(f"evals/fixtures/{case}")))
                g.add((node, sd.hasFixture, fx))
    for r in index.get("rulings") or []:
        node = iri("ruling", r["id"])
        g.add((node, RDF.type, sd.Ruling))
        g.add((node, sd.identifier, Literal(r["id"])))
        if "order" in r:
            g.add((node, sd.order, Literal(int(r["order"]))))
    for pair in index.get("conflicts") or []:
        a, b = pair["checks"]
        node = iri("conflict", f"{a}--{b}")
        g.add((node, RDF.type, sd.Conflict))
        g.add((node, sd.between, iri("check", a)))
        g.add((node, sd.between, iri("check", b)))
        if pair.get("ruling"):
            g.add((node, sd.resolvedBy, iri("ruling", pair["ruling"])))
    return g


def _cell(text) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|")


def build_catalog_md(index: dict, results: dict) -> str:
    lines = [
        "# チェック一覧",
        "",
        "`tools/dev/build_knowledge.py` が checks.yml と評価結果から生成する。手で編集しない。",
        "",
        "状態が ready のチェックは、評価の出荷ゲート（適合率・再現率とも 0.85 以上）を通ると既定で有効になる。"
        "draft のチェックは、設定の `experimental: true` のときだけ走る。",
        "",
    ]
    for pid in catalog.PHILOSOPHY_ORDER + tuple(p for p in index["philosophies"] if p not in catalog.PHILOSOPHY_ORDER):
        ph = index["philosophies"].get(pid)
        if not ph:
            continue
        lines += [f"## {ph.get('name', pid)}（{pid}）", "", _cell(ph.get("summary")), ""]
        lines += ["| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for cid in ph.get("check_ids") or []:
            c = index["checks"][cid]
            g = (results.get("checks") or {}).get(cid)
            if g:
                ev = f"P {g['precision']:.2f} / R {g['recall']:.2f}（{'通過' if g['passed'] else '未通過'}）"
            else:
                ev = "-"
            lines.append(
                f"| {cid} | {_cell(c['name'])} | {c['detection']['type']} | {c['status']} | "
                f"{c['severity']['default']} | {c.get('release', '')} | {ev} |"
            )
        lines.append("")
    if index.get("conflicts"):
        lines += ["## 衝突の裁定", "", "| 組 | 裁定 |", "| --- | --- |"]
        for pair in index["conflicts"]:
            lines.append(f"| {' と '.join(pair['checks'])} | {pair.get('ruling', '')} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="書き込まずに、最新かどうかと参照の規則だけを確かめる")
    args = ap.parse_args(argv)

    errors = validate_sources()
    for e in errors:
        print(f"エラー: {e}")
    index = catalog.build_index(ROOT)
    results = catalog.load_results()
    outputs = {
        INDEX: json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        KNOWLEDGE: "# tools/dev/build_knowledge.py が生成した。手で編集しない。\n"
        + build_graph(index).serialize(format="turtle"),
        CATALOG_MD: build_catalog_md(index, results),
    }
    stale = []
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    if args.check:
        for s in stale:
            print(f"古い生成物: {s}（build_knowledge.py を実行してコミットする）")
        return 1 if errors or stale else 0
    print(f"チェック {len(index['checks'])}、原則 {len(index['principles'])}、出典 {len(index['sources'])}。"
          f"更新: {', '.join(stale) or 'なし'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
