"""TypeScript を tree-sitter で読み、中間モデル（model.py）に落とす。"""

from __future__ import annotations

import re

import tree_sitter_typescript as tst
from tree_sitter import Language, Node, Parser

from .model import ClassDecl, Decorator, Field, Function, Import, Module, Param

_LANG_TS = Language(tst.language_typescript())
_LANG_TSX = Language(tst.language_tsx())

GUARD_CALL = re.compile(r"^(assert|validate|ensure|check|guard|invariant)", re.IGNORECASE)
ARRAY_MUTATORS = {"push", "pop", "shift", "unshift", "splice", "sort", "reverse", "fill", "copyWithin"}


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


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _has_token(node: Node, token: str) -> bool:
    return any(c.type == token for c in node.children)


def _string_value(src: _Src, node: Node | None) -> str | None:
    if node is None or node.type not in ("string", "template_string"):
        return None
    frag = [c for c in node.children if c.type == "string_fragment"]
    if frag:
        return src.text(frag[0])
    raw = src.text(node)
    return raw[1:-1] if len(raw) >= 2 else None


def _type_text(src: _Src, node: Node | None) -> str | None:
    if node is None:
        return None
    t = src.text(node).strip()
    return t[1:].strip() if t.startswith(":") else t


def parse_typescript(path: str, data: bytes) -> Module:
    lang = _LANG_TSX if path.endswith((".tsx", ".jsx")) else _LANG_TS
    tree = Parser(lang).parse(data)
    src = _Src(data)
    mod = Module(path=path, lang="typescript", lines=data.decode("utf-8", "replace").splitlines())
    root = tree.root_node
    mod.parse_errors = sum(1 for n in _walk(root) if n.type == "ERROR")

    for node in root.children:
        _top_level(src, mod, node, exported=False)

    seen = {(i.line, i.specifier) for i in mod.imports}
    for node in _walk(root):
        if node.type != "call_expression":
            continue
        fn = node.child_by_field_name("function")
        args = node.child_by_field_name("arguments")
        if fn is None or args is None:
            continue
        kind = None
        if fn.type == "identifier" and src.text(fn) == "require":
            kind = "require"
        elif fn.type == "import":
            kind = "dynamic"
        if kind is None:
            continue
        first = next((c for c in args.named_children), None)
        spec = _string_value(src, first)
        if spec is None or (_line(node), spec) in seen:
            continue
        mod.imports.append(Import(line=_line(node), end_line=_end_line(node), specifier=spec, kind=kind))
    mod.imports.sort(key=lambda i: (i.line, i.specifier))
    return mod


def _top_level(src: _Src, mod: Module, node: Node, exported: bool) -> None:
    t = node.type
    if t == "import_statement":
        _import(src, mod, node)
    elif t == "export_statement":
        source = node.child_by_field_name("source")
        if source is not None:
            spec = _string_value(src, source)
            if spec is not None:
                names = {}
                clause = next((c for c in node.children if c.type == "export_clause"), None)
                if clause is not None:
                    for spec_node in clause.named_children:
                        if spec_node.type == "export_specifier":
                            n = spec_node.child_by_field_name("name")
                            names[src.text(n)] = src.text(n)
                mod.imports.append(
                    Import(
                        line=_line(node),
                        end_line=_end_line(node),
                        specifier=spec,
                        kind="reexport",
                        type_only=_has_token(node, "type"),
                        bindings=names,
                    )
                )
            return
        decl = node.child_by_field_name("declaration")
        decorators = [c for c in node.children if c.type == "decorator"]
        if decl is not None:
            _top_level(src, mod, decl, exported=True)
            if decorators and mod.classes and mod.classes[-1].start_line >= _line(decl):
                mod.classes[-1].decorators[:0] = [_decorator(src, d) for d in decorators]
    elif t in ("class_declaration", "abstract_class_declaration"):
        mod.classes.append(_class(src, node, exported))
    elif t == "interface_declaration":
        mod.classes.append(_interface(src, node, exported))
    elif t == "type_alias_declaration":
        name = node.child_by_field_name("name")
        mod.classes.append(
            ClassDecl(
                name=src.text(name),
                line=_line(name),
                start_line=_line(node),
                end_line=_end_line(node),
                kind="type_alias",
                exported=exported,
            )
        )
    elif t == "function_declaration":
        mod.functions.append(_function(src, node, kind="function", exported=exported))
    elif t == "lexical_declaration":
        for decl in node.named_children:
            if decl.type != "variable_declarator":
                continue
            value = decl.child_by_field_name("value")
            if value is not None and value.type in ("arrow_function", "function_expression", "function"):
                fn = _function(src, value, kind="function", exported=exported)
                name = decl.child_by_field_name("name")
                fn.name = src.text(name)
                fn.line = _line(name)
                fn.start_line = _line(node)
                mod.functions.append(fn)


def _import(src: _Src, mod: Module, node: Node) -> None:
    source = node.child_by_field_name("source")
    spec = _string_value(src, source)
    bindings: dict[str, str] = {}
    type_only = _has_token(node, "type")
    clause = next((c for c in node.children if c.type == "import_clause"), None)
    require_clause = next((c for c in node.children if c.type == "import_require_clause"), None)
    if require_clause is not None:
        ident = next((c for c in require_clause.named_children if c.type == "identifier"), None)
        spec = _string_value(src, next((c for c in require_clause.named_children if c.type == "string"), None))
        if ident is not None:
            bindings[src.text(ident)] = "default"
    if spec is None:
        return
    specifiers_all_type = None
    if clause is not None:
        for c in clause.named_children:
            if c.type == "identifier":
                bindings[src.text(c)] = "default"
                specifiers_all_type = False
            elif c.type == "namespace_import":
                ident = next((x for x in c.named_children if x.type == "identifier"), None)
                if ident is not None:
                    bindings[src.text(ident)] = "*"
                specifiers_all_type = False
            elif c.type == "named_imports":
                for s in c.named_children:
                    if s.type != "import_specifier":
                        continue
                    name = s.child_by_field_name("name")
                    alias = s.child_by_field_name("alias")
                    bindings[src.text(alias or name)] = src.text(name)
                    is_type = _has_token(s, "type")
                    if specifiers_all_type is None:
                        specifiers_all_type = is_type
                    else:
                        specifiers_all_type = specifiers_all_type and is_type
    if specifiers_all_type:
        type_only = True
    mod.imports.append(
        Import(
            line=_line(node),
            end_line=_end_line(node),
            specifier=spec,
            kind="import",
            type_only=type_only,
            bindings=bindings,
        )
    )


def _decorator(src: _Src, node: Node) -> Decorator:
    raw = src.text(node).lstrip("@").strip()
    name = raw.split("(", 1)[0].strip()
    args = raw[len(name) :].strip()
    return Decorator(name=name, args=args, line=_line(node))


def _heritage(src: _Src, node: Node) -> tuple[list[str], list[str]]:
    names: list[str] = []
    texts: list[str] = []
    for h in _walk(node):
        if h.type == "extends_clause":
            value = h.child_by_field_name("value")
            if value is not None:
                names.append(src.text(value))
                targs = h.child_by_field_name("type_arguments")
                texts.append(src.text(value) + (src.text(targs) if targs is not None else ""))
        elif h.type in ("implements_clause", "extends_type_clause"):
            for t in h.named_children:
                text = src.text(t)
                texts.append(text)
                if t.type == "generic_type":
                    names.append(src.text(t.child_by_field_name("name")))
                else:
                    names.append(text)
    return names, texts


def _modifiers(src: _Src, node: Node) -> dict:
    mods = {"access": "public", "static": False, "readonly": False, "abstract": False, "accessor": None}
    for c in node.children:
        if c.type == "accessibility_modifier":
            mods["access"] = src.text(c).strip()
        elif c.type == "static":
            mods["static"] = True
        elif c.type == "readonly":
            mods["readonly"] = True
        elif c.type == "abstract":
            mods["abstract"] = True
        elif c.type in ("get", "set"):
            mods["accessor"] = c.type
    return mods


def _class(src: _Src, node: Node, exported: bool) -> ClassDecl:
    name = node.child_by_field_name("name")
    bases, bases_text = [], []
    heritage = next((c for c in node.children if c.type == "class_heritage"), None)
    if heritage is not None:
        bases, bases_text = _heritage(src, heritage)
    cls = ClassDecl(
        name=src.text(name),
        line=_line(name) if name is not None else _line(node),
        start_line=_line(node),
        end_line=_end_line(node),
        kind="abstract_class" if node.type == "abstract_class_declaration" else "class",
        exported=exported,
        bases=bases,
        bases_text=bases_text,
        decorators=[_decorator(src, c) for c in node.children if c.type == "decorator"],
    )
    body = node.child_by_field_name("body")
    if body is None:
        return cls
    for member in body.named_children:
        if member.type == "public_field_definition":
            mods = _modifiers(src, member)
            mname = member.child_by_field_name("name")
            access = "private" if mname is not None and mname.type == "private_property_identifier" else mods["access"]
            cls.fields.append(
                Field(
                    name=src.text(mname),
                    line=_line(mname) if mname is not None else _line(member),
                    type=_type_text(src, member.child_by_field_name("type")),
                    access=access,
                    readonly=mods["readonly"],
                    static=mods["static"],
                )
            )
        elif member.type in ("method_definition", "abstract_method_signature", "method_signature"):
            fn = _method(src, member)
            cls.methods.append(fn)
            if fn.kind == "constructor":
                cls.fields.extend(_parameter_properties(src, member))
    return cls


def _parameter_properties(src: _Src, method: Node) -> list[Field]:
    params = method.child_by_field_name("parameters")
    out: list[Field] = []
    if params is None:
        return out
    for p in params.named_children:
        if p.type not in ("required_parameter", "optional_parameter"):
            continue
        mods = _modifiers(src, p)
        explicit = any(c.type in ("accessibility_modifier", "readonly") for c in p.children)
        if not explicit:
            continue
        pattern = p.child_by_field_name("pattern")
        out.append(
            Field(
                name=src.text(pattern),
                line=_line(p),
                type=_type_text(src, p.child_by_field_name("type")),
                access=mods["access"],
                readonly=mods["readonly"],
                origin="ctor_param",
            )
        )
    return out


def _interface(src: _Src, node: Node, exported: bool) -> ClassDecl:
    name = node.child_by_field_name("name")
    bases, bases_text = _heritage(src, node) if any(c.type == "extends_type_clause" for c in node.children) else ([], [])
    cls = ClassDecl(
        name=src.text(name),
        line=_line(name),
        start_line=_line(node),
        end_line=_end_line(node),
        kind="interface",
        exported=exported,
        bases=bases,
        bases_text=bases_text,
    )
    body = node.child_by_field_name("body")
    if body is None:
        return cls
    for member in body.named_children:
        if member.type == "method_signature":
            fn = _method(src, member)
            fn.abstract = True
            cls.methods.append(fn)
        elif member.type == "property_signature":
            mname = member.child_by_field_name("name")
            cls.fields.append(
                Field(
                    name=src.text(mname),
                    line=_line(mname) if mname is not None else _line(member),
                    type=_type_text(src, member.child_by_field_name("type")),
                    readonly=_has_token(member, "readonly"),
                )
            )
    return cls


def _params(src: _Src, node: Node | None) -> list[Param]:
    out: list[Param] = []
    if node is None:
        return out
    if node.type == "identifier":  # x => ... の1引数アロー関数
        return [Param(name=src.text(node), type=None, line=_line(node))]
    for p in node.named_children:
        if p.type in ("required_parameter", "optional_parameter"):
            pattern = p.child_by_field_name("pattern")
            out.append(Param(name=src.text(pattern), type=_type_text(src, p.child_by_field_name("type")), line=_line(p)))
    return out


def _method(src: _Src, node: Node) -> Function:
    mods = _modifiers(src, node)
    name = node.child_by_field_name("name")
    name_text = src.text(name)
    access = "private" if name is not None and name.type == "private_property_identifier" else mods["access"]
    kind = "constructor" if name_text == "constructor" else (mods["accessor"] or "method")
    fn = _function(src, node, kind=kind, exported=True)
    fn.name = name_text
    fn.line = _line(name) if name is not None else _line(node)
    fn.access = access
    fn.static = mods["static"]
    fn.abstract = mods["abstract"] or node.type in ("abstract_method_signature", "method_signature")
    fn.decorators = [_decorator(src, c).name for c in node.children if c.type == "decorator"]
    return fn


def _is_this_member(node: Node | None) -> Node | None:
    """this.x なら x のノードを返す。"""
    if node is None or node.type != "member_expression":
        return None
    obj = node.child_by_field_name("object")
    if obj is not None and obj.type == "this":
        return node.child_by_field_name("property")
    return None


def _function(src: _Src, node: Node, kind: str, exported: bool) -> Function:
    name = node.child_by_field_name("name")
    params = node.child_by_field_name("parameters") or node.child_by_field_name("parameter")
    body = node.child_by_field_name("body")
    fn = Function(
        name=src.text(name) if name is not None else "",
        line=_line(name) if name is not None else _line(node),
        start_line=_line(node),
        end_line=_end_line(node),
        params=_params(src, params),
        returns=_type_text(src, node.child_by_field_name("return_type")),
        kind=kind,
        exported=exported,
    )
    if body is None:
        return fn
    fn.body_text = src.text(body)
    for n in _walk(body):
        if n.type in ("if_statement", "throw_statement"):
            fn.has_guard = True
        elif n.type == "call_expression":
            callee = n.child_by_field_name("function")
            callee_name = ""
            if callee is not None:
                if callee.type == "identifier":
                    callee_name = src.text(callee)
                elif callee.type == "member_expression":
                    prop = callee.child_by_field_name("property")
                    callee_name = src.text(prop)
                    field_node = _is_this_member(callee.child_by_field_name("object"))
                    if field_node is not None and callee_name in ARRAY_MUTATORS:
                        fn.self_mutator_calls.append((src.text(field_node), callee_name, _line(n)))
            if GUARD_CALL.match(callee_name or ""):
                fn.has_guard = True
        elif n.type in ("assignment_expression", "augmented_assignment_expression"):
            field_node = _is_this_member(n.child_by_field_name("left"))
            if field_node is not None:
                fn.self_assignments.append((src.text(field_node), _line(n)))
        elif n.type == "update_expression":
            field_node = _is_this_member(n.child_by_field_name("argument"))
            if field_node is not None:
                fn.self_assignments.append((src.text(field_node), _line(n)))
    if body.type == "statement_block":
        stmts = [c for c in body.named_children if c.type != "comment"]
        if len(stmts) == 1:
            stmt = stmts[0]
            if stmt.type == "expression_statement":
                expr = stmt.named_children[0] if stmt.named_children else None
                if expr is not None and expr.type == "assignment_expression":
                    field_node = _is_this_member(expr.child_by_field_name("left"))
                    if field_node is not None:
                        fn.single_assignment_to = src.text(field_node)
            elif stmt.type == "return_statement" and stmt.named_children:
                field_node = _is_this_member(stmt.named_children[0])
                if field_node is not None:
                    fn.returns_self_field = src.text(field_node)
    else:  # 式本体のアロー関数
        field_node = _is_this_member(body)
        if field_node is not None:
            fn.returns_self_field = src.text(field_node)
    return fn
