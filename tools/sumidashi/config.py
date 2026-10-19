"""プロジェクト設定 .claude/sumidashi.yml の読み込み。"""

from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import dataclass, field

import yaml

CONFIG_PATH = ".claude/sumidashi.yml"
STRICTNESS = ("lenient", "standard", "strict")


@dataclass
class Config:
    path: str | None = None
    philosophies: dict[str, str] = field(default_factory=dict)
    strictness: str = "standard"
    disabled_checks: list[str] = field(default_factory=list)
    enabled_checks: list[str] = field(default_factory=list)
    experimental: bool = False
    layers: dict[str, str] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    source_roots: list[str] = field(default_factory=lambda: [".", "src"])
    adr_path: str = "docs/adr"
    glossary_path: str = "docs/glossary.yml"
    business_rules_path: str = "docs/business-rules.yml"
    coverage_path: str | None = None
    frameworks_add: list[str] = field(default_factory=list)
    frameworks_allow: list[str] = field(default_factory=list)
    onboarding_until: dt.date | None = None
    report_scores: bool = True
    report_language: str = "ja"
    pre_pr_check: bool = False
    warnings: list[str] = field(default_factory=list)

    def onboarding(self, today: dt.date | None = None) -> bool:
        today = today or dt.date.today()
        return self.onboarding_until is not None and today <= self.onboarding_until

    def effective_strictness(self, today: dt.date | None = None) -> str:
        if self.strictness == "strict" and self.onboarding(today):
            return "standard"
        return self.strictness

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "philosophies": self.philosophies,
            "strictness": self.strictness,
            "effective_strictness": self.effective_strictness(),
            "disabled_checks": self.disabled_checks,
            "enabled_checks": self.enabled_checks,
            "experimental": self.experimental,
            "layers": self.layers,
            "exclude": self.exclude,
            "source_roots": self.source_roots,
            "adr_path": self.adr_path,
            "coverage_path": self.coverage_path,
            "onboarding_until": self.onboarding_until.isoformat() if self.onboarding_until else None,
            "onboarding": self.onboarding(),
            "report_scores": self.report_scores,
            "pre_pr_check": self.pre_pr_check,
            "warnings": self.warnings,
        }


def load_config(root: pathlib.Path) -> Config:
    path = root / CONFIG_PATH
    cfg = Config()
    if not path.is_file():
        return cfg
    cfg.path = CONFIG_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        cfg.warnings.append(f"{CONFIG_PATH} を読めませんでした（既定値で続行）: {exc}")
        return cfg
    if not isinstance(raw, dict):
        cfg.warnings.append(f"{CONFIG_PATH} の最上位がマッピングではありません（既定値で続行）")
        return cfg

    def as_list(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(v) for v in value]

    for name, mode in (raw.get("philosophies") or {}).items():
        mode = {True: "on", False: "off"}.get(mode, str(mode))
        if mode not in ("auto", "on", "off"):
            cfg.warnings.append(f"philosophies.{name} の値 {mode!r} は auto・on・off のどれでもないため auto とみなします")
            mode = "auto"
        cfg.philosophies[str(name)] = mode
    strictness = str(raw.get("strictness", "standard"))
    if strictness not in STRICTNESS:
        cfg.warnings.append(f"strictness の値 {strictness!r} は不正なため standard とみなします")
        strictness = "standard"
    cfg.strictness = strictness
    cfg.disabled_checks = as_list(raw.get("disabled_checks"))
    cfg.enabled_checks = as_list(raw.get("enabled_checks"))
    cfg.experimental = bool(raw.get("experimental", False))
    cfg.layers = {str(k): str(v) for k, v in (raw.get("layers") or {}).items()}
    cfg.exclude = as_list(raw.get("exclude"))
    if raw.get("source_roots"):
        cfg.source_roots = as_list(raw.get("source_roots"))
    cfg.adr_path = str((raw.get("adr") or {}).get("path", cfg.adr_path))
    cfg.glossary_path = str((raw.get("glossary") or {}).get("path", cfg.glossary_path))
    cfg.business_rules_path = str((raw.get("business_rules") or {}).get("path", cfg.business_rules_path))
    cov = (raw.get("coverage") or {}).get("path")
    cfg.coverage_path = str(cov) if cov else None
    fw = raw.get("frameworks") or {}
    cfg.frameworks_add = as_list(fw.get("add"))
    cfg.frameworks_allow = as_list(fw.get("allow"))
    until = raw.get("onboarding_until")
    if until:
        try:
            cfg.onboarding_until = until if isinstance(until, dt.date) else dt.date.fromisoformat(str(until))
        except ValueError:
            cfg.warnings.append(f"onboarding_until の値 {until!r} を日付として読めません")
    report = raw.get("report") or {}
    cfg.report_scores = bool(report.get("scores", True))
    cfg.report_language = str(report.get("language", "ja"))
    cfg.pre_pr_check = bool((raw.get("hooks") or {}).get("pre_pr_check", False))
    known = {
        "version", "philosophies", "strictness", "disabled_checks", "enabled_checks", "experimental",
        "layers", "exclude", "source_roots", "adr", "glossary", "business_rules", "coverage",
        "frameworks", "onboarding_until", "report", "hooks",
    }
    for key in raw:
        if key not in known:
            cfg.warnings.append(f"{CONFIG_PATH} の未知の項目 {key!r} を無視しました")
    return cfg
