"""import をリポジトリ内のファイルか外部モジュールに解決する。"""

from __future__ import annotations

import json
import os
import pathlib
import posixpath
import re

from .model import Import, Module

TS_EXTS = (".ts", ".tsx", ".mts", ".cts", ".d.ts", ".js", ".jsx", ".mjs", ".cjs")
_JS_TO_TS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}


def _strip_jsonc(text: str) -> str:
    """tsconfig.json のコメントと末尾のカンマを取り除く。"""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def _load_tsconfig(path: pathlib.Path, depth: int = 0) -> dict:
    try:
        data = json.loads(_strip_jsonc(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    opts = dict(data.get("compilerOptions") or {})
    ext = data.get("extends")
    if isinstance(ext, str) and ext.startswith(".") and depth < 4:
        parent_path = (path.parent / ext).resolve()
        if parent_path.suffix != ".json":
            parent_path = parent_path.with_suffix(".json")
        parent = _load_tsconfig(parent_path, depth + 1)
        here = path.parent.resolve()
        # 親の baseUrl・paths は親の tsconfig の場所が基準なので、子の場所からの相対に直す
        if "baseUrl" in parent and "baseUrl" not in opts:
            opts["baseUrl"] = os.path.relpath(parent_path.parent / parent["baseUrl"], here)
        if "paths" in parent and "paths" not in opts:
            opts["paths"] = parent["paths"]
            opts.setdefault("_paths_base", parent.get("_paths_base") and os.path.relpath(
                parent_path.parent / parent["_paths_base"], here) or opts.get("baseUrl")
                or os.path.relpath(parent_path.parent, here))
    return opts


class Resolver:
    def __init__(self, root: pathlib.Path, files: set[str], source_roots: list[str]):
        self.root = root
        self.files = files
        self.source_roots = [r.strip("/") or "." for r in source_roots]
        self._py_index = self._build_py_index()
        opts = _load_tsconfig(root / "tsconfig.json") if (root / "tsconfig.json").is_file() else {}
        self.base_url = posixpath.normpath(opts["baseUrl"]) if opts.get("baseUrl") else None
        paths_base = opts.get("_paths_base") or self.base_url or "."
        self.ts_paths: list[tuple[str, str, list[str]]] = []
        for pattern, targets in (opts.get("paths") or {}).items():
            prefix, _, suffix = pattern.partition("*")
            self.ts_paths.append(
                (prefix, suffix, [posixpath.normpath(posixpath.join(paths_base, t)) for t in targets])
            )
        self.ts_paths.sort(key=lambda p: -len(p[0]))

    # ---------------------------------------------------------------- TypeScript
    def _ts_candidates(self, base: str) -> list[str]:
        base = posixpath.normpath(base)
        cands = [base]
        stem, ext = posixpath.splitext(base)
        if ext in _JS_TO_TS:
            cands += [stem + e for e in _JS_TO_TS[ext]]
        cands += [base + e for e in TS_EXTS]
        cands += [posixpath.join(base, "index" + e) for e in TS_EXTS]
        return cands

    def _ts_find(self, base: str) -> str | None:
        for c in self._ts_candidates(base):
            if c.startswith("./"):
                c = c[2:]
            if c in self.files:
                return c
        return None

    def resolve_ts(self, mod: Module, imp: Import) -> None:
        spec = imp.specifier
        if spec.startswith("."):
            hit = self._ts_find(posixpath.join(posixpath.dirname(mod.path), spec))
            if hit:
                imp.resolved = [hit]
            return  # 相対パスで見つからなければ、外部でもないので何もしない
        for prefix, suffix, targets in self.ts_paths:
            if spec.startswith(prefix) and spec.endswith(suffix) and len(spec) >= len(prefix) + len(suffix):
                star = spec[len(prefix) : len(spec) - len(suffix) if suffix else None]
                for t in targets:
                    hit = self._ts_find(t.replace("*", star, 1))
                    if hit:
                        imp.resolved = [hit]
                        return
        if self.base_url is not None:
            hit = self._ts_find(posixpath.join(self.base_url, spec))
            if hit:
                imp.resolved = [hit]
                return
        imp.external = spec

    # ---------------------------------------------------------------- Python
    def _build_py_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for f in self.files:
            if not f.endswith(".py"):
                continue
            for r in self.source_roots:
                if r != "." and not f.startswith(r + "/"):
                    continue
                rel = f if r == "." else f[len(r) + 1 :]
                parts = rel[:-3].split("/")
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                if not parts or not all(p.isidentifier() for p in parts):
                    continue
                index.setdefault(".".join(parts), f)
        return index

    def _py_module_file(self, dotted: str) -> str | None:
        return self._py_index.get(dotted)

    def _py_relative_base(self, mod: Module, level: int) -> str:
        """相対 import の基準になるパッケージのディレクトリ。"""
        d = posixpath.dirname(mod.path)
        for _ in range(level - 1):
            d = posixpath.dirname(d)
        return d

    def _py_path_file(self, directory: str, dotted: str) -> str | None:
        rel = dotted.replace(".", "/") if dotted else ""
        base = posixpath.normpath(posixpath.join(directory, rel)) if rel else directory
        for cand in (base + ".py", posixpath.join(base, "__init__.py")):
            cand = cand[2:] if cand.startswith("./") else cand
            if cand in self.files:
                return cand
        return None

    def resolve_py(self, mod: Module, imp: Import) -> None:
        spec = imp.specifier
        if spec.startswith("."):
            level = len(spec) - len(spec.lstrip("."))
            dotted = spec[level:]
            base_dir = self._py_relative_base(mod, level)
            targets: list[str] = []
            for name in imp.py_names:
                hit = self._py_path_file(base_dir, f"{dotted}.{name}" if dotted else name)
                if hit:
                    targets.append(hit)
            if not targets or len(targets) < len(imp.py_names):
                hit = self._py_path_file(base_dir, dotted)
                if hit:
                    targets.append(hit)
            imp.resolved = sorted(set(targets))
            return
        targets = []
        if imp.kind == "py_from":
            for name in imp.py_names:
                hit = self._py_module_file(f"{spec}.{name}")
                if hit:
                    targets.append(hit)
        parts = spec.split(".")
        for i in range(len(parts), 0, -1):
            hit = self._py_module_file(".".join(parts[:i]))
            if hit:
                if not targets or i == len(parts):
                    targets.append(hit)
                break
        if targets:
            imp.resolved = sorted(set(targets))
            return
        imp.external = spec

    def resolve(self, mod: Module) -> None:
        for imp in mod.imports:
            if mod.lang == "typescript":
                self.resolve_ts(mod, imp)
            else:
                self.resolve_py(mod, imp)
