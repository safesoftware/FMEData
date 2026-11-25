"""Checks on the FMEData repository itself (FD = FMEData)."""

from __future__ import annotations

from typing import Callable

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
