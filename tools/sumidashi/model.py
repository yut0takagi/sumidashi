"""言語に依存しないコードの中間モデル。

TypeScript と Python のパーサがこの形に落とし、チェックはこの形だけを見る。
行番号はすべて1始まり。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def words_in(text: str | None) -> set[str]:
    """型注釈などの文字列に出る識別子の集合。`Prisma.OrderWhereInput` は Prisma と OrderWhereInput の両方を返す。"""
    if not text:
        return set()
    return set(_WORD.findall(text))


@dataclass
class Import:
    line: int
    end_line: int
    specifier: str
    """書かれたままのモジュール指定（'../infra/db'、'express'、'shop.domain.order'）。Python の相対 import は先頭に '.' を付ける。"""
    kind: str
    """import / reexport / require / dynamic / py_import / py_from"""
    type_only: bool = False
    bindings: dict[str, str] = field(default_factory=dict)
    """ローカル名 → 元の名前。名前空間 import と default import は元の名前を '*' / 'default' にする。"""
    py_names: list[str] = field(default_factory=list)
    """Python の from import で取り込む名前（元の名前）。サブモジュールの解決に使う。"""
    resolved: list[str] = field(default_factory=list)
    """解決できたリポジトリ内のファイル（ルートからの相対パス）。"""
    external: str | None = None
    """解決できなかった場合の書かれたままのモジュール名。フレームワーク台帳はこれを前方一致で引く。"""


@dataclass
class Param:
    name: str
    type: str | None
    line: int


@dataclass
class Function:
    name: str
    line: int
    """名前の行"""
    start_line: int
    end_line: int
    params: list[Param] = field(default_factory=list)
    returns: str | None = None
    kind: str = "method"
    """function / method / constructor / get / set"""
    access: str = "public"
    """public / private / protected"""
    exported: bool = True
    static: bool = False
    abstract: bool = False
    decorators: list[str] = field(default_factory=list)
    has_guard: bool = False
    self_assignments: list[tuple[str, int]] = field(default_factory=list)
    """this.x / self.x への代入・複合代入・++/-- の (フィールド名, 行)"""
    self_mutator_calls: list[tuple[str, str, int]] = field(default_factory=list)
    """this.x.push(...) のような (フィールド名, メソッド名, 行)"""
    single_assignment_to: str | None = None
    """本体が this.x / self.x への代入1文だけなら、そのフィールド名"""
    returns_self_field: str | None = None
    """本体が return this.x / return self.x だけなら、そのフィールド名"""
    body_text: str = ""


@dataclass
class Field:
    name: str
    line: int
    type: str | None = None
    access: str = "public"
    readonly: bool = False
    static: bool = False
    origin: str = "field"
    """field / ctor_param / py_class / py_init"""
    init_kind: str | None = None
    """Python の初期値の種類: list / dict / set"""


@dataclass
class Decorator:
    name: str
    """dataclass、define、attr.s、x.setter など"""
    args: str = ""
    line: int = 0


@dataclass
class ClassDecl:
    name: str
    line: int
    start_line: int
    end_line: int
    kind: str = "class"
    """class / abstract_class / interface / type_alias"""
    exported: bool = True
    bases: list[str] = field(default_factory=list)
    """継承・実装する型の名前（型引数を除いた名前）"""
    bases_text: list[str] = field(default_factory=list)
    """継承・実装する型の書かれたままの文字列"""
    decorators: list[Decorator] = field(default_factory=list)
    fields: list[Field] = field(default_factory=list)
    methods: list[Function] = field(default_factory=list)

    def member_names(self) -> set[str]:
        return {f.name for f in self.fields} | {m.name for m in self.methods}

    def decorator(self, *names: str) -> Decorator | None:
        for d in self.decorators:
            if d.name in names or d.name.split(".")[-1] in names:
                return d
        return None


@dataclass
class Module:
    path: str
    lang: str
    """typescript / python"""
    lines: list[str]
    imports: list[Import] = field(default_factory=list)
    classes: list[ClassDecl] = field(default_factory=list)
    functions: list[Function] = field(default_factory=list)
    parse_errors: int = 0

    @property
    def loc(self) -> int:
        return sum(1 for line in self.lines if line.strip())

    def line_text(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1]
        return ""

    def snippet(self, start: int, end: int, limit: int = 10) -> str:
        end = min(end, start + limit - 1)
        return "\n".join(self.lines[start - 1 : end])
