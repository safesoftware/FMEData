"""Findings, configuration, and how a finding's severity is decided."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning", "notice"]

# Every check: id -> (short name, one-line summary). The report prints these; CHECKS.md has the full detail.
CHECKS: dict[str, tuple[str, str]] = {
    "FD001": ("Workspace data paths", r"C:\FMEData paths in workspaces point to files in this repository"),
    "FD002": ("Workspace S3 links", "FMEData S3 URLs in workspaces resolve"),
    "FD003": ("Personal folders in workspaces", r"Workspaces don't read data from a personal C:\Users folder"),
    "FD005": ("Legacy exercise- names", "Workspaces don't use the legacy exercise- prefix, which is being phased out"),
    "FD006": ("Public safety", "Changes add no secrets, email addresses, or personal folders"),
    "FD010": ("Linked file removed", "A pull request doesn't remove or rename a file a current lesson links"),
    "FD011": ("Complete workspace names", 'Complete workspace names end in "-complete"'),
    "FD012": ("Folder dataset zips", "A folder dataset's zip is updated whenever its folder changes"),
    "FT001": ("Lesson data paths", r"C:\FMEData paths in lessons point to files in this repository"),
    "FT002": ("Lesson S3 links", "FMEData S3 links in lessons resolve"),
    "FT003": ("Exercise workspaces", "Exercises list a complete workspace, and it exists"),
    "FT005": ("Lesson web links", "Web links in lessons don't return an error"),
    "FT006": ("Workspace FME version", "Linked workspaces open in the FME version the course teaches"),
    "FT007": ("Lessons linking exercise- names", "Lessons don't link workspaces with the legacy exercise- prefix"),
    "FT008": ("Step 1 starting workspace", "Step 1 gives the starting workspace's path, and Resources lists it"),
    "FT009": ("Course copies in the archive", "No Skilljar course copies or test courses in the lesson archive"),
}

# Checks that look at what a pull request changes, so the nightly report never counts them.
PR_ONLY = {"FD006", "FD010"}

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
    ignore_courses: list[str] = field(default_factory=list)
    # Course name -> the version Skilljar publishes as current, where the archive's newest version isn't it,
    # or "annual" for an unversioned course that is always current.
    course_versions: dict[str, str] = field(default_factory=dict)
    # Courses (names or patterns) with no current version on Skilljar: every version is archived.
    archived_courses: list[str] = field(default_factory=list)


_VERSION = re.compile(r"^\d{4}\.\d+$")
# An unversioned course that is always current: its workspaces follow each year's FME release (FT006).
ANNUAL = "annual"


def _course_versions(table: dict) -> dict[str, str]:
    for name, version in table.items():
        if version != ANNUAL and not _VERSION.match(str(version)):
            raise ValueError(f"courses.current entry {name!r} needs a version like 2026.2 or \"{ANNUAL}\", "
                             f"not {version!r}")
    return {str(k): str(v) for k, v in table.items()}


def annotation(f: Finding) -> str:
    """Render a finding as a GitHub Actions annotation line."""
    loc = f"file={_escape(f.path, prop=True)}" + (f",line={f.line}" if f.line is not None else "")
    message = _escape(f"{f.check_id} {f.message} (see CHECKS.md#{f.check_id.lower()})")
    return f"::{f.severity} {loc}::{message}"


def _escape(value: str, prop: bool = False) -> str:
    """Escape a workflow-command value; properties also escape : and ,."""
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if prop else value


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
        ignore_courses=list(data.get("ignore_courses", [])),
        course_versions=_course_versions(data.get("courses", {}).get("current", {})),
        archived_courses=list(data.get("courses", {}).get("archived", [])),
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
