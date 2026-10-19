"""ファイルを層に振り分ける。設定の layers が最優先で、残りはディレクトリ名から推定する。"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import globs

LAYERS = ("domain", "application", "adapter", "infrastructure", "main", "shared")
DEPTH = {"domain": 0, "shared": 0, "application": 1, "adapter": 2, "infrastructure": 2, "main": 3}

# 依存元の層 → 依存してよい層（docs/architecture.md の表）
ALLOWED = {
    "domain": {"domain", "shared"},
    "application": {"domain", "application", "shared"},
    "adapter": {"domain", "application", "adapter", "infrastructure", "shared"},
    "infrastructure": {"domain", "application", "adapter", "infrastructure", "shared"},
    "main": set(LAYERS),
    "shared": {"shared"},
}

STRONG = {
    "domain": {"domain", "domains", "domain-model", "domain_model"},
    "application": {
        "application", "usecase", "usecases", "use-case", "use-cases", "use_case", "use_cases",
        "interactor", "interactors",
    },
    "adapter": {"adapters", "adapter", "presentation"},
    "infrastructure": {"infrastructure", "infra", "persistence"},
    "main": {"composition-root", "composition_root", "bootstrap", "di", "container"},
    "shared": {"shared", "shared-kernel", "shared_kernel", "sharedkernel"},
}
WEAK = {
    "adapter": {
        "controllers", "controller", "handlers", "handler", "routes", "routers", "api", "web", "http",
        "rest", "graphql", "resolvers", "views", "cli", "presenters", "interfaces", "ui",
    },
    "infrastructure": {"db", "database", "gateways", "external", "clients", "orm", "storage"},
    "shared": {"common"},
}
MAIN_FILES = {"main.ts", "main.py"}

_STRONG_INDEX = {kw: layer for layer, kws in STRONG.items() for kw in kws}
_WEAK_INDEX = {kw: layer for layer, kws in WEAK.items() for kw in kws}


def allowed(src: str, dst: str) -> bool:
    return dst in ALLOWED.get(src, set())


def _literal_prefix_len(pattern: str) -> int:
    for i, ch in enumerate(pattern):
        if ch in "*?{":
            return i
    return len(pattern)


def estimate_layer(path: str) -> tuple[str | None, str]:
    """(層, 根拠)。根拠は 'strong:<dir>'・'main-file'・'weak:<dir>'・'none'。"""
    parts = path.split("/")
    dirs = [p.lower() for p in parts[:-1]]
    for d in dirs:
        if d in _STRONG_INDEX:
            return _STRONG_INDEX[d], f"strong:{d}"
    if parts[-1].lower() in MAIN_FILES:
        return "main", "main-file"
    for d in dirs:
        if d in _WEAK_INDEX:
            return _WEAK_INDEX[d], f"weak:{d}"
    return None, "none"


@dataclass
class LayerMap:
    files: dict[str, str] = field(default_factory=dict)
    """ファイル → 層（ignore は含めない）"""
    reasons: dict[str, str] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    source: str = "estimated"
    """config / estimated / config+estimated"""

    def layer_of(self, path: str) -> str | None:
        return self.files.get(path)

    @property
    def present(self) -> set[str]:
        return set(self.files.values())

    @property
    def estimable(self) -> bool:
        core = self.present & {"domain", "application", "adapter", "infrastructure"}
        return "domain" in self.present and len(core) >= 2

    def counts(self) -> dict[str, int]:
        out = {layer: 0 for layer in LAYERS}
        for layer in self.files.values():
            out[layer] += 1
        return out

    def as_dict(self, include_files: bool = True) -> dict:
        data = {
            "source": self.source,
            "estimable": self.estimable,
            "counts": self.counts(),
            "unmapped_count": len(self.unmapped),
            "ignored_count": len(self.ignored),
        }
        if include_files:
            data["files"] = dict(sorted(self.files.items()))
            data["unmapped"] = self.unmapped
        return data


def build_layer_map(files: list[str], config_layers: dict[str, str]) -> LayerMap:
    lm = LayerMap()
    # 設定の glob は、ワイルドカードの前の固定部分が長いものほど具体的とみなして先に当てる
    patterns = sorted(config_layers.items(), key=lambda kv: -_literal_prefix_len(kv[0]))
    used_config = used_estimate = False
    for path in files:
        layer = None
        for pattern, value in patterns:
            if globs.match(path, pattern):
                layer, reason = value, f"config:{pattern}"
                break
        if layer is None:
            layer, reason = estimate_layer(path)
            if layer is not None:
                used_estimate = True
        else:
            used_config = True
        if layer == "ignore":
            lm.ignored.append(path)
            continue
        if layer is None or layer not in LAYERS:
            lm.unmapped.append(path)
            continue
        lm.files[path] = layer
        lm.reasons[path] = reason
    if used_config and used_estimate:
        lm.source = "config+estimated"
    elif used_config:
        lm.source = "config"
    return lm
