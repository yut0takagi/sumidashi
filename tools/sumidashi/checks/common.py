"""チェックに共通する判定: エンティティ・値オブジェクト・集約らしき型、コレクション型、dataclass。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..model import ClassDecl, Field, Function, Module, words_in

_EXCLUDED_SUFFIXES = ("Dto", "DTO", "Props", "Input", "Output", "Command", "Query", "Event", "Error", "Exception")
_VO_EXTRA_SUFFIXES = ("Config", "Settings")
_ID_NAMES = {"id", "_id", "#id"}


def snake_case(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _identifier_names(cls: ClassDecl, lang: str) -> set[str]:
    names = set(_ID_NAMES)
    if lang == "typescript":
        names.add(cls.name[:1].lower() + cls.name[1:] + "Id")
    else:
        names.add(snake_case(cls.name) + "_id")
    return names


def has_identifier(cls: ClassDecl, lang: str) -> bool:
    ids = _identifier_names(cls, lang)
    if any(f.name in ids for f in cls.fields):
        return True
    return any(m.name in ids and m.kind == "get" for m in cls.methods)


def _inherits_value_object(cls: ClassDecl) -> bool:
    return any("ValueObject" in b for b in cls.bases)


# ------------------------------------------------------------------ Python の dataclass・attrs
_DATACLASS = ("dataclass",)
_ATTRS_MUTABLE = ("define", "mutable", "s", "attrs")
_ATTRS_FROZEN = ("frozen",)


def _frozen_arg(args: str) -> bool:
    return bool(re.search(r"\bfrozen\s*=\s*True\b", args or ""))


def dataclass_info(cls: ClassDecl) -> tuple[str | None, bool, int]:
    """(種類 'dataclass'・'attrs'・None, frozen か, デコレータの行)"""
    for d in cls.decorators:
        last = d.name.split(".")[-1]
        if last in _DATACLASS:
            return "dataclass", _frozen_arg(d.args), d.line
        if d.name in ("attr.s", "attr.attrs", "attrs.define", "attrs.mutable", "attr.define", "attr.mutable") or (
            "." not in d.name and last in ("define", "mutable")
        ):
            return "attrs", _frozen_arg(d.args), d.line
        if d.name in ("attrs.frozen", "attr.frozen") or ("." not in d.name and last in _ATTRS_FROZEN):
            return "attrs", True, d.line
    return None, False, 0


# ------------------------------------------------------------------ コレクション型
_TS_MUTABLE_HEAD = re.compile(r"^(Array|Map|Set|Record|WeakMap|WeakSet)\s*<")
_TS_IMMUTABLE_HEAD = re.compile(r"^(ReadonlyArray|ReadonlyMap|ReadonlySet|Readonly)\s*<")


def _split_top(text: str, sep: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def ts_mutable_collection(type_text: str | None) -> bool:
    if not type_text:
        return False
    for part in _split_top(type_text, "|"):
        if part.startswith("readonly ") or _TS_IMMUTABLE_HEAD.match(part):
            continue
        if part.startswith("[") and part.endswith("]"):
            continue  # タプル
        if part.endswith("[]") or _TS_MUTABLE_HEAD.match(part):
            return True
    return False


_PY_MUTABLE_HEADS = {"list", "List", "dict", "Dict", "set", "Set"}


def py_mutable_annotation(type_text: str | None) -> bool:
    if not type_text:
        return False
    for part in _split_top(type_text, "|"):
        head = re.split(r"[\[\s]", part.strip(), maxsplit=1)[0].split(".")[-1]
        if head in _PY_MUTABLE_HEADS:
            return True
        if head == "Optional":
            inner = part[part.find("[") + 1 : part.rfind("]")]
            if py_mutable_annotation(inner):
                return True
    return False


# ------------------------------------------------------------------ 公開かどうか
def is_public_member(name: str, access: str, lang: str) -> bool:
    if lang == "typescript":
        return access == "public" and not name.startswith("#")
    if name.startswith("__") and name.endswith("__"):
        return True
    return not name.startswith("_")


def public_methods(cls: ClassDecl, lang: str) -> list[Function]:
    return [m for m in cls.methods if is_public_member(m.name, m.access, lang)]


def field_named(cls: ClassDecl, name: str) -> Field | None:
    for f in cls.fields:
        if f.name == name:
            return f
    return None


# ------------------------------------------------------------------ ドメインのモデル
@dataclass
class TypeRef:
    module: Module
    cls: ClassDecl

    @property
    def key(self) -> str:
        return f"{self.module.path}::{self.cls.name}"


@dataclass
class DomainModel:
    entities: list[TypeRef] = field(default_factory=list)
    value_objects: list[TypeRef] = field(default_factory=list)
    aggregates: dict[str, list[str]] = field(default_factory=dict)
    """集約らしき型: ルートのエンティティ名 → 所有する子のエンティティ名"""

    def entity_names(self) -> set[str]:
        return {t.cls.name for t in self.entities}

    def as_dict(self) -> dict:
        return {
            "entities": [{"name": t.cls.name, "file": t.module.path, "line": t.cls.line} for t in self.entities],
            "value_objects": [{"name": t.cls.name, "file": t.module.path, "line": t.cls.line} for t in self.value_objects],
            "aggregate_candidates": [
                {"root": root, "children": children} for root, children in sorted(self.aggregates.items())
            ],
        }


def classify_domain_types(domain_modules: list[Module]) -> DomainModel:
    dm = DomainModel()
    for mod in domain_modules:
        for cls in mod.classes:
            if cls.kind not in ("class", "abstract_class"):
                continue
            if has_identifier(cls, mod.lang):
                if cls.name.endswith(_EXCLUDED_SUFFIXES) or _inherits_value_object(cls):
                    continue
                dm.entities.append(TypeRef(mod, cls))
                continue
            if cls.name.endswith(_EXCLUDED_SUFFIXES + _VO_EXTRA_SUFFIXES):
                continue
            is_vo = (
                _inherits_value_object(cls)
                or any(m.name in ("equals", "__eq__") for m in cls.methods)
                or dataclass_info(cls)[0] is not None
            )
            if is_vo:
                dm.value_objects.append(TypeRef(mod, cls))
    names = dm.entity_names()
    for ref in dm.entities:
        children = set()
        for f in ref.cls.fields:
            for w in words_in(f.type) & names:
                if w != ref.cls.name:
                    children.add(w)
        if children:
            dm.aggregates[ref.cls.name] = sorted(children)
    return dm
