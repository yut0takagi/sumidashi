import json

import pytest

from sumidashi import cli, hook

FILES = {
    "src/domain/order.ts": """
        import { Db } from "../infrastructure/db";

        export class Order {
          constructor(readonly id: string, private db: Db) {}
        }
    """,
    "src/application/place-order.ts": """
        import { Order } from "../domain/order";

        export function placeOrder(id: string): string {
          return id;
        }
    """,
    "src/infrastructure/db.ts": """
        export class Db {}
    """,
}


@pytest.fixture
def repo(make_repo):
    return make_repo(FILES)


def test_review_reports_dependency_violation(repo, capsys):
    code = cli.main(["review", "--root", str(repo), "--all", "--format", "json", "--fail-on", "High"])
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    hits = [f for f in report["findings"] if f["id"] == "CA-DEP-01"]
    assert len(hits) == 1
    assert hits[0]["location"] == {"file": "src/domain/order.ts", "start_line": 1, "end_line": 1}
    assert hits[0]["severity"] == "High" and hits[0]["status"] == "reported"
    assert report["scores"]["clean-architecture"]["score"] == 7.0


def test_review_markdown_and_out_dir(repo, tmp_path_factory, capsys):
    out = tmp_path_factory.mktemp("out")
    assert cli.main(["review", "--root", str(repo), "--all", "--out", str(out)]) == 0
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "CA-DEP-01" in md and "src/domain/order.ts:1" in md
    assert (out / "facts.json").is_file() and (out / "report.json").is_file()


def test_layers_explain_and_export(repo, capsys):
    assert cli.main(["layers", "--root", str(repo), "--format", "json"]) == 0
    layers = json.loads(capsys.readouterr().out)
    assert layers["layer_map"]["estimable"]
    assert cli.main(["explain", "CA-DEP-01", "--root", str(repo)]) == 0
    assert "CA-DEP-01" in capsys.readouterr().out
    assert cli.main(["export", "depcruise", "--root", str(repo)]) == 0
    assert "module.exports" in capsys.readouterr().out


def _event(repo, command="gh pr create --fill"):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(repo)})


def test_pre_pr_hook_is_off_by_default(repo):
    assert hook.pre_pr(_event(repo)) is None


def test_pre_pr_hook_warns_on_high(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude" / "sumidashi.yml").write_text("hooks:\n  pre_pr_check: true\n", encoding="utf-8")
    out = hook.pre_pr(_event(repo))
    assert out and "CA-DEP-01 src/domain/order.ts:1" in out["systemMessage"]
    assert hook.pre_pr(_event(repo, "gh pr list")) is None
    assert hook.pre_pr("not json") is None
