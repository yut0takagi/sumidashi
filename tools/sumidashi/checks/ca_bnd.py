"""CA-BND-02: ユースケースの公開シグネチャに Web フレームワークの型が出ている。"""

from __future__ import annotations

from ..frameworks import WEB_DI_ONLY
from ..model import Function, Module, words_in
from . import Ctx, finding, register
from .common import is_public_member


def _public_functions(mod: Module) -> list[Function]:
    out: list[Function] = []
    if mod.lang == "typescript":
        out += [f for f in mod.functions if f.exported]
        for cls in mod.classes:
            if cls.exported and cls.kind in ("class", "abstract_class"):
                out += [m for m in cls.methods if is_public_member(m.name, m.access, "typescript")]
    else:
        out += [f for f in mod.functions if is_public_member(f.name, "public", "python")]
        for cls in mod.classes:
            if not cls.name.startswith("_"):
                out += [m for m in cls.methods if is_public_member(m.name, "public", "python")]
    return out


def _signature_words(fn: Function) -> set[str]:
    words = words_in(fn.returns)
    for p in fn.params:
        words |= words_in(p.type)
    return words


@register("ca_bnd_02")
def ca_bnd_02(ctx: Ctx) -> list[dict]:
    out = []
    for mod in ctx.modules_in("application"):
        web_imports = [
            imp for imp in mod.imports
            if imp.external and ctx.ledger.classify(imp.external, mod.lang) == "web"
        ]
        if not web_imports:
            continue
        web_names = {local: imp for imp in web_imports for local in imp.bindings if local != "*"}
        used: set[str] = set()
        for fn in _public_functions(mod):
            hits = sorted(_signature_words(fn) & set(web_names))
            if not hits:
                continue
            used.update(hits)
            pkgs = sorted({web_names[h].external for h in hits})
            out.append(
                finding(
                    ctx, "CA-BND-02", mod, fn.line,
                    summary=f"{fn.name} の引数か戻り値に Web フレームワークの型 {', '.join(hits)} が出ている",
                    facts=[f"{h} は {web_names[h].external} から import（{mod.path}:{web_names[h].line}）" for h in hits],
                    suggestion=(
                        "ユースケースの入出力を、フレームワークに依存しない入力・出力の型（DTO）で定義し、"
                        f"{', '.join(pkgs)} の型との変換はコントローラ（アダプタ層）で行う"
                    ),
                    fix_cost="小〜中（入出力の型を定義し、コントローラで変換する）",
                    impact="ユースケースを CLI・バッチ・テストから呼べず、Web フレームワークの変更がユースケースに波及する",
                    files_to_change=2,
                )
            )
        for imp in web_imports:
            names = {local for local in imp.bindings if local != "*"}
            if not names or names & used:
                continue
            if {imp.bindings[n] for n in names} <= WEB_DI_ONLY:
                continue
            out.append(
                finding(
                    ctx, "CA-BND-02", mod, imp.line, imp.end_line,
                    verdict="borderline",
                    summary=f"アプリケーション層の {mod.path} が Web フレームワーク {imp.external} を import している（公開シグネチャには出ていない）",
                    facts=[f"import した名前: {', '.join(sorted(names))}"],
                    suggestion="ユースケースの内部で HTTP の概念（リクエスト・レスポンス・ステータス）を扱っていないか確かめる",
                    fix_cost="小",
                    impact="HTTP の概念がユースケースに入り込むと、Web 以外の入口から再利用しにくくなる",
                )
            )
    return out
