"""DDD-VO-02: 値オブジェクトが変更できる。"""

from __future__ import annotations

from ..model import ClassDecl, Module
from . import Ctx, finding, register
from .common import dataclass_info, py_mutable_annotation, ts_mutable_collection

_TS_ARRAY_MUTATORS = {"push", "pop", "shift", "unshift", "splice", "sort", "reverse"}
_PY_INIT_METHODS = {"__init__", "__post_init__", "__new__", "__setstate__"}

_FIX_COST = "小（readonly・frozen にし、変更は新しいインスタンスを返すメソッドにする）"
_IMPACT = "共有された値が別の場所で書き換わり、等価性やハッシュに頼る処理が壊れる"


def _f(ctx: Ctx, mod: Module, line: int, summary: str, fact: str, suggestion: str, *, verdict="violation", diff=None):
    return finding(
        ctx, "DDD-VO-02", mod, line, verdict=verdict, summary=summary, facts=[fact],
        suggestion=suggestion, diff=diff, fix_cost=_FIX_COST, impact=_IMPACT,
    )


def _ts(ctx: Ctx, mod: Module, cls: ClassDecl) -> list[dict]:
    out = []
    for f in cls.fields:
        if f.static:
            continue
        public = f.access == "public" and not f.name.startswith("#")
        if f.origin == "field" and public and not f.readonly:
            line = mod.line_text(f.line)
            diff = None
            if line.lstrip().startswith(f.name) or line.lstrip().startswith(f"public {f.name}"):
                new = line.replace(f"public {f.name}", f"readonly {f.name}", 1)
                if new == line:
                    new = line.replace(f.name, f"readonly {f.name}", 1)
                diff = f"--- a/{mod.path}\n+++ b/{mod.path}\n@@ -{f.line} +{f.line} @@\n-{line}\n+{new}\n"
            out.append(_f(
                ctx, mod, f.line,
                f"値オブジェクト {cls.name} のフィールド {f.name} が readonly でない",
                f"{cls.name}.{f.name}: 公開・readonly なし",
                f"{f.name} を readonly にし、値を変えたいときは新しいインスタンスを返すメソッドにする",
                diff=diff,
            ))
        elif f.origin == "ctor_param" and f.access == "public" and not f.readonly:
            out.append(_f(
                ctx, mod, f.line,
                f"値オブジェクト {cls.name} の引数プロパティ {f.name} が public で readonly でない",
                f"{cls.name}.{f.name}: public の引数プロパティ",
                f"public readonly {f.name} にする",
            ))
        elif public and f.readonly and ts_mutable_collection(f.type):
            out.append(_f(
                ctx, mod, f.line,
                f"値オブジェクト {cls.name} の {f.name} は readonly だが、中身を変更できるコレクション（{f.type}）",
                f"{cls.name}.{f.name}: {f.type}",
                "ReadonlyArray・readonly T[]・ReadonlyMap にする",
                verdict="borderline",
            ))
    for m in cls.methods:
        if m.kind == "set":
            out.append(_f(
                ctx, mod, m.line,
                f"値オブジェクト {cls.name} に set アクセサ {m.name} がある",
                f"{cls.name}.{m.name}: set アクセサ",
                f"set アクセサをやめ、with{m.name[:1].upper()}{m.name[1:]}() のように新しいインスタンスを返す",
            ))
            continue
        if m.kind == "constructor" or m.static:
            continue
        for name, line in m.self_assignments:
            out.append(_f(
                ctx, mod, line,
                f"値オブジェクト {cls.name} のメソッド {m.name} が this.{name} を書き換えている",
                f"{cls.name}.{m.name}: this.{name} への代入",
                "自分を書き換えず、新しい値で作ったインスタンスを返す",
            ))
        for name, method, line in m.self_mutator_calls:
            if method in _TS_ARRAY_MUTATORS:
                out.append(_f(
                    ctx, mod, line,
                    f"値オブジェクト {cls.name} のメソッド {m.name} が this.{name}.{method}() で中身を変えている",
                    f"{cls.name}.{m.name}: this.{name}.{method}()",
                    "配列をコピーして変更し、新しいインスタンスを返す",
                ))
    return out


def _py(ctx: Ctx, mod: Module, cls: ClassDecl) -> list[dict]:
    out = []
    kind, frozen, deco_line = dataclass_info(cls)
    if kind is not None and not frozen:
        deco = mod.line_text(deco_line)
        diff = None
        if deco.strip() in ("@dataclass", "@dataclasses.dataclass", "@dataclass()"):
            name = deco.strip().rstrip("()")
            new = deco.replace(deco.strip(), f"{name}(frozen=True)")
            diff = f"--- a/{mod.path}\n+++ b/{mod.path}\n@@ -{deco_line} +{deco_line} @@\n-{deco}\n+{new}\n"
        out.append(_f(
            ctx, mod, deco_line,
            f"値オブジェクト {cls.name} が frozen でない {kind}",
            f"{cls.name}: {deco.strip()}",
            "frozen=True にし、値を変えたいときは dataclasses.replace() などで新しいインスタンスを作る",
            diff=diff,
        ))
    if kind is None:
        for f in cls.fields:
            if f.origin == "py_init" and not f.name.startswith("_"):
                out.append(_f(
                    ctx, mod, f.line,
                    f"値オブジェクト {cls.name} の属性 self.{f.name} を外から代入できる",
                    f"{cls.name}.__init__ で self.{f.name} に代入",
                    "frozen な dataclass にするか、self._x と読み取り専用の property にする",
                ))
    if kind is not None and frozen:
        for f in cls.fields:
            if f.origin == "py_class" and py_mutable_annotation(f.type):
                out.append(_f(
                    ctx, mod, f.line,
                    f"値オブジェクト {cls.name} は frozen だが、{f.name} の型 {f.type} は中身を変更できる",
                    f"{cls.name}.{f.name}: {f.type}",
                    "tuple・frozenset・Mapping にする",
                    verdict="borderline",
                ))
    for m in cls.methods:
        if m.kind == "set":
            out.append(_f(
                ctx, mod, m.line,
                f"値オブジェクト {cls.name} に setter {m.name} がある",
                f"{cls.name}.{m.name}: @{m.name}.setter",
                "setter をやめ、新しいインスタンスを返すメソッドにする",
            ))
            continue
        if m.name in _PY_INIT_METHODS or m.static:
            continue
        for name, line in m.self_assignments:
            out.append(_f(
                ctx, mod, line,
                f"値オブジェクト {cls.name} のメソッド {m.name} が self.{name} を書き換えている",
                f"{cls.name}.{m.name}: self.{name} への代入",
                "自分を書き換えず、新しい値で作ったインスタンスを返す",
            ))
    return out


@register("ddd_vo_02")
def ddd_vo_02(ctx: Ctx) -> list[dict]:
    out = []
    for ref in ctx.domain.value_objects:
        if ref.module.lang == "typescript":
            out += _ts(ctx, ref.module, ref.cls)
        else:
            out += _py(ctx, ref.module, ref.cls)
    return out
