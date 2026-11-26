"""Command line: `pr` checks a pull request's changes; `lessons` builds the nightly report.

    python -m fmedata_checks pr --repo . --base origin/main
    python -m fmedata_checks lessons --repo . --fmetraining ../FMETraining --out out
    python -m fmedata_checks courses --fmetraining ../FMETraining   (local only: reads Skilljar's catalog)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import checks_fd, checks_ft, courses
from .gitdiff import added_lines, changed_files
from .lessons import current_index, ignored_courses, is_current, iter_lessons, latest_versions, lesson_index, previous_version, read_index
from .links import check_urls, http_status
from .model import Finding, annotation, effective, load_config
from .reports import build_reports
from .tree import RepoTree
from .workspace import parse_workspace

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "checks.toml"
DEFAULT_INDEX = "https://s3.amazonaws.com/FMEData/reports/findings.json"
WORKSPACE_EXT = (".fmw", ".fmwt")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run_pr(args) -> int:
    cfg = load_config(Path(args.config))
    repo = Path(args.repo)
    tree = RepoTree.from_git(repo)
    changes = changed_files(repo, args.base)
    findings: list[Finding] = []
    for c in changes:
        if c.status == "D":
            continue
        if c.path.endswith(WORKSPACE_EXT):
            ws = parse_workspace(c.path, _read(repo / c.path))
            findings += checks_fd.fd001(ws, tree, cfg)
            findings += checks_fd.fd002(ws, tree, cfg, fetch=None)
            findings += checks_fd.fd003(ws)
        findings += checks_fd.fd006(c.path, added_lines(repo, args.base, c.path, old_path=c.old_path))
    new_names = [c.path for c in changes if c.status in ("A", "R")]
    findings += checks_fd.fd005(new_names, pr_added=True)
    findings += checks_fd.fd011(new_names, pr_added=True, cfg=cfg)
    findings += checks_fd.fd012_changes(changes, tree)
    # "--index none" (pull requests into a year branch): lessons link main, so FD010 doesn't apply.
    if args.index != "none":
        idx, current, stale = read_index(args.index, with_current=True)
        findings += checks_fd.fd010(changes, idx, stale, current=current, cfg=cfg)

    shown = [f for f in (effective(f, cfg) for f in findings) if f.severity != "notice"]
    for f in shown:
        print(annotation(f))
    errors = sum(f.severity == "error" for f in shown)
    print(f"{len(changes)} changed file(s): {errors} error(s), {len(shown) - errors} warning(s). See CHECKS.md.")
    return 1 if errors else 0


def run_lessons(args) -> int:
    cfg = load_config(Path(args.config))
    repo = Path(args.repo)
    tree = RepoTree.from_git(repo)
    fetch = None if args.no_network else http_status

    findings: list[Finding] = []
    workspaces = {}
    for rel in sorted(tree.all_files()):
        if rel.endswith(WORKSPACE_EXT):
            ws = workspaces[rel] = parse_workspace(rel, _read(repo / rel))
            findings += checks_fd.fd001(ws, tree, cfg) + checks_fd.fd003(ws)
            findings += checks_fd.fd002(ws, tree, cfg, fetch=fetch)
    findings += checks_fd.fd005(workspaces, pr_added=False)
    findings += checks_fd.fd011(workspaces, pr_added=False, cfg=cfg)
    findings += checks_fd.fd012_history(repo, tree)

    lessons = list(iter_lessons(Path(args.fmetraining), cfg.ignore_courses, cfg.course_versions))
    latest = latest_versions(lessons, cfg.course_versions, cfg.archived_courses)
    urls = {r.raw for l in lessons for r in [*l.web_refs, *l.s3_refs] if not r.rel}
    statuses = {} if args.no_network else check_urls(urls, http_status, workers=args.workers)
    for lesson in lessons:
        current = is_current(lesson, latest)
        findings += checks_ft.ft001(lesson, tree, cfg, current)
        findings += checks_ft.ft002(lesson, tree, cfg, statuses, current)
        findings += checks_ft.ft003(lesson, tree, current)
        findings += checks_ft.ft005(lesson, statuses, cfg, current)
        findings += checks_ft.ft006(lesson, workspaces, current, previous_version(lesson, lessons))
        findings += checks_ft.ft007(lesson, current)
        findings += checks_ft.ft008(lesson, current)
    findings += checks_ft.ft009(ignored_courses(Path(args.fmetraining), cfg.ignore_courses))

    findings = [effective(f, cfg) for f in findings]
    build_reports(lessons, findings, statuses, lesson_index(lessons), Path(args.out),
                  datetime.now(timezone.utc), fmetraining_sha=args.sha, exempt=list(cfg.exempt), cfg=cfg,
                  fmedata_sha=args.fmedata_sha, current_idx=current_index(lessons, cfg.course_versions, cfg.archived_courses))
    print(f"{len(lessons)} lessons, {len(findings)} findings; report in {args.out}")
    return 0


def run_courses(args) -> int:
    """Print checks.toml's [courses] table from Skilljar's published catalog, and the renames it suggests."""
    cfg = load_config(Path(args.config))
    if args.catalog:
        catalog = courses.catalog_rows(json.loads(Path(args.catalog).read_text(encoding="utf-8")))
    else:
        key = os.environ.get("SKILLJAR_API_KEY")
        if not key:
            print("Set SKILLJAR_API_KEY (read-only use) or pass --catalog with a saved list of {title, slug}.",
                  file=sys.stderr)
            return 2
        catalog = courses.fetch_catalog(args.domain, key)
    annual = [name for name, version in cfg.course_versions.items() if version == "annual"]
    found = courses.derive(courses.archive_courses(Path(args.fmetraining)), catalog, cfg.ignore_courses, annual)
    print(f"# From {len(catalog)} published courses on {args.domain}. Replace the [courses] table in checks.toml.")
    print(courses.render_toml(found), end="")
    if found.renames:
        print("\n# Courses to rename in Skilljar so their names carry their version:")
        for old, new in found.renames:
            print(f"#   {old} -> {new}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fmedata_checks")
    sub = parser.add_subparsers(dest="command", required=True)
    pr = sub.add_parser("pr", help="check a pull request's changes")
    pr.add_argument("--repo", default=".")
    pr.add_argument("--base", required=True)
    pr.add_argument("--index", default=DEFAULT_INDEX, help="findings.json with the lesson index (path or URL), or 'none' to skip FD010")
    pr.add_argument("--config", default=str(DEFAULT_CONFIG))
    les = sub.add_parser("lessons", help="check the lesson archive and write the report")
    les.add_argument("--repo", default=".")
    les.add_argument("--fmetraining", required=True)
    les.add_argument("--out", required=True)
    les.add_argument("--no-network", action="store_true")
    les.add_argument("--workers", type=int, default=8)
    les.add_argument("--sha", default="", help="FMETraining commit the archive was read at")
    les.add_argument("--fmedata-sha", default="", help="FMEData commit the checks ran on")
    les.add_argument("--config", default=str(DEFAULT_CONFIG))
    crs = sub.add_parser("courses", help="print checks.toml's [courses] table from Skilljar's catalog (local only)")
    crs.add_argument("--fmetraining", required=True)
    crs.add_argument("--catalog", help="saved JSON list of published courses ({title, slug}); else SKILLJAR_API_KEY")
    crs.add_argument("--domain", default="academy.safe.com")
    crs.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args(argv)
    return {"pr": run_pr, "lessons": run_lessons, "courses": run_courses}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
