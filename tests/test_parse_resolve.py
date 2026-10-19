import pathlib
import textwrap

from sumidashi.parse_py import parse_python
from sumidashi.parse_ts import parse_typescript
from sumidashi.resolve import Resolver, _strip_jsonc


def ts(src: str):
    return parse_typescript("src/a.ts", textwrap.dedent(src).encode())


def py(src: str, path="pkg/a.py"):
    return parse_python(path, textwrap.dedent(src).encode())


def test_ts_type_only_imports():
    m = ts("""
        import type { A } from "./a";
        import { type B, type C } from "./b";
        import { D, type E } from "./d";
        export type { F } from "./f";
    """)
    assert [i.type_only for i in m.imports] == [True, True, False, True]
    assert m.imports[3].kind == "reexport"


def test_ts_class_members():
    m = ts("""
        export class Order {
          id: string;
          readonly lines: Line[] = [];
          #secret = 1;
          constructor(public status: string, private readonly total: number, plain: number) {}
          set note(v: string) { this._note = v; }
          get items() { return this.lines; }
          setStatus(s: string) { this.status = s; }
          rename(n: string) { if (!n) throw new Error(); this.name = n; }
        }
    """)
    cls = m.classes[0]
    fields = {f.name: f for f in cls.fields}
    assert fields["id"].access == "public" and not fields["id"].readonly
    assert fields["lines"].readonly
    assert fields["#secret"].access == "private"
    assert fields["status"].origin == "ctor_param" and fields["status"].access == "public"
    assert "plain" not in fields
    methods = {f.name: f for f in cls.methods}
    assert methods["note"].kind == "set" and not methods["note"].has_guard
    assert methods["items"].returns_self_field == "lines"
    assert methods["setStatus"].single_assignment_to == "status"
    assert methods["rename"].has_guard


def test_py_type_checking_and_dataclass():
    m = py("""
        from dataclasses import dataclass, field
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from pkg.infra import Row

        @dataclass(frozen=True)
        class Money:
            amount: int
            tags: list[str] = field(default_factory=list)

        class Customer:
            def __init__(self, customer_id: str):
                self.customer_id = customer_id
                self._orders = []

            @property
            def orders(self):
                return self._orders

            @orders.setter
            def orders(self, v):
                self._orders = v
    """)
    assert [i.type_only for i in m.imports] == [False, False, True]
    money, customer = m.classes
    assert money.decorator("dataclass").args.replace(" ", "") == "(frozen=True)"
    assert {f.name: f.init_kind for f in money.fields}["tags"] == "list"
    fields = {f.name: f for f in customer.fields}
    assert fields["_orders"].init_kind == "list"
    kinds = [(f.name, f.kind) for f in customer.methods]
    assert ("orders", "get") in kinds and ("orders", "set") in kinds


def test_strip_jsonc():
    text = '{\n // c\n "a": "http://x", /* b */ "b": [1, 2,],\n}'
    assert _strip_jsonc(text).replace(" ", "").replace("\n", "") == '{"a":"http://x","b":[1,2]}'


def test_resolve_ts_paths_and_extends(make_repo):
    root = make_repo({
        "tsconfig.base.json": '{ "compilerOptions": { "baseUrl": ".", "paths": { "@app/*": ["src/*"] } } }',
        "tsconfig.json": '{ // コメント\n "extends": "./tsconfig.base.json" }',
        "src/domain/order.ts": "export class Order {}\n",
        "src/domain/index.ts": "export * from './order';\n",
        "src/app/use.ts": 'import { Order } from "@app/domain/order";\nimport x from "../domain";\nimport y from "../domain/order.js";\nimport z from "express";\n',
    })
    files = {"src/domain/order.ts", "src/domain/index.ts", "src/app/use.ts"}
    r = Resolver(root, files, [".", "src"])
    m = parse_typescript("src/app/use.ts", (root / "src/app/use.ts").read_bytes())
    r.resolve(m)
    assert [i.resolved for i in m.imports[:3]] == [["src/domain/order.ts"], ["src/domain/index.ts"], ["src/domain/order.ts"]]
    assert m.imports[3].external == "express"


def test_resolve_python(make_repo):
    root = make_repo({
        "src/shop/__init__.py": "",
        "src/shop/domain/__init__.py": "",
        "src/shop/domain/order.py": "class Order: ...\n",
        "src/shop/app/__init__.py": "",
        "src/shop/app/use.py": "from shop.domain.order import Order\nfrom ..domain import order\nfrom . import nothing\nimport sqlalchemy.orm\n",
    })
    files = {str(p.relative_to(root)) for p in pathlib.Path(root).rglob("*.py")}
    r = Resolver(root, files, [".", "src"])
    m = parse_python("src/shop/app/use.py", (root / "src/shop/app/use.py").read_bytes())
    r.resolve(m)
    assert m.imports[0].resolved == ["src/shop/domain/order.py"]
    assert m.imports[1].resolved == ["src/shop/domain/order.py"]
    assert m.imports[2].resolved == ["src/shop/app/__init__.py"]
    assert m.imports[3].external == "sqlalchemy.orm"
