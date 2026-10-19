"""collect の本体。設定・ファイル・構文解析・層マップ・適用判定・static チェックをまとめて facts を作る。"""

from __future__ import annotations

import datetime as dt
import pathlib

from . import VERSION, adr, catalog, coverage, files
from .checks import Ctx, run_checks
from .checks.common import classify_domain_types
from .config import Config, load_config
from .frameworks import Ledger
from .graph import Graph
from .layers import LAYERS, build_layer_map
from .model import Module
from .parse_py import parse_python
from .parse_ts import parse_typescript
from .resolve import Resolver

MAX_FILE_BYTES = 2_000_000
CRUD_DOMAIN_RATIO = 0.10
APPLY_MODES = {
    "clean-architecture": ("full", "dep-only", "off"),
    "ddd-tactical": ("full", "ent-vo-only", "off"),
}
_MODE_PREFIXES = {"dep-only": ("CA-DEP-",), "ent-vo-only": ("DDD-ENT-", "DDD-VO-")}
_REQUIRES_FILES = {"adr", "glossary", "business_rules", "ticket"}


def parse_file(root: pathlib.Path, path: str) -> Module | None:
    full = root / path
    try:
        if full.stat().st_size > MAX_FILE_BYTES:
            return None
        data = full.read_bytes()
    except OSError:
        return None
    lang = files.language_of(path)
    if lang == "typescript":
        return parse_typescript(path, data)
    if lang == "python":
        return parse_python(path, data)
    return None


# ------------------------------------------------------------------ 適用判定
def decide_applicability(
    cfg: Config, layer_map, scale: dict, domain, overrides: dict[str, str], eval_mode: bool, index: dict
) -> dict:
    out: dict[str, dict] = {}
    for pid in index["philosophies"]:
        entry = {"mode": "full", "reasons": [], "severity_shift": 0, "source": "auto"}
        if eval_mode:
            entry.update(source="eval", reasons=["評価では適用判定を on に固定する"])
            out[pid] = entry
            continue
        if pid in overrides:
            entry.update(mode=overrides[pid], source="override", reasons=["呼び出し側の指定（--apply）"])
            out[pid] = entry
            continue
        conf = cfg.philosophies.get(pid, "auto")
        if conf in ("on", "off"):
            entry.update(mode="full" if conf == "on" else "off", source="config",
                         reasons=[f"設定の philosophies.{pid} が {conf}"])
            out[pid] = entry
            continue
        crud = scale["domain_ratio"] < CRUD_DOMAIN_RATIO
        if pid == "clean-architecture":
            if not layer_map.estimable:
                entry.update(mode="dep-only", severity_shift=-1,
                             reasons=["層マップが推定できない（domain がないか、主要な層が2つ未満）ため CA-DEP 系だけを重大度を1段下げて適用"])
            elif crud:
                entry.update(mode="dep-only",
                             reasons=[f"ドメイン層の行数が全体の {scale['domain_ratio']:.0%} で、CRUD 中心とみなし CA-DEP 系だけを適用"])
            else:
                entry["reasons"] = ["層マップが推定でき、ドメイン層に十分なコードがある"]
        elif pid == "ddd-tactical":
            if not layer_map.estimable:
                entry.update(mode="off", reasons=["層マップが推定できないため適用しない"])
            elif crud:
                entry.update(mode="off",
                             reasons=[f"ドメイン層の行数が全体の {scale['domain_ratio']:.0%} で、CRUD 中心とみなし適用しない"])
            elif not domain.aggregates:
                entry.update(mode="ent-vo-only",
                             reasons=["集約らしき型（子のエンティティを持つエンティティ）が見つからないため ENT・VO 系だけを適用"])
            else:
                entry["reasons"] = [f"集約らしき型が {len(domain.aggregates)} 個ある"]
        else:
            entry["reasons"] = ["既定で適用（設定の philosophies で切り替えられる）"]
        out[pid] = entry
    return out


# ------------------------------------------------------------------ チェックの有効・無効
def select_checks(
    cfg: Config, index: dict, results: dict, applicability: dict, *, eval_mode: bool, root: pathlib.Path,
    only_philosophy: str | None, only_checks: set[str] | None, today: dt.date, available: dict[str, bool],
    ignore_gate: bool = False,
) -> tuple[list[dict], list[dict]]:
    active, skipped = [], []
    onboarding = cfg.onboarding(today) and not eval_mode
    for cid, c in sorted(index["checks"].items()):
        pid = c["_philosophy"]
        det = c["detection"]["type"]

        def skip(reason: str) -> None:
            skipped.append({"id": cid, "philosophy": pid, "detection": det, "reason": reason})

        if only_philosophy and pid != only_philosophy:
            continue
        if only_checks is not None and cid not in only_checks:
            continue
        app = applicability.get(pid, {"mode": "full"})
        if app["mode"] == "off":
            skip(f"思想 {pid} を適用しない")
            continue
        prefixes = _MODE_PREFIXES.get(app["mode"])
        if prefixes and not cid.startswith(prefixes):
            skip(f"思想 {pid} は {app['mode']} で適用")
            continue
        if cid in cfg.disabled_checks and not eval_mode:
            skip("設定の disabled_checks")
            continue
        missing = [r for r in c["applies_when"].get("requires", []) if r in _REQUIRES_FILES and not available.get(r)]
        if missing and not eval_mode:
            skip(f"必要な入力がない: {', '.join(missing)}")
            continue
        g = catalog.gate(results, cid)
        enabled_by = None
        if eval_mode:
            enabled_by = "eval" if c["status"] == "ready" or cfg.experimental else None
            if enabled_by is None:
                skip("draft（評価では experimental: true のケースだけで走る）")
                continue
        elif c["status"] == "draft":
            if not cfg.experimental:
                skip("draft のチェック（設定の experimental: true で有効）")
                continue
            enabled_by = "experimental"
        elif cid in cfg.enabled_checks:
            enabled_by = "enabled_checks"
        elif g and g.get("passed"):
            enabled_by = "gate"
        elif ignore_gate:
            enabled_by = "ignore_gate"
        else:
            skip("出荷ゲート未通過（evals/results/latest.json）")
            continue
        if onboarding and not ignore_gate and not (g and (g.get("precision") or 0) >= 0.9):
            skip("onboarding 期間中は適合率 0.9 以上のチェックだけを走らせる")
            continue
        impl = c["detection"].get("implementation")
        active.append({
            "id": cid,
            "philosophy": pid,
            "name": c.get("name"),
            "detection": det,
            "status": c["status"],
            "severity": c["severity"]["default"],
            "implementation": impl,
            "enabled_by": enabled_by,
        })
    return active, skipped


# ------------------------------------------------------------------ 対象の絞り込み
def _under(path: str, prefixes: list[str]) -> bool:
    return any(p in (".", "") or path == p or path.startswith(p.rstrip("/") + "/") for p in prefixes)


def _in_target(f: dict, target: dict, diff: files.DiffInfo | None) -> tuple[bool, bool | None]:
    """(残すか, 差分の変更行に掛かるか)"""
    locs = [f["location"]] + f.get("touches", [])
    if target["mode"] == "diff" and diff is not None:
        hit = any(diff.touches(loc["file"], loc["start_line"], loc["end_line"]) for loc in locs)
        return hit, hit
    if target["mode"] == "paths":
        return any(_under(loc["file"], target["paths"]) for loc in locs), None
    return True, None


def collect(
    root: pathlib.Path,
    *,
    paths: list[str] | None = None,
    base: str | None = None,
    all_files: bool = False,
    philosophy: str | None = None,
    checks: list[str] | None = None,
    overrides: dict[str, str] | None = None,
    eval_mode: bool = False,
    ignore_gate: bool = False,
    today: dt.date | None = None,
) -> dict:
    today = today or dt.date.today()
    root = root.resolve()
    cfg = load_config(root)
    notes: list[str] = list(cfg.warnings)
    listed = files.list_source_files(root, cfg.exclude)
    analyzed = [p for p in listed if not files.is_test_path(p)]
    layer_map = build_layer_map(analyzed, cfg.layers)
    ignored = set(layer_map.ignored)

    modules: dict[str, Module] = {}
    parse_errors = []
    for path in analyzed:
        if path in ignored:
            continue
        mod = parse_file(root, path)
        if mod is None:
            notes.append(f"{path} は読めないか大きすぎるため解析しなかった")
            continue
        if mod.parse_errors:
            parse_errors.append(path)
        modules[path] = mod
    resolver = Resolver(root, set(listed), cfg.source_roots)
    for mod in modules.values():
        resolver.resolve(mod)
    graph = Graph(modules)
    domain = classify_domain_types([m for p, m in modules.items() if layer_map.layer_of(p) == "domain"])

    loc_by_layer = {layer: 0 for layer in LAYERS}
    loc_by_layer["unmapped"] = 0
    for p, m in modules.items():
        loc_by_layer[layer_map.layer_of(p) or "unmapped"] += m.loc
    total = sum(loc_by_layer.values())
    scale = {
        "files": len(modules),
        "loc": total,
        "loc_by_layer": loc_by_layer,
        "domain_ratio": round(loc_by_layer["domain"] / total, 4) if total else 0.0,
        **domain.as_dict(),
    }

    index = catalog.load_index()
    results = catalog.load_results()
    overrides = overrides or {}
    for pid, mode in overrides.items():
        if pid not in index["philosophies"]:
            notes.append(f"--apply の思想 {pid} は存在しないため無視した")
    applicability = decide_applicability(cfg, layer_map, scale, domain, overrides, eval_mode, index)

    adr_dir, adrs = adr.load_adrs(root, cfg.adr_path)
    available = {
        "adr": bool(adrs),
        "glossary": (root / cfg.glossary_path).is_file(),
        "business_rules": (root / cfg.business_rules_path).is_file(),
        "ticket": False,
    }
    active, skipped = select_checks(
        cfg, index, results, applicability, eval_mode=eval_mode, root=root, only_philosophy=philosophy,
        only_checks=set(checks) if checks else None, today=today, available=available, ignore_gate=ignore_gate,
    )

    ctx = Ctx(root=root, modules=modules, layer_map=layer_map,
              ledger=Ledger(cfg.frameworks_add, cfg.frameworks_allow), graph=graph, domain=domain,
              checks=index["checks"])
    impls = [a["implementation"] for a in active if a["detection"] == "static" and a["implementation"]]
    raw, missing = run_checks(ctx, impls)
    for a in active:
        if a["detection"] == "static" and (not a["implementation"] or a["implementation"] in missing):
            notes.append(f"{a['id']} は static だが解析器に実装がないため走らせなかった")

    # 対象の決め方: PATH → そのパス配下、--all → 全体、どちらもなければ差分
    diff = None
    if paths:
        target = {"mode": "paths", "paths": [p.rstrip("/") or "." for p in paths]}
        target_files = [p for p in modules if _under(p, target["paths"])]
    elif all_files:
        target = {"mode": "all"}
        target_files = sorted(modules)
    else:
        diff = files.git_diff(root, base)
        if diff is None and base:
            raise files.BaseNotFound(
                f"比較先 {base} とのマージベースが見つからない。浅い clone なら履歴を取得する（actions/checkout は"
                " fetch-depth: 0）か、--all で全体を対象にする"
            )
        if diff is None:
            target = {"mode": "all"}
            target_files = sorted(modules)
            notes.append("比較先のブランチ（main・master）か git が見つからないため、全体を対象にした")
        else:
            target = {"mode": "diff", "base": diff.base, "merge_base": diff.merge_base}
            target_files = sorted(p for p in diff.changed if p in modules)
    target["files"] = target_files
    target["changed_lines"] = (
        {p: [list(r) for r in diff.changed[p]] for p in target_files} if diff is not None else None
    )

    findings = []
    for f in raw:
        keep, in_diff = _in_target(f, target, diff)
        if not keep:
            continue
        if in_diff is not None:
            f["in_diff"] = in_diff
        findings.append(f)
    findings.sort(key=lambda f: (f["location"]["file"], f["location"]["start_line"], f["id"]))

    cov_path, _cov = coverage.load_coverage(root, cfg.coverage_path)
    candidates = {a["id"]: [] for a in active if a["detection"] == "hybrid"}
    if candidates:
        notes.append("hybrid のチェックの候補抽出は v0.1 では未実装のため、候補は空")

    return {
        "schema_version": 1,
        "tool": {"name": "sumidashi", "version": VERSION},
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "root": str(root),
        "eval_mode": eval_mode,
        "target": target,
        "config": cfg.as_dict(),
        "layer_map": layer_map.as_dict(),
        "scale": scale,
        "applicability": applicability,
        "active_checks": active,
        "skipped_checks": skipped,
        "findings": findings,
        "candidates": candidates,
        "adr_dir": adr_dir,
        "adrs": adrs,
        "coverage_path": cov_path,
        "parse_errors": parse_errors,
        "notes": notes,
    }
