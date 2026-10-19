"""DDD-ENT-03: エンティティの状態を外から直接書き換えられる。"""

from __future__ import annotations

import re

from ..model import ClassDecl, Module
from . import Ctx, finding, register
from .common import dataclass_info, field_named, is_public_member, ts_mutable_collection

_SETTER_TS = re.compile(r"^set[A-Z]")
_SETTER_PY = re.compile(r"^set_[a-z0-9]")

_FIX_COST = "小〜中（フィールドを非公開にし、変更を意図を表すメソッドに寄せる。呼び出し側も直す）"
_IMPACT = "どこからでも状態を書き換えられ、不変条件の検証を通らない変更が紛れ込む"


def _ts(ctx: Ctx, mod: Module, cls: ClassDecl) -> list[dict]:
    out = []
    for f in cls.fields:
        if f.static:
            continue
        if f.origin == "field" and f.access == "public" and not f.name.startswith("#"):
            if not f.readonly:
                out.append(finding(
                    ctx, "DDD-ENT-03", mod, f.line,
                    summary=f"エンティティ {cls.name} のフィールド {f.name} が公開されていて、外から代入できる",
                    facts=[f"{cls.name}.{f.name}: 修飾子なし（public）、readonly なし"],
                    suggestion=f"{f.name} を private にし、変更は業務上の意図を表すメソッド経由にする",
                    fix_cost=_FIX_COST, impact=_IMPACT,
                ))
            elif ts_mutable_collection(f.type):
                out.append(_ts_collection(ctx, mod, cls, f.name, f.line, f.type))
        elif f.origin == "ctor_param" and f.access == "public" and not f.readonly:
            out.append(finding(
                ctx, "DDD-ENT-03", mod, f.line,
                summary=f"エンティティ {cls.name} のコンストラクタ引数プロパティ {f.name} が public で readonly でない",
                facts=[f"{cls.name}.{f.name}: public の引数プロパティ"],
                suggestion=f"{f.name} を private readonly にし、変更は意図を表すメソッド経由にする",
                fix_cost=_FIX_COST, impact=_IMPACT,
            ))
    for m in cls.methods:
        if m.static or not is_public_member(m.name, m.access, "typescript"):
            continue
        if m.kind == "set" and not m.has_guard:
            out.append(_setter(ctx, mod, cls, m.name, m.line, "set アクセサ"))
        elif m.kind == "method" and _SETTER_TS.match(m.name) and m.single_assignment_to:
            out.append(_setter(ctx, mod, cls, m.name, m.line, f"this.{m.single_assignment_to} への代入だけのメソッド"))
        elif m.kind == "get" and m.returns_self_field:
            backing = field_named(cls, m.returns_self_field)
            type_text = m.returns or (backing.type if backing else None)
            if ts_mutable_collection(type_text) or (backing is not None and ts_mutable_collection(backing.type)):
                out.append(_ts_collection(ctx, mod, cls, m.name, m.line, type_text or (backing.type if backing else "")))
    return out


def _ts_collection(ctx: Ctx, mod: Module, cls: ClassDecl, name: str, line: int, type_text: str | None) -> dict:
    return finding(
        ctx, "DDD-ENT-03", mod, line,
        verdict="borderline",
        summary=f"エンティティ {cls.name} の {name} は変更できるコレクション（{type_text}）をそのまま公開している",
        facts=[f"{cls.name}.{name}: {type_text}"],
        suggestion="ReadonlyArray・readonly T[] を返すか、コピーを返す。要素の追加・削除は意図を表すメソッドにする",
        fix_cost="小", impact="呼び出し側が中身を書き換えると、不変条件の検証を通らずに状態が変わる",
    )


def _setter(ctx: Ctx, mod: Module, cls: ClassDecl, name: str, line: int, what: str) -> dict:
    return finding(
        ctx, "DDD-ENT-03", mod, line,
        summary=f"エンティティ {cls.name} の {name} は検証なしで状態を書き換える（{what}）",
        facts=[f"{cls.name}.{name}: {what}（検証なし）"],
        suggestion=f"{name} をやめ、業務上の操作を表す名前のメソッドで、検証してから状態を変える",
        fix_cost=_FIX_COST, impact=_IMPACT,
    )


def _py(ctx: Ctx, mod: Module, cls: ClassDecl) -> list[dict]:
    out = []
    kind, frozen, _ = dataclass_info(cls)
    if kind is not None:
        if not frozen:
            for f in cls.fields:
                if f.origin == "py_class" and not f.name.startswith("_"):
                    out.append(finding(
                        ctx, "DDD-ENT-03", mod, f.line,
                        summary=f"エンティティ {cls.name}（frozen でない {kind}）のフィールド {f.name} を外から代入できる",
                        facts=[f"{cls.name}.{f.name}: frozen でない {kind} の公開フィールド"],
                        suggestion=f"{f.name} を _{f.name} にして property で読み取りだけを公開し、変更は意図を表すメソッドにする",
                        fix_cost=_FIX_COST, impact=_IMPACT,
                    ))
    else:
        for f in cls.fields:
            if f.origin == "py_init" and not f.name.startswith("_"):
                out.append(finding(
                    ctx, "DDD-ENT-03", mod, f.line,
                    summary=f"エンティティ {cls.name} の属性 self.{f.name} が公開されていて、外から代入できる",
                    facts=[f"{cls.name}.__init__ で self.{f.name} に代入"],
                    suggestion=f"self._{f.name} にして property で読み取りだけを公開し、変更は意図を表すメソッドにする",
                    fix_cost=_FIX_COST, impact=_IMPACT,
                ))
    for m in cls.methods:
        if m.static or not is_public_member(m.name, "public", "python"):
            continue
        if m.kind == "set" and not m.has_guard:
            out.append(_setter(ctx, mod, cls, m.name, m.line, "setter"))
        elif m.kind == "method" and _SETTER_PY.match(m.name) and m.single_assignment_to:
            out.append(_setter(ctx, mod, cls, m.name, m.line, f"self.{m.single_assignment_to} への代入だけのメソッド"))
        elif m.kind == "get" and m.returns_self_field and m.returns_self_field.startswith("_"):
            backing = field_named(cls, m.returns_self_field)
            if backing is not None and backing.init_kind in ("list", "dict", "set"):
                out.append(finding(
                    ctx, "DDD-ENT-03", mod, m.line,
                    verdict="borderline",
                    summary=f"エンティティ {cls.name} の property {m.name} は変更できる {backing.init_kind} をそのまま返している",
                    facts=[f"self.{backing.name} は {backing.init_kind} として初期化（{mod.path}:{backing.line}）"],
                    suggestion="tuple・frozenset・MappingProxyType にして返すか、コピーを返す",
                    fix_cost="小", impact="呼び出し側が中身を書き換えると、不変条件の検証を通らずに状態が変わる",
                ))
    return out


@register("ddd_ent_03")
def ddd_ent_03(ctx: Ctx) -> list[dict]:
    out = []
    for ref in ctx.domain.entities:
        if ref.module.lang == "typescript":
            out += _ts(ctx, ref.module, ref.cls)
        else:
            out += _py(ctx, ref.module, ref.cls)
    return out
