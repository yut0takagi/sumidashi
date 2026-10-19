"""層マップから dependency-cruiser・import-linter の設定を作る。"""

from __future__ import annotations

import json
import re

from . import globs
from .layers import ALLOWED, LAYERS, LayerMap


def layer_patterns(lm: LayerMap) -> dict[str, list[str]]:
    """層 → パスの正規表現。推定はキーワードのディレクトリまで、設定は glob をそのまま正規表現にする。"""
    out: dict[str, set[str]] = {layer: set() for layer in LAYERS}
    for path, layer in lm.files.items():
        reason = lm.reasons.get(path, "")
        if reason.startswith("config:"):
            out[layer].add(globs._compile(reason[len("config:"):]).pattern)
        elif reason.startswith(("strong:", "weak:")):
            kw = reason.split(":", 1)[1]
            parts = path.split("/")
            idx = next(i for i, p in enumerate(parts[:-1]) if p.lower() == kw)
            out[layer].add("^" + re.escape("/".join(parts[: idx + 1])) + "/")
        else:
            out[layer].add("^" + re.escape(path) + "$")
    return {layer: sorted(p) for layer, p in out.items() if p}


def depcruise(lm: LayerMap) -> str:
    pats = layer_patterns(lm)
    rules = []
    for src in LAYERS:
        for dst in LAYERS:
            if src == dst or dst in ALLOWED[src] or src not in pats or dst not in pats:
                continue
            rules.append({
                "name": f"{src}-not-to-{dst}",
                "comment": f"{src} から {dst} への依存は禁止（sumidashi の層マップ）",
                "severity": "error",
                "from": {"path": "|".join(f"({p})" for p in pats[src])},
                "to": {"path": "|".join(f"({p})" for p in pats[dst])},
            })
    rules.append({
        "name": "no-cross-layer-cycles",
        "comment": "層をまたぐ循環（CA-DEP-04）",
        "severity": "error",
        "from": {},
        "to": {"circular": True},
    })
    body = json.dumps({"forbidden": rules, "options": {"tsPreCompilationDeps": True}}, ensure_ascii=False, indent=2)
    return "/** sumidashi export depcruise が層マップから生成した。 */\nmodule.exports = " + body + ";\n"


def _modules_for(lm: LayerMap, layer: str, source_roots: list[str]) -> list[str]:
    mods = set()
    for path, lay in lm.files.items():
        if lay != layer or not path.endswith(".py"):
            continue
        reason = lm.reasons.get(path, "")
        parts = path[:-3].split("/")
        if reason.startswith(("strong:", "weak:")):
            kw = reason.split(":", 1)[1]
            idx = next(i for i, p in enumerate(parts[:-1]) if p.lower() == kw)
            parts = parts[: idx + 1]
        elif parts[-1] == "__init__":
            parts = parts[:-1]
        for r in sorted(source_roots, key=len, reverse=True):
            r = r.strip("/")
            if r not in ("", ".") and parts[: len(r.split("/"))] == r.split("/"):
                parts = parts[len(r.split("/")) :]
                break
        if parts and all(p.isidentifier() for p in parts):
            mods.add(".".join(parts))
    # 親のモジュールがあれば子は省く
    return sorted(m for m in mods if not any(m != o and m.startswith(o + ".") for o in mods))


def importlinter(lm: LayerMap, source_roots: list[str]) -> str:
    mods = {layer: _modules_for(lm, layer, source_roots) for layer in LAYERS}
    roots = sorted({m.split(".")[0] for ms in mods.values() for m in ms})
    lines = ["# sumidashi export importlinter が層マップから生成した", "[importlinter]", "root_packages ="]
    lines += [f"    {r}" for r in roots]
    n = 0
    for src in LAYERS:
        forbidden = [m for dst in LAYERS if dst != src and dst not in ALLOWED[src] for m in mods[dst]]
        if not mods[src] or not forbidden:
            continue
        n += 1
        lines += ["", f"[importlinter:contract:sumidashi-{src}]", f"name = {src} は外側の層に依存しない",
                  "type = forbidden", "source_modules ="]
        lines += [f"    {m}" for m in mods[src]]
        lines += ["forbidden_modules ="] + [f"    {m}" for m in forbidden]
    if n == 0:
        lines.append("# Python の層が2つ以上見つからないため、契約は作れなかった")
    return "\n".join(lines) + "\n"
