"""ontology/shapes.ttl が、壊した設計知識を本当に弾くかを確かめる。"""

import copy

import pytest

pytest.importorskip("pyshacl")

from build_knowledge import build_graph  # noqa: E402
from rdflib import Graph  # noqa: E402
from validate_knowledge import SHAPES, VOCAB, adr_graph  # noqa: E402

from sumidashi.catalog import PLUGIN_ROOT, build_index  # noqa: E402


@pytest.fixture(scope="module")
def index():
    return build_index(PLUGIN_ROOT)


@pytest.fixture(scope="module")
def shapes():
    return Graph().parse(SHAPES, format="turtle"), Graph().parse(VOCAB, format="turtle")


def validate(data, shapes):
    from pyshacl import validate as shacl

    sh, vocab = shapes
    conforms, _, text = shacl(data, shacl_graph=sh, ont_graph=vocab, inference="none", advanced=True)
    return conforms, text


def broken(index, mutate):
    idx = copy.deepcopy(index)
    mutate(idx)
    return build_graph(idx)


def test_current_knowledge_conforms(index, shapes):
    conforms, text = validate(build_graph(index), shapes)
    assert conforms, text


def test_principle_without_source(index, shapes):
    pid = sorted(index["principles"])[0]
    conforms, text = validate(broken(index, lambda i: i["principles"][pid].update(sources=[])), shapes)
    assert not conforms and "出典を 1 つ以上" in text


def test_check_based_on_undefined_principle(index, shapes):
    conforms, text = validate(broken(index, lambda i: i["checks"]["CA-DEP-01"].update(principles=["NO-SUCH"])), shapes)
    assert not conforms and "定義済みの原則" in text


def test_ready_check_without_borderline_fixture(index, shapes):
    conforms, text = validate(broken(index, lambda i: i["checks"]["CA-DEP-01"]["fixtures"].pop("borderline")), shapes)
    assert not conforms and "borderline の評価ケースがない" in text


def test_conflict_needs_symmetry_and_ruling(index, shapes):
    def one_way(i):
        i["checks"]["CA-DEP-01"].setdefault("conflicts_with", []).append("DDD-EVT-01")

    conforms, text = validate(broken(index, one_way), shapes)
    assert not conforms and "逆向きの conflictsWith がない" in text

    def both_ways_no_ruling(i):
        one_way(i)
        i["checks"]["DDD-EVT-01"].setdefault("conflicts_with", []).append("CA-DEP-01")

    conforms, text = validate(broken(index, both_ways_no_ruling), shapes)
    assert not conforms and "裁定ルールがない" in text
    assert "逆向き" not in text


def test_also_accept_must_be_related(index, shapes):
    def mutate(i):
        c = i["checks"]["DDD-EVT-01"]
        c["also_accept"] = ["CA-DEP-01"]
        c["related"] = [r for r in c.get("related") or [] if r != "CA-DEP-01"]

    conforms, text = validate(broken(index, mutate), shapes)
    assert not conforms and "related に入れていない" in text


def test_adr_exempts_unknown_check_and_missing_scope(index, shapes, make_repo):
    repo = make_repo({
        "docs/adr/0001-ok.md": """
            ---
            status: accepted
            scope: [src/reporting/**]
            exempts: [CA-DEP-02]
            ---
            # 1. 集計系の例外
        """,
        "docs/adr/0002-bad.md": """
            ---
            status: accepted
            exempts: [CA-DEP-99]
            ---
            # 2. 範囲のない例外
        """,
    })
    g, n = adr_graph(repo)
    assert n == 2
    conforms, text = validate(build_graph(index) + g, shapes)
    assert not conforms
    assert "実在するチェックID" in text and "scope が空" in text
    assert "ADR-0001" not in text
