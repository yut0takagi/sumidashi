"""CA-DEP-01〜04: 依存の向きとフレームワーク依存、層をまたぐ循環。"""

from __future__ import annotations

from ..layers import DEPTH, allowed
from . import Ctx, finding, register

_LAYER_JA = {
    "domain": "ドメイン層",
    "application": "アプリケーション層",
    "adapter": "アダプタ層",
    "infrastructure": "インフラ層",
    "main": "main（組み立て）",
    "shared": "共有カーネル",
}


def _inward(ctx: Ctx, check_id: str, src_layer: str) -> list[dict]:
    out = []
    for mod in ctx.modules_in(src_layer):
        for imp in mod.imports:
            bad = [(d, ctx.layer_map.layer_of(d)) for d in imp.resolved]
            bad = [(d, layer) for d, layer in bad if layer is not None and not allowed(src_layer, layer)]
            if not bad:
                continue
            dst, dst_layer = bad[0]
            facts = [f"{mod.path}（{src_layer}）→ {d}（{layer}）" for d, layer in bad]
            if imp.type_only:
                facts.append("型だけの import（実行時には依存しない）")
            out.append(
                finding(
                    ctx, check_id, mod, imp.line, imp.end_line,
                    verdict="borderline" if imp.type_only else "violation",
                    summary=f"{_LAYER_JA[src_layer]}の {mod.path} が{_LAYER_JA[dst_layer]}の {dst} を import している",
                    facts=facts,
                    suggestion=(
                        f"{_LAYER_JA[src_layer]}に必要な振る舞いをインターフェース（ポート）として定義し、"
                        f"{dst} 側がそれを実装する形に向きを逆にする"
                    ),
                    fix_cost="中（ポートの定義と、実装側・組み立て側の変更）",
                    impact=f"{_LAYER_JA[dst_layer]}の変更が{_LAYER_JA[src_layer]}に波及し、単体でテストできなくなる",
                    files_to_change=3,
                )
            )
    return out


@register("ca_dep_01")
def ca_dep_01(ctx: Ctx) -> list[dict]:
    return _inward(ctx, "CA-DEP-01", "domain")


@register("ca_dep_03")
def ca_dep_03(ctx: Ctx) -> list[dict]:
    return _inward(ctx, "CA-DEP-03", "application")


def _categories(ctx: Ctx, mod, imp) -> list[tuple[str, str]]:
    """(モジュール名, 分類) の一覧。Python の from import はサブモジュールでも引く。"""
    names = [imp.external]
    if mod.lang == "python" and imp.kind == "py_from":
        names = [f"{imp.external}.{n}" for n in imp.py_names if n != "*"] + names
    out = []
    for name in names:
        cat = ctx.ledger.classify(name, mod.lang)
        if cat is not None:
            out.append((name, cat))
    return out


@register("ca_dep_02")
def ca_dep_02(ctx: Ctx) -> list[dict]:
    out = []
    for mod in ctx.modules_in("domain"):
        for imp in mod.imports:
            if not imp.external:
                continue
            cats = _categories(ctx, mod, imp)
            violating = [(n, c) for n, c in cats if ctx.ledger.is_violating(c)]
            validation = [(n, c) for n, c in cats if c == "validation"]
            if violating:
                name, cat = violating[0]
                hint = None
                if imp.type_only:
                    hint = {"to": "Medium", "rule": "deescalate", "reason": "型だけの import"}
                out.append(
                    finding(
                        ctx, "CA-DEP-02", mod, imp.line, imp.end_line,
                        summary=f"ドメイン層の {mod.path} が {imp.external}（分類: {cat}）を import している",
                        facts=[f"フレームワーク台帳の分類: {name} → {cat}"]
                        + (["型だけの import"] if imp.type_only else []),
                        fix_cost="中〜大（ドメインの型と永続化・通信の型を分け、変換を書く）",
                        impact="フレームワークの更新や差し替えがドメインのコードに波及し、業務ルールを単体でテストしにくくなる",
                        files_to_change=2,
                        severity_hint=hint,
                    )
                )
            elif validation:
                name, cat = validation[0]
                out.append(
                    finding(
                        ctx, "CA-DEP-02", mod, imp.line, imp.end_line,
                        verdict="borderline",
                        summary=f"ドメイン層の {mod.path} が入力検証ライブラリ {imp.external} を import している",
                        facts=[f"フレームワーク台帳の分類: {name} → validation"],
                        suggestion="業務ルールの表現に使っているならそのままでよい。外部入力の検証ならアダプタ層に移す",
                        fix_cost="小〜中",
                        impact="検証ライブラリの更新がドメインに波及する",
                    )
                )
    return out


@register("ca_dep_04")
def ca_dep_04(ctx: Ctx) -> list[dict]:
    lm = ctx.layer_map
    out = []
    strict = ctx.graph.sccs(include_type_only=False)
    for comp in ctx.graph.sccs(include_type_only=True):
        layers = {lm.layer_of(p) for p in comp} - {None}
        if len(layers) < 2:
            continue
        members = set(comp)
        runtime_cycle = any(
            set(c) <= members and len({lm.layer_of(p) for p in c} - {None}) >= 2 for c in strict
        )
        inner = [e for e in ctx.graph.edges if e.src in members and e.dst in members]

        def depth(p: str) -> int:
            layer = lm.layer_of(p)
            return DEPTH[layer] if layer is not None else 99

        outward = [e for e in inner if depth(e.src) < depth(e.dst) and lm.layer_of(e.dst) is not None]
        if outward:
            edge = min(outward, key=lambda e: (depth(e.src), e.src, e.line))
        else:
            crossing = [e for e in inner if lm.layer_of(e.src) != lm.layer_of(e.dst)] or inner
            edge = min(crossing, key=lambda e: (e.src, e.line))
        mod = ctx.modules[edge.src]
        facts = [f"循環に含まれるファイル: {', '.join(comp)}"]
        facts += [
            f"{e.src}:{e.line} → {e.dst}" + ("（型だけ）" if e.type_only else "")
            for e in sorted(inner, key=lambda e: (e.src, e.line))
        ]
        if not runtime_cycle:
            facts.append("型だけの import を除くと、層をまたぐ循環は残らない")
        out.append(
            finding(
                ctx, "CA-DEP-04", mod, edge.line, edge.end_line,
                verdict="violation" if runtime_cycle else "borderline",
                summary=(
                    f"{len(comp)} ファイルが {', '.join(sorted(layers, key=lambda x: DEPTH[x]))} をまたいで循環している。"
                    f"{edge.src} → {edge.dst} が内側から外側への依存"
                ),
                facts=facts,
                suggestion="内側から外側への import をやめ、内側にインターフェースを置いて外側が実装する（依存性逆転）",
                fix_cost="中（循環を切る1本の依存を逆転させる）",
                impact="どの層も単独で変更・テストできなくなり、変更の影響範囲が読めなくなる",
                files_to_change=2,
                touches=[(e.src, e.line, e.end_line) for e in inner],
            )
        )
    return out
