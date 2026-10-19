"""差分モード: マージベースからの変更行に掛かる指摘だけを出す。"""

import shutil
import subprocess

import pytest

from sumidashi.analyze import collect
from sumidashi.files import churn

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git がない")


def git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
        cwd=root, check=True, capture_output=True,
    )


@pytest.fixture
def repo(make_repo):
    root = make_repo({
        "src/domain/order.ts": """
            export class Order {
              constructor(readonly id: string) {}
            }
        """,
        "src/domain/legacy.ts": """
            import { Db } from "../infrastructure/db";
            export const legacy = (db: Db) => db;
        """,
        "src/application/place-order.ts": """
            import { Order } from "../domain/order";
            export const place = (id: string) => new Order(id);
        """,
        "src/infrastructure/db.ts": "export class Db {}\n",
    })
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "feature")
    return root


def violations(facts, cid):
    return sorted((f["location"]["file"], f["location"]["start_line"]) for f in facts["findings"] if f["id"] == cid)


def test_only_changed_lines_are_reported(repo):
    (repo / "src/domain/order.ts").write_text(
        'import { Db } from "../infrastructure/db";\n\nexport class Order {\n  constructor(readonly id: string) {}\n}\n',
        encoding="utf-8",
    )
    git(repo, "commit", "-qam", "change")
    # コミットしていない新しいファイルも対象
    (repo / "src/domain/coupon.ts").write_text('import { Db } from "../infrastructure/db";\nexport class Coupon {}\n',
                                               encoding="utf-8")
    facts = collect(repo, base="main")
    assert facts["target"]["mode"] == "diff"
    assert sorted(facts["target"]["files"]) == ["src/domain/coupon.ts", "src/domain/order.ts"]
    # 変更していない legacy.ts の既存の違反は出さない
    assert violations(facts, "CA-DEP-01") == [("src/domain/coupon.ts", 1), ("src/domain/order.ts", 1)]

    everything = collect(repo, all_files=True)
    assert ("src/domain/legacy.ts", 1) in violations(everything, "CA-DEP-01")


def test_explicit_base_must_exist(repo, capsys):
    from sumidashi import cli
    from sumidashi.files import BaseNotFound

    with pytest.raises(BaseNotFound):
        collect(repo, base="no-such-branch")
    with pytest.raises(SystemExit) as e:
        cli.main(["review", "--root", str(repo), "--base", "no-such-branch"])
    assert e.value.code == 2 and "no-such-branch" in capsys.readouterr().err


def test_default_base_falls_back_to_all(make_repo):
    root = make_repo({"src/domain/a.ts": "export class A {}\n"})
    git(root, "init", "-q", "-b", "trunk")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    facts = collect(root)
    assert facts["target"]["mode"] == "all"
    assert any("比較先" in n for n in facts["notes"])


def test_churn_counts_commits(repo):
    for i in range(3):
        (repo / "src/domain/order.ts").write_text(f"export class Order {{}} // {i}\n", encoding="utf-8")
        git(repo, "commit", "-qam", f"c{i}")
    counts = churn(repo)
    assert counts["src/domain/order.ts"] == 4
    assert counts["src/infrastructure/db.ts"] == 1
