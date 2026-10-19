"""PreToolUse hook: gh pr create の前に、High の static チェックだけを差分にかけて警告する。

ブロックはしない。設定の hooks.pre_pr_check が true のときだけ動く。
失敗したときは何も出さずに終わる（PR の作成を邪魔しない）。
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

_GH_PR_CREATE = re.compile(r"(^|[;&|]\s*|\s)gh\s+pr\s+create(\s|$)")


def _git_root(cwd: pathlib.Path) -> pathlib.Path:
    from .files import _git

    out = _git(cwd, "rev-parse", "--show-toplevel")
    return pathlib.Path(out.strip()) if out else cwd


def pre_pr(stdin_text: str) -> dict | None:
    try:
        event = json.loads(stdin_text or "{}")
    except ValueError:
        return None
    if event.get("tool_name") != "Bash":
        return None
    command = (event.get("tool_input") or {}).get("command") or ""
    if not _GH_PR_CREATE.search(command):
        return None
    root = _git_root(pathlib.Path(event.get("cwd") or "."))

    from .analyze import collect
    from .config import load_config
    from .finalize import finalize

    if not load_config(root).pre_pr_check:
        return None
    facts = collect(root)
    facts["active_checks"] = [
        a for a in facts["active_checks"] if a["detection"] == "static" and a["severity"] == "High"
    ]
    ids = {a["id"] for a in facts["active_checks"]}
    facts["findings"] = [f for f in facts["findings"] if f["id"] in ids]
    report = finalize(facts)
    highs = [f for f in report["findings"] if f["status"] in ("reported", "aggregated") and f["severity"] == "High"]
    if not highs:
        return None
    lines = [f"sumidashi: この差分に High の設計上の指摘が {len(highs)} 件あります（PR の作成は止めません）。"]
    for f in highs[:5]:
        loc = f["location"]
        lines.append(f"- {f['id']} {loc['file']}:{loc['start_line']} {f['evidence']['summary']}")
    if len(highs) > 5:
        lines.append(f"- ほか {len(highs) - 5} 件")
    lines.append("詳しくは /sumidashi:review で確認できます。")
    return {"systemMessage": "\n".join(lines)}


def main() -> int:
    try:
        out = pre_pr(sys.stdin.read())
    except Exception:  # noqa: BLE001  hook は PR の作成を邪魔しない
        return 0
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0
