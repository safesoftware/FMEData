"""Findings, configuration, and how a finding's severity is decided."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning", "notice"]

ALWAYS_ENFORCED = "FD006"
# Removing a file a lesson links breaks the lesson wherever the file lives.
WARN_EVEN_WHEN_EXEMPT = "FD010"


@dataclass(frozen=True)
class Finding:
    check_id: str
    path: str
    line: int | None
    message: str
    severity: Severity


@dataclass
class Config:
    enforce: set[str] = field(default_factory=lambda: {ALWAYS_ENFORCED})
    allow_paths: dict[str, str] = field(default_factory=dict)
    allow_urls: dict[str, str] = field(default_factory=dict)
    bot_refusers: list[str] = field(default_factory=list)
    complete_suffixes: list[str] = field(default_factory=lambda: ["-complete"])
    exempt: dict[str, str] = field(default_factory=dict)


def annotation(f: Finding) -> str:
    """Render a finding as a GitHub Actions annotation line."""
    loc = f"file={f.path}" + (f",line={f.line}" if f.line is not None else "")
    return f"::{f.severity} {loc}::{f.check_id} {f.message} (see CHECKS.md#{f.check_id.lower()})"


def _reasoned(table: dict, name: str) -> dict[str, str]:
    for key, reason in table.items():
        if not str(reason).strip():
            raise ValueError(f"{name} entry {key!r} needs a reason")
    return {str(k): str(v) for k, v in table.items()}


def load_config(path: Path) -> Config:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    allow = data.get("allow", {})
    return Config(
        enforce=set(data.get("enforce", [])) | {ALWAYS_ENFORCED},
        allow_paths=_reasoned(allow.get("paths", {}), "allow.paths"),
        allow_urls=_reasoned(allow.get("urls", {}), "allow.urls"),
        bot_refusers=list(data.get("bot_refusers", [])),
        complete_suffixes=list(data.get("complete_suffixes", ["-complete"])),
        exempt=_reasoned(data.get("exempt", {}), "exempt"),
    )


def is_exempt(path: str, cfg: Config) -> bool:
    return any(path.startswith(prefix) for prefix in cfg.exempt)


def effective(f: Finding, cfg: Config) -> Finding:
    """Apply enforcement and exempt paths to a check's raw severity."""
    if f.check_id == ALWAYS_ENFORCED:
        return f
    if is_exempt(f.path, cfg):
        sev: Severity = "warning" if f.check_id == WARN_EVEN_WHEN_EXEMPT and f.severity != "notice" else "notice"
        return replace(f, severity=sev)
    if f.severity == "error" and f.check_id not in cfg.enforce:
        return replace(f, severity="warning")
    return f
