"""ファイル間の依存グラフと強連結成分。"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Import, Module


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    line: int
    end_line: int
    type_only: bool


class Graph:
    def __init__(self, modules: dict[str, Module]):
        self.edges: list[Edge] = []
        self.out: dict[str, list[Edge]] = {p: [] for p in modules}
        for path, mod in modules.items():
            for imp in mod.imports:
                for dst in imp.resolved:
                    if dst == path or dst not in modules:
                        continue
                    e = Edge(path, dst, imp.line, imp.end_line, imp.type_only)
                    self.edges.append(e)
                    self.out[path].append(e)

    def sccs(self, include_type_only: bool = True) -> list[list[str]]:
        """2ファイル以上の強連結成分。反復版の Tarjan 法。"""
        succ = {
            p: sorted({e.dst for e in es if include_type_only or not e.type_only})
            for p, es in self.out.items()
        }
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        result: list[list[str]] = []
        counter = 0
        for start in sorted(succ):
            if start in index:
                continue
            work = [(start, 0)]
            index[start] = low[start] = counter
            counter += 1
            stack.append(start)
            on_stack.add(start)
            while work:
                node, i = work[-1]
                children = succ[node]
                if i < len(children):
                    work[-1] = (node, i + 1)
                    child = children[i]
                    if child not in index:
                        index[child] = low[child] = counter
                        counter += 1
                        stack.append(child)
                        on_stack.add(child)
                        work.append((child, 0))
                    elif child in on_stack:
                        low[node] = min(low[node], index[child])
                    continue
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1:
                        result.append(sorted(comp))
        return sorted(result)

    def imported_by(self, path: str) -> list[Edge]:
        return [e for e in self.edges if e.dst == path]


def import_for_edge(mod: Module, edge: Edge) -> Import | None:
    for imp in mod.imports:
        if imp.line == edge.line and edge.dst in imp.resolved:
            return imp
    return None
