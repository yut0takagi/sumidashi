"""DDD-REP-02: リポジトリのインターフェースに ORM・DB の型が漏れている。"""

from __future__ import annotations

import re

from ..model import Module, words_in
from . import Ctx, finding, register
from .common import is_public_member

_QUERY_PARAMS = {"sql", "query", "where", "filter", "raw", "rawQuery", "condition", "conditions"}
_LOOSE_TS = re.compile(r"^(string|object|any|unknown|Record\s*<.*>)$")
_LOOSE_PY = re.compile(r"^(str|dict|Dict\[.*\]|dict\[.*\]|Mapping\[.*\]|typing\.Mapping\[.*\])$")


def _orm_names(ctx: Ctx, mod: Module) -> dict[str, str]:
    """ローカル名 → import 元。名前空間の別名も含む。"""
    names = {}
    for imp in mod.imports:
        if not imp.external:
            continue
        cands = [imp.external]
        if mod.lang == "python" and imp.kind == "py_from":
            cands = [f"{imp.external}.{n}" for n in imp.py_names] + cands
        if any(ctx.ledger.classify(c, mod.lang) in ("orm", "db") for c in cands):
            for local in imp.bindings:
                if local != "*":
                    names[local] = imp.external
    return names


def _loose(type_text: str | None, lang: str) -> bool:
    if not type_text:
        return False
    pattern = _LOOSE_TS if lang == "typescript" else _LOOSE_PY
    return bool(pattern.match(type_text.strip()))


@register("ddd_rep_02")
def ddd_rep_02(ctx: Ctx) -> list[dict]:
    out = []
    for mod in ctx.modules_in("domain", "application"):
        orm = _orm_names(ctx, mod)
        for cls in mod.classes:
            if cls.kind == "type_alias" or not cls.name.endswith(("Repository", "Repo")):
                continue
            for base, text in zip(cls.bases, cls.bases_text):
                hits = sorted((words_in(text) | {base}) & set(orm))
                if hits:
                    out.append(finding(
                        ctx, "DDD-REP-02", mod, cls.line,
                        summary=f"リポジトリ {cls.name} が ORM の型 {text} を継承・実装している",
                        facts=[f"{h} は {orm[h]} から import" for h in hits],
                        suggestion="ドメインの言葉だけで書いたリポジトリのインターフェースを置き、ORM を使う実装はインフラ層に移す",
                        fix_cost="中（インターフェースと実装を分け、呼び出し側を差し替える）",
                        impact="ドメイン・ユースケースが ORM に縛られ、永続化の方式を変えられず、テストで差し替えにくい",
                        files_to_change=3,
                    ))
            for m in cls.methods:
                if m.static or not is_public_member(m.name, m.access, mod.lang):
                    continue
                words = words_in(m.returns)
                for p in m.params:
                    words |= words_in(p.type)
                hits = sorted(words & set(orm))
                if hits:
                    out.append(finding(
                        ctx, "DDD-REP-02", mod, m.line,
                        summary=f"リポジトリ {cls.name}.{m.name} の引数か戻り値に ORM・DB の型 {', '.join(hits)} が出ている",
                        facts=[f"{h} は {orm[h]} から import" for h in hits],
                        suggestion="引数と戻り値をドメインの型（集約・値オブジェクト・ID）にし、ORM の型との変換は実装側で行う",
                        fix_cost="中（シグネチャの変更と、実装・呼び出し側の変換）",
                        impact="ドメイン・ユースケースが ORM の型に依存し、永続化の詳細が業務ロジックに漏れる",
                        files_to_change=3,
                    ))
                    continue
                loose = [p for p in m.params if p.name in _QUERY_PARAMS and _loose(p.type, mod.lang)]
                if loose:
                    p = loose[0]
                    out.append(finding(
                        ctx, "DDD-REP-02", mod, m.line,
                        verdict="borderline",
                        summary=f"リポジトリ {cls.name}.{m.name} が問い合わせ条件 {p.name}: {p.type} をそのまま受け取っている",
                        facts=[f"{p.name}: {p.type}"],
                        suggestion="条件を業務の言葉で表すメソッド（findActiveByCustomer など）か、仕様（Specification）の型にする",
                        fix_cost="小〜中",
                        impact="SQL や ORM の条件の書き方が呼び出し側に漏れる",
                    ))
    return out
