"""Checks on FME Academy lesson pages against FMEData (FT = FMETraining).

Lessons are fixed in Skilljar, not here, so these findings never fail a pull request. A lesson in a course's
latest version gets warnings; older versions get notices.
"""

from __future__ import annotations

from .checks_fd import OUTPUT_PREFIX, _resolution_message
from .lessons import Lesson
from .links import classify_url
from .model import Config, Finding, Severity
from .tree import RepoTree


def _sev(current: bool) -> Severity:
    return "warning" if current else "notice"


def ft001(lesson: Lesson, tree: RepoTree, cfg: Config, current: bool) -> list[Finding]:
    """C:\\FMEData paths in a lesson resolve to files in FMEData."""
    found, seen = [], set()
    for r in lesson.local_refs:
        if r.rel in seen or r.rel.startswith(OUTPUT_PREFIX) or r.rel in cfg.allow_paths:
            continue
        seen.add(r.rel)
        msg = _resolution_message(r.rel, tree, r.rel)
        if msg:
            found.append(Finding("FT001", lesson.rel_html, None, msg, _sev(current)))
    return found


def ft002(lesson: Lesson, tree: RepoTree, cfg: Config, statuses: dict[str, int | None],
          current: bool) -> list[Finding]:
    """FMEData S3 links in a lesson resolve: main-branch ones against the tree, others by their HTTP status."""
    found, seen = [], set()
    for r in lesson.s3_refs:
        if r.raw in seen or r.raw in cfg.allow_urls:
            continue
        seen.add(r.raw)
        if r.rel:
            msg = _resolution_message(r.rel, tree, r.raw)
        else:
            status = statuses.get(r.raw)
            kind = classify_url(r.raw, status, cfg)
            msg = None if kind == "ok" or r.raw not in statuses else f"{r.raw} returned {status or 'no response'}"
        if msg:
            found.append(Finding("FT002", lesson.rel_html, None, msg, _sev(current)))
    return found


def ft003(lesson: Lesson, tree: RepoTree, current: bool) -> list[Finding]:
    """An exercise lists its complete workspace (and starting one, if any), and they exist."""
    if not lesson.is_exercise:
        return []
    if not lesson.parsed:
        return [Finding("FT003", lesson.rel_html, None, "lesson not parsed: no Resources section", "notice")]
    found = []
    if not lesson.complete:
        found.append(Finding("FT003", lesson.rel_html, None, "no complete workspace listed in Resources", _sev(current)))
    for kind, rels in (("starting", lesson.starting), ("complete", lesson.complete)):
        for rel in rels:
            if tree.resolve(rel) == "missing":
                found.append(Finding("FT003", lesson.rel_html, None,
                                     f"{kind} workspace {rel} not found in FMEData", _sev(current)))
    return found


def ft005(lesson: Lesson, statuses: dict[str, int | None], cfg: Config, current: bool) -> list[Finding]:
    """Web links in a lesson answer. Bot-refusing hosts and localhost are reported separately, not as broken."""
    found, seen = [], set()
    for r in lesson.web_refs:
        if r.raw in seen or r.raw in cfg.allow_urls or r.raw not in statuses:
            continue
        seen.add(r.raw)
        if classify_url(r.raw, statuses[r.raw], cfg) == "broken":
            found.append(Finding("FT005", lesson.rel_html, None,
                                 f"{r.raw} returned {statuses[r.raw]}", _sev(current)))
    return found
