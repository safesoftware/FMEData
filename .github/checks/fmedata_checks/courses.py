"""Derive checks.toml's [courses] table from Skilljar's published catalog. Run locally; CI never calls Skilljar.

    SKILLJAR_API_KEY=... python -m fmedata_checks courses --fmetraining ../FMETraining
    python -m fmedata_checks courses --fmetraining ../FMETraining --catalog catalog.json

On the Academy, a course's unversioned slug ("compare-workspaces") is its current version; when a new version
ships, the outgoing one takes a versioned slug ("compare-workspaces-2024-1"). So for each course in the lesson
archive:

- its current version is the version in the title of the published course with an unversioned slug;
- if no published course has an unversioned slug, every version is archived;
- if that course's title carries no version ("MCP and FME"), the current copy is the course's newest archive
  folder, and the course is worth renaming in Skilljar to carry the version;
- unless checks.toml already marks it "annual": an unversioned course that stays current and follows each year's
  FME release (FT006). Skilljar can't tell the two apart, so "annual" is set by hand and kept on regeneration.

Only overrides are written: a course whose newest archive version is already its current one needs no entry.
"""

from __future__ import annotations

import base64
import fnmatch
import json
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .lessons import _COURSE_VERSION, _VERSION_DIR, _key

API = "https://api.skilljar.com/v1/domains/{domain}/published-courses?page_size=100"
_VERSIONED_SLUG = re.compile(r"-\d{4}-?\d+$")
# Characters the S3 export can't use in a folder name; it writes "_" instead ("What is FME Flow_ 2026.1").
_FOLDER_UNSAFE = re.compile(r'[?:/\\*"<>|]')


@dataclass
class CourseConfig:
    current: dict[str, str] = field(default_factory=dict)
    archived: list[str] = field(default_factory=list)
    renames: list[tuple[str, str]] = field(default_factory=list)
    # Courses with more than one live unversioned copy at different versions: (name, ["title (slug)", ...]).
    # Neither copy is taken as current; a person decides, and checks.toml's existing entry is kept until then.
    conflicts: list[tuple[str, list[str]]] = field(default_factory=list)


def archive_name(title: str) -> str:
    """A Skilljar course title as the lesson archive spells its folder."""
    return _FOLDER_UNSAFE.sub("_", title.replace("​", "")).strip()


def _split(name: str) -> tuple[str, str | None]:
    m = _COURSE_VERSION.match(name)
    return (m.group(1), m.group(2)) if m else (name, None)


def catalog_rows(rows: Iterable[dict]) -> list[dict]:
    """Normalize published-course rows (v1 API rows, or a saved list of {title, slug}) to {title, slug, hidden}."""
    out = []
    for r in rows:
        title = r.get("title") or (r.get("course") or {}).get("title")
        if title and r.get("slug"):
            out.append({"title": title, "slug": r["slug"], "hidden": bool(r.get("hidden"))})
    return out


def derive(archive: Iterable[tuple[str, str]], catalog: Iterable[dict],
           ignore_courses: list[str] | None = None, annual: Iterable[str] = (),
           keep_current: dict[str, str] | None = None, keep_archived: Iterable[str] = ()) -> CourseConfig:
    """archive: (archive version folder, course folder name) pairs. catalog: published courses on one domain.

    annual: courses checks.toml marks "annual"; while they're live and unversioned they stay annual.
    keep_current, keep_archived: checks.toml's existing entries, kept as they are for a course in conflict.
    """
    keep_current = keep_current or {}
    keep_archived = set(keep_archived)
    annual = set(annual)
    ignore = ignore_courses or []
    folders: dict[str, set[str]] = {}
    versions: dict[str, set[str]] = {}
    for folder, course in archive:
        if any(fnmatch.fnmatchcase(course, p) for p in ignore):
            continue
        base, version = _split(course)
        folders.setdefault(base, set()).add(folder)
        versions.setdefault(base, set())
        if version:
            versions[base].add(version)
    live: dict[str, str | None] = {}
    seen: dict[str, list[tuple[str | None, str]]] = {}
    for row in catalog_rows(catalog):
        # A hidden course isn't on the Academy catalog, so it says nothing about which copy is current.
        if row.get("hidden") or _VERSIONED_SLUG.search(row["slug"]):
            continue
        base, version = _split(archive_name(row["title"]))
        seen.setdefault(base, []).append((version, f"{row['title']} ({row['slug']})"))
        live[base] = version
    result = CourseConfig()
    conflicted = set()
    for base, copies in sorted(seen.items()):
        if len({v for v, _ in copies}) > 1:
            conflicted.add(base)
            if base in folders:
                result.conflicts.append((base, [label for _, label in copies]))
    for base in sorted(folders):
        if base in conflicted:
            if base in keep_current:
                result.current[base] = keep_current[base]
            elif base in keep_archived:
                result.archived.append(base)
            continue
        newest = max(versions[base], key=_key) if versions[base] else None
        if base not in live:
            if newest:
                result.archived.append(base)
            continue
        if base in annual and (newest is None or live[base] is None):
            result.current[base] = "annual"
        elif newest is None:
            folder = max(folders[base], key=_key)
            result.current[base] = folder
            result.renames.append((base, f"{base} {folder}"))
        elif live[base] and live[base] != newest:
            result.current[base] = live[base]
    return result


def render_toml(cfg: CourseConfig) -> str:
    lines = ["[courses]", "archived = ["]
    lines += [f"    {json.dumps(name)}," for name in cfg.archived]
    lines += ["]", "", "[courses.current]"]
    lines += [f"{json.dumps(name)} = {json.dumps(version)}" for name, version in sorted(cfg.current.items())]
    return "\n".join(lines) + "\n"


def archive_courses(root: Path) -> list[tuple[str, str]]:
    """(archive version folder, course folder) for every course in the lesson archive."""
    found = set()
    for course in Path(root).glob("*/*/*"):
        version = course.parent.parent.name
        if course.is_dir() and _VERSION_DIR.match(version):
            found.add((version, course.name))
    return sorted(found)


def _get_json(url: str, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_catalog(domain: str, key: str, get: Callable[[str, dict[str, str]], dict] = _get_json) -> list[dict]:
    """Every published course on a domain, read-only, from Skilljar's v1 API. The key never leaves this call."""
    token = base64.b64encode(f"{key}:".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    url: str | None = API.format(domain=domain)
    rows: list[dict] = []
    while url:
        page = get(url, headers)
        rows += catalog_rows(page.get("results", []))
        url = page.get("next")
    return rows
