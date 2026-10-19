"""generated/knowledge.ttl を ontology/shapes.ttl（SHACL）で検証する。

使い方:
  uv run --no-project --with-requirements tools/requirements.txt --with rdflib --with pyshacl \
      python tools/dev/validate_knowledge.py [--adr-root REPO]

--adr-root を渡すと、そのリポジトリの ADR も RDF にして一緒に検証する
（exempts が実在するチェックを指すか、exempts を持つ ADR に scope があるか）。
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

KNOWLEDGE = ROOT / "generated" / "knowledge.ttl"
VOCAB = ROOT / "ontology" / "vocabulary.ttl"
SHAPES = ROOT / "ontology" / "shapes.ttl"


def adr_graph(repo: pathlib.Path):
    from rdflib import RDF, Graph, Literal, Namespace, URIRef

    from sumidashi import adr
    from sumidashi.config import load_config

    sd = Namespace("urn:sumidashi:vocab#")
    g = Graph()
    _, adrs = adr.load_adrs(repo, load_config(repo).adr_path)
    for a in adrs:
        node = URIRef(f"urn:sumidashi:adr:{a['id']}")
        g.add((node, RDF.type, sd.ADR))
        g.add((node, sd.identifier, Literal(a["id"])))
        g.add((node, sd.adrStatus, Literal(a["status"])))
        for s in a["scope"]:
            g.add((node, sd.scope, Literal(s)))
        # 形の崩れた ID も検証で見えるよう、読み込み前の値を使う
        raw = adr._as_list(adr._split_frontmatter(
            (repo / a["file"]).read_text(encoding="utf-8", errors="replace"))[0].get("exempts"))
        for cid in raw:
            g.add((node, sd.exempts, URIRef(f"urn:sumidashi:check:{cid}")))
    return g, len(adrs)


def main(argv: list[str] | None = None) -> int:
    from pyshacl import validate
    from rdflib import Graph

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adr-root", help="ADR も検証する対象リポジトリ")
    args = ap.parse_args(argv)

    if not KNOWLEDGE.is_file():
        print("generated/knowledge.ttl がない。先に tools/dev/build_knowledge.py を実行する")
        return 1
    data = Graph().parse(KNOWLEDGE, format="turtle")
    if args.adr_root:
        g, n = adr_graph(pathlib.Path(args.adr_root))
        data += g
        print(f"ADR {n} 件を加えた")
    shapes = Graph().parse(SHAPES, format="turtle")
    vocab = Graph().parse(VOCAB, format="turtle")
    conforms, _, text = validate(
        data, shacl_graph=shapes, ont_graph=vocab, inference="none", advanced=True, allow_warnings=False,
    )
    if conforms:
        print(f"SHACL: 適合（トリプル {len(data)}）")
        return 0
    print(text)
    return 1


if __name__ == "__main__":
    sys.exit(main())
