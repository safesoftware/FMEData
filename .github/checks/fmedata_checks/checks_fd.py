"""Checks on the FMEData repository itself (FD = FMEData)."""

from __future__ import annotations

import re
from typing import Callable

from .gitdiff import Change
from .model import Config, Finding
from .refs import Ref
from .tree import RepoTree
from .workspace import Workspace

Fetch = Callable[[str], "int | None"]

# Workspaces write their results under Output/, so those paths are destinations, not data.
OUTPUT_PREFIX = "Output/"


def _first_per_rel(refs: list[Ref]) -> list[Ref]:
    seen, out = set(), []
    for r in refs:
        if r.rel not in seen:
            seen.add(r.rel)
            out.append(r)
    return out


def _resolution_message(rel: str, tree: RepoTree, shown: str) -> str | None:
    status = tree.resolve(rel)
    if status == "exact":
        return None
    if status == "case":
        return f"{shown} differs only in case from {tree.actual(rel) or rel}; S3 links are case-sensitive"
    return f"{shown} not found in FMEData"


def fd001(ws: Workspace, tree: RepoTree, cfg: Config) -> list[Finding]:
    """Every C:\\FMEData dataset path in a workspace resolves to a file or folder in the repo."""
    found = []
    for r in _first_per_rel(ws.local_refs):
        if r.rel.startswith(OUTPUT_PREFIX) or r.rel in cfg.allow_paths:
            continue
        msg = _resolution_message(r.rel, tree, r.rel)
        if msg:
            found.append(Finding("FD001", ws.path, r.line, msg, "error"))
    return found


def fd002(ws: Workspace, tree: RepoTree, cfg: Config, fetch: Fetch | None) -> list[Finding]:
    """FMEData S3 URLs in a workspace resolve: in-repo ones against the tree, others over the network."""
    found = []
    seen = set()
    for r in ws.s3_refs:
        if r.raw in seen or r.raw in cfg.allow_urls:
            continue
        seen.add(r.raw)
        if r.rel:
            if r.rel.startswith(OUTPUT_PREFIX) or r.rel in cfg.allow_paths:
                continue
            msg = _resolution_message(r.rel, tree, r.raw)
            if msg:
                found.append(Finding("FD002", ws.path, r.line, msg, "error"))
        elif fetch is not None:
            status = fetch(r.raw)
            if status is None or status >= 400:
                found.append(Finding("FD002", ws.path, r.line,
                                     f"{r.raw} returned {status if status else 'no response'}", "error"))
    return found


_SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "an AWS access key id"),
    (re.compile(r"aws_secret_access_key", re.I), "an AWS secret key setting"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}"), "a GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
_ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
_USER_DIR = re.compile(r"[Cc]:[\\/]Users[\\/](?!Public[\\/]|…)[^\\/\s\"'<>]+[\\/]")


def fd006(path: str, added: list[tuple[int, str]]) -> list[Finding]:
    """Added lines carry no secrets, email addresses, or personal user folders (the repo is public)."""
    found = []
    for n, text in added:
        what = next((label for rx, label in _SECRET_PATTERNS if rx.search(text)), None)
        if what is None:
            for m in _EMAIL.finditer(text):
                if not m.group(0).lower().endswith(_ALLOWED_EMAIL_DOMAINS):
                    what = "an email address"
                    break
        # FME records the command line it saved from as a plain "#" comment; FD003 reports that as a notice.
        fme_comment = path.endswith((".fmw", ".fmwt")) and text.startswith("#") and not text.startswith("#!")
        if what is None and not fme_comment and _USER_DIR.search(text):
            what = "a personal C:\\Users\\… folder"
        if what:
            found.append(Finding("FD006", path, n, f"this line adds {what}; the repository is public", "error"))
    return found


def fd010(changes: list[Change], idx: dict[str, list[str]], stale: bool) -> list[Finding]:
    """A change that deletes or renames a file that lessons still link."""
    found = []
    for c in changes:
        removed = c.path if c.status == "D" else c.old_path if c.status == "R" else None
        lessons = idx.get(removed or "", [])
        if not lessons:
            continue
        shown = "; ".join(lessons[:3]) + (f"; and {len(lessons) - 3} more" if len(lessons) > 3 else "")
        msg = (f"removes {removed}, still linked by {len(lessons)} lesson(s): {shown}. "
               "Restore it, or update those lessons in Skilljar first")
        if stale:
            found.append(Finding("FD010", removed, None, msg + " (lesson index is stale; check the report)", "warning"))
        else:
            found.append(Finding("FD010", removed, None, msg, "error"))
    return found


WORKSPACE_EXT = (".fmw", ".fmwt")


def fd005(paths, pr_added: bool) -> list[Finding]:
    """A workspace still named exercise-*; the prefix is being phased out."""
    return [Finding("FD005", p, None, "legacy exercise- prefix; drop it when the workspace is next updated",
                    "warning" if pr_added else "notice")
            for p in paths if p.endswith(WORKSPACE_EXT) and p.rsplit("/", 1)[-1].startswith("exercise-")]


_COMPLETE = re.compile(r"^(?P<base>.*?)(?P<sep>-{1,2}|_|\s)?(?P<word>complete[d]?|completo|complet)$", re.I)


def fd011(paths, pr_added: bool, cfg: Config) -> list[Finding]:
    """A complete workspace's name ends in exactly one of the accepted suffixes (default -complete)."""
    found = []
    for p in paths:
        if not p.endswith(WORKSPACE_EXT):
            continue
        folder, _, name = p.rpartition("/")
        stem, ext = name.rsplit(".", 1)
        m = _COMPLETE.match(stem)
        if not m or not m.group("base"):
            continue
        # Without a separator, only a capitalized "Complete" starts a suffix ("incomplete" is a word).
        if not m.group("sep") and not m.group("word")[0].isupper():
            continue
        suffix = m.group("sep") or ""
        actual = suffix + m.group("word")
        if actual in cfg.complete_suffixes:
            continue
        word = m.group("word").lower()
        wanted = next((s for s in cfg.complete_suffixes if s.lstrip("-_ ").lower() == word), None) \
            or next((s for s in cfg.complete_suffixes if word.startswith(s.lstrip("-_ ").lower())), None) \
            or cfg.complete_suffixes[0]
        target = f"{folder}/{m.group('base')}{wanted}.{ext}" if folder else f"{m.group('base')}{wanted}.{ext}"
        found.append(Finding("FD011", p, None, f"rename to {target}", "error" if pr_added else "notice"))
    return found


def fd003(ws: Workspace) -> list[Finding]:
    """No personal C:\\Users paths: an error in a dataset, a notice in FME's command-line comment."""
    found = []
    for r in ws.dataset_user_paths:
        found.append(Finding("FD003", ws.path, r.line,
                             "dataset path under C:\\Users\\…; use C:\\FMEData or an S3 URL", "error"))
    for r in ws.header_user_paths[:1]:
        found.append(Finding("FD003", ws.path, r.line,
                             "header comment contains C:\\Users\\…; harmless, but re-saving from C:\\FMEData removes it",
                             "notice"))
    return found
