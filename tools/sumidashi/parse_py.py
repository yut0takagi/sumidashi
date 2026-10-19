"""Python を tree-sitter で読み、中間モデル（model.py）に落とす。"""

from __future__ import annotations

import re

import tree_sitter_python as tsp
from tree_sitter import Language, Node, Parser

from .model import ClassDecl, Decorator, Field, Function, Import, Module, Param

_LANG = Language(tsp.language())

GUARD_CALL = re.compile(r"^(assert|validate|ensure|check|guard|invariant)", re.IGNORECASE)
COLLECTION_MUTATORS = {
    "append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse",
    "update", "add", "discard", "setdefault", "popitem",
}
_COLLECTION_CALLS = {"list": "list", "dict": "dict", "set": "set", "defaultdict": "dict", "OrderedDict": "dict", "deque": "list"}


class _Src:
    def __init__(self, data: bytes):
        self.data = data

    def text(self, node: Node | None) -> str:
        if node is None:
            return ""
        return self.data[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _end_line(node: Node) -> int:
    return node.end_point[0] + 1


def _walk(node: Node, skip_nested_defs: bool = False):
    stack = [node]
    first = True
    while stack:
        n = stack.pop()
        if skip_nested_defs and not first and n.type in ("function_definition", "class_definition", "lambda"):
            continue
        first = False
        yield n
        stack.extend(reversed(n.children))


def _in_type_checking(node: Node, src: _Src) -> bool:
    p = node.parent
    while p is not None:
        if p.type == "if_statement":
            cond = p.child_by_field_name("condition")
            if cond is not None and src.text(cond).strip() in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
                return True
        p = p.parent
    return False


def parse_python(path: str, data: bytes) -> Module:
    tree = Parser(_LANG).parse(data)
    src = _Src(data)
    mod = Module(path=path, lang="python", lines=data.decode("utf-8", "replace").splitlines())
    root = tree.root_node
    for n in _walk(root):
        if n.type == "ERROR":
            mod.parse_errors += 1
        elif n.type == "import_statement":
            _import(src, mod, n)
        elif n.type == "import_from_statement":
            _import_from(src, mod, n)
    for node in root.children:
        decorators: list[Node] = []
        target = node
        if node.type == "decorated_definition":
            decorators = [c for c in node.children if c.type == "decorator"]
            target = node.child_by_field_name("definition")
        if target is None:
            continue
        if target.type == "class_definition":
            mod.classes.append(_class(src, target, decorators))
        elif target.type == "function_definition":
            fn = _function(src, target, decorators)
            fn.kind = "function"
            fn.exported = not fn.name.startswith("_")
            mod.functions.append(fn)
    mod.imports.sort(key=lambda i: (i.line, i.specifier))
    return mod


def _import(src: _Src, mod: Module, node: Node) -> None:
    type_only = _in_type_checking(node, src)
    for c in node.named_children:
        if c.type == "dotted_name":
            name = src.text(c)
            bindings = {name.split(".")[0]: name.split(".")[0]}
        elif c.type == "aliased_import":
            name = src.text(c.child_by_field_name("name"))
            bindings = {src.text(c.child_by_field_name("alias")): "*"}
        else:
            continue
        mod.imports.append(
            Import(
                line=_line(node),
                end_line=_end_line(node),
                specifier=name,
                kind="py_import",
                type_only=type_only,
                bindings=bindings,
            )
        )


def _import_from(src: _Src, mod: Module, node: Node) -> None:
    module_node = node.child_by_field_name("module_name")
    if module_node is None:
        return
    if module_node.type == "relative_import":
        prefix = next((c for c in module_node.children if c.type == "import_prefix"), None)
        dotted = next((c for c in module_node.children if c.type == "dotted_name"), None)
        spec = src.text(prefix) + (src.text(dotted) if dotted is not None else "")
    else:
        spec = src.text(module_node)
    bindings: dict[str, str] = {}
    names: list[str] = []
    for i, c in enumerate(node.children):
        if node.field_name_for_child(i) != "name":
            continue
        if c.type == "dotted_name":
            n = src.text(c)
            bindings[n] = n
            names.append(n)
        elif c.type == "aliased_import":
            n = src.text(c.child_by_field_name("name"))
            bindings[src.text(c.child_by_field_name("alias"))] = n
            names.append(n)
    if any(c.type == "wildcard_import" for c in node.children):
        bindings["*"] = "*"
    mod.imports.append(
        Import(
            line=_line(node),
            end_line=_end_line(node),
            specifier=spec,
            kind="py_from",
            type_only=_in_type_checking(node, src),
            bindings=bindings,
            py_names=names,
        )
    )


def _decorator(src: _Src, node: Node) -> Decorator:
    expr = next((c for c in node.named_children), None)
    if expr is None:
        return Decorator(name="", line=_line(node))
    if expr.type == "call":
        fn = expr.child_by_field_name("function")
        args = expr.child_by_field_name("arguments")
        return Decorator(name=src.text(fn), args=src.text(args), line=_line(node))
    return Decorator(name=src.text(expr), line=_line(node))


def _collection_kind(src: _Src, node: Node | None) -> str | None:
    if node is None:
        return None
    if node.type in ("list", "list_comprehension"):
        return "list"
    if node.type in ("dictionary", "dictionary_comprehension"):
        return "dict"
    if node.type in ("set", "set_comprehension"):
        return "set"
    if node.type == "call":
        fn = src.text(node.child_by_field_name("function")).split(".")[-1]
        if fn in _COLLECTION_CALLS:
            return _COLLECTION_CALLS[fn]
        if fn == "field":  # dataclasses.field(default_factory=list)
            m = re.search(r"default_factory\s*=\s*(\w+)", src.text(node))
            if m and m.group(1) in _COLLECTION_CALLS:
                return _COLLECTION_CALLS[m.group(1)]
    return None


def _annotation_kind(text: str | None) -> str | None:
    if not text:
        return None
    head = re.split(r"[\[\s|]", text.strip(), maxsplit=1)[0].split(".")[-1]
    return {
        "list": "list", "List": "list", "MutableSequence": "list",
        "dict": "dict", "Dict": "dict", "MutableMapping": "dict", "defaultdict": "dict",
        "set": "set", "Set": "set", "MutableSet": "set",
    }.get(head)


def _self_attr(node: Node | None, src: _Src) -> str | None:
    if node is None or node.type != "attribute":
        return None
    obj = node.child_by_field_name("object")
    if obj is not None and obj.type == "identifier" and src.text(obj) == "self":
        return src.text(node.child_by_field_name("attribute"))
    return None


def _class(src: _Src, node: Node, decorators: list[Node]) -> ClassDecl:
    name = node.child_by_field_name("name")
    bases: list[str] = []
    bases_text: list[str] = []
    supers = node.child_by_field_name("superclasses")
    if supers is not None:
        for b in supers.named_children:
            if b.type == "keyword_argument":
                continue
            text = src.text(b)
            bases_text.append(text)
            bases.append(src.text(b.child_by_field_name("value")) if b.type == "subscript" else text)
    cls = ClassDecl(
        name=src.text(name),
        line=_line(name),
        start_line=_line(decorators[0]) if decorators else _line(node),
        end_line=_end_line(node),
        kind="class",
        exported=not src.text(name).startswith("_"),
        bases=bases,
        bases_text=bases_text,
        decorators=[_decorator(src, d) for d in decorators],
    )
    body = node.child_by_field_name("body")
    if body is None:
        return cls
    for stmt in body.named_children:
        decs: list[Node] = []
        target = stmt
        if stmt.type == "decorated_definition":
            decs = [c for c in stmt.children if c.type == "decorator"]
            target = stmt.child_by_field_name("definition")
        if target is None:
            continue
        if target.type == "function_definition":
            fn = _function(src, target, decs)
            cls.methods.append(fn)
            if fn.name == "__init__":
                cls.fields.extend(_init_fields(src, target, fn))
        elif target.type == "expression_statement":
            assign = target.named_children[0] if target.named_children else None
            if assign is not None and assign.type == "assignment":
                left = assign.child_by_field_name("left")
                type_node = assign.child_by_field_name("type")
                if left is not None and left.type == "identifier" and type_node is not None:
                    ann = src.text(type_node)
                    if ann.startswith("ClassVar"):
                        continue
                    fname = src.text(left)
                    cls.fields.append(
                        Field(
                            name=fname,
                            line=_line(left),
                            type=ann,
                            access="private" if fname.startswith("_") else "public",
                            origin="py_class",
                            init_kind=_collection_kind(src, assign.child_by_field_name("right")) or _annotation_kind(ann),
                        )
                    )
    return cls


def _init_fields(src: _Src, init: Node, fn: Function) -> list[Field]:
    param_types = {p.name: p.type for p in fn.params}
    out: list[Field] = []
    seen: set[str] = set()
    body = init.child_by_field_name("body")
    for n in _walk(body, skip_nested_defs=True) if body is not None else []:
        if n.type != "assignment":
            continue
        attr = _self_attr(n.child_by_field_name("left"), src)
        if attr is None or attr in seen:
            continue
        seen.add(attr)
        right = n.child_by_field_name("right")
        ann_node = n.child_by_field_name("type")
        ann = src.text(ann_node) if ann_node is not None else None
        if ann is None and right is not None and right.type == "identifier":
            ann = param_types.get(src.text(right))
        out.append(
            Field(
                name=attr,
                line=_line(n),
                type=ann,
                access="private" if attr.startswith("_") else "public",
                origin="py_init",
                init_kind=_collection_kind(src, right) or _annotation_kind(ann),
            )
        )
    return out


def _params(src: _Src, node: Node | None) -> list[Param]:
    out: list[Param] = []
    if node is None:
        return out
    for p in node.named_children:
        if p.type == "identifier":
            out.append(Param(name=src.text(p), type=None, line=_line(p)))
        elif p.type in ("typed_parameter", "default_parameter", "typed_default_parameter"):
            name_node = p.child_by_field_name("name") or next(
                (c for c in p.named_children if c.type == "identifier"), None
            )
            out.append(Param(name=src.text(name_node), type=src.text(p.child_by_field_name("type")) or None, line=_line(p)))
    if out and out[0].name in ("self", "cls"):
        out = out[1:]
    return out


def _is_trivial_body(src: _Src, body: Node | None) -> bool:
    if body is None:
        return True
    stmts = [c for c in body.named_children if c.type != "comment"]
    if stmts and stmts[0].type == "expression_statement" and stmts[0].named_children and stmts[0].named_children[0].type == "string":
        stmts = stmts[1:]
    if not stmts:
        return True
    if len(stmts) == 1:
        s = stmts[0]
        text = src.text(s).strip()
        if s.type == "pass_statement" or text == "...":
            return True
        if s.type == "raise_statement" and "NotImplementedError" in text:
            return True
    return False


def _function(src: _Src, node: Node, decorators: list[Node]) -> Function:
    name = node.child_by_field_name("name")
    name_text = src.text(name)
    decs = [_decorator(src, d) for d in decorators]
    dec_names = [d.name for d in decs]
    kind = "method"
    if name_text == "__init__":
        kind = "constructor"
    elif "property" in dec_names or "cached_property" in dec_names or "functools.cached_property" in dec_names:
        kind = "get"
    elif any(d.endswith(".setter") for d in dec_names):
        kind = "set"
    is_dunder = name_text.startswith("__") and name_text.endswith("__")
    body = node.child_by_field_name("body")
    fn = Function(
        name=name_text,
        line=_line(name),
        start_line=_line(decorators[0]) if decorators else _line(node),
        end_line=_end_line(node),
        params=_params(src, node.child_by_field_name("parameters")),
        returns=src.text(node.child_by_field_name("return_type")) or None,
        kind=kind,
        access="private" if name_text.startswith("_") and not is_dunder else "public",
        static="staticmethod" in dec_names,
        abstract=any(d.split(".")[-1] == "abstractmethod" for d in dec_names) or _is_trivial_body(src, body),
        decorators=dec_names,
    )
    if body is None:
        return fn
    fn.body_text = src.text(body)
    for n in _walk(body, skip_nested_defs=True):
        if n.type in ("if_statement", "raise_statement", "assert_statement"):
            fn.has_guard = True
        elif n.type == "call":
            callee = n.child_by_field_name("function")
            callee_name = ""
            if callee is not None:
                if callee.type == "identifier":
                    callee_name = src.text(callee)
                elif callee.type == "attribute":
                    callee_name = src.text(callee.child_by_field_name("attribute"))
                    target = _self_attr(callee.child_by_field_name("object"), src)
                    if target is not None and callee_name in COLLECTION_MUTATORS:
                        fn.self_mutator_calls.append((target, callee_name, _line(n)))
            if GUARD_CALL.match(callee_name or ""):
                fn.has_guard = True
        elif n.type in ("assignment", "augmented_assignment"):
            attr = _self_attr(n.child_by_field_name("left"), src)
            if attr is not None:
                fn.self_assignments.append((attr, _line(n)))
    stmts = [c for c in body.named_children if c.type != "comment"]
    if stmts and stmts[0].type == "expression_statement" and stmts[0].named_children and stmts[0].named_children[0].type == "string":
        stmts = stmts[1:]
    if len(stmts) == 1:
        s = stmts[0]
        if s.type == "expression_statement" and s.named_children and s.named_children[0].type == "assignment":
            attr = _self_attr(s.named_children[0].child_by_field_name("left"), src)
            if attr is not None:
                fn.single_assignment_to = attr
        elif s.type == "return_statement" and s.named_children:
            attr = _self_attr(s.named_children[0], src)
            if attr is not None:
                fn.returns_self_field = attr
    return fn
