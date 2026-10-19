"""collect・finalize の出力が schemas/ の JSON Schema に従うことを確かめる。"""

import json

import pytest

jsonschema = pytest.importorskip("jsonschema")
referencing = pytest.importorskip("referencing")

from sumidashi.analyze import collect  # noqa: E402
from sumidashi.catalog import PLUGIN_ROOT  # noqa: E402
from sumidashi.finalize import finalize  # noqa: E402

from test_cli import FILES  # noqa: E402

SCHEMAS = PLUGIN_ROOT / "schemas"


@pytest.fixture(scope="module")
def registry():
    from referencing.jsonschema import DRAFT202012

    resources = []
    for p in SCHEMAS.glob("*.schema.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        resources.append((doc["$id"], DRAFT202012.create_resource(doc)))
    return referencing.Registry().with_resources(resources)


def validator(registry, name):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, registry=registry)


def errors(v, doc):
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in v.iter_errors(doc)]


def test_facts_and_report_follow_schemas(make_repo, registry):
    repo = make_repo({
        **FILES,
        "docs/adr/0001-reporting.md": "---\nstatus: accepted\nscope: [src/reporting/**]\nexempts: [CA-DEP-02]\n---\n# 1. x\n",
    })
    facts = collect(repo, all_files=True)
    assert not errors(validator(registry, "facts"), facts)
    report = finalize(json.loads(json.dumps(facts)))
    assert report["findings"], "違反を含むリポジトリなのに指摘がない"
    v = validator(registry, "report")
    assert not errors(v, report)
    # $ref 先の finding スキーマまで効いていること
    broken = json.loads(json.dumps(report))
    broken["findings"][0]["severity"] = "Critical"
    del broken["findings"][0]["status"]
    msgs = errors(v, broken)
    assert any("Critical" in m for m in msgs) and any("status" in m for m in msgs)


def test_report_without_scores(make_repo, registry):
    repo = make_repo({**FILES, ".claude/sumidashi.yml": "report:\n  scores: false\n"})
    report = finalize(collect(repo, all_files=True))
    assert report["scores"] is None
    assert not errors(validator(registry, "report"), report)


def test_other_schemas_are_valid(registry):
    for name in ("finding", "checks-file", "config"):
        validator(registry, name)
