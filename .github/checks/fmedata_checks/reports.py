"""Write the nightly report: a summary page, a broken-links page, and findings.json."""

from __future__ import annotations

import html
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo

from .lessons import Lesson
from .links import classify_url
from .model import CHECKS, Config, Finding
from .refs import redact

__all__ = ["build_reports", "redact"]

_TEMPLATE = Template((Path(__file__).parent / "templates" / "report.html").read_text(encoding="utf-8"))
_PACIFIC = ZoneInfo("America/Los_Angeles")
# Checks that look at what a pull request changes, so the nightly report never counts them.
PR_ONLY = {"FD006", "FD010"}


def _e(text: object) -> str:
    return html.escape(redact(str(text)))


def _page(title: str, generated_at: datetime, body: str) -> str:
    when = generated_at.astimezone(_PACIFIC).strftime("%A, %Y-%m-%d %H:%M %Z")
    return _TEMPLATE.substitute(title=html.escape(title), generated=html.escape(when), body=body)


def _table(table_id: str, headers: list[str], rows: list[list[str]], filter_box: bool = True) -> str:
    head = "".join(f"<th><button type=\"button\">{html.escape(h)}</button></th>" for h in headers)
    body = "".join("<tr>" + "".join(rows_cell for rows_cell in row) + "</tr>" for row in rows)
    box = (f'<input type="text" class="filter" data-table="{table_id}" placeholder="Filter...">'
           if filter_box else "")
    return f'{box}<table id="{table_id}" class="sortable"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _finding_rows(findings: list[Finding]) -> list[list[str]]:
    return [[
        f'<td class="{f.severity}">{_e(f.severity)}</td>',
        f"<td>{_e(f.check_id)}</td>",
        f"<td>{_e(f.path)}{':' + str(f.line) if f.line else ''}</td>",
        f"<td>{_e(f.message)}</td>",
    ] for f in findings]


def _index_body(findings: list[Finding], exempt: list[str], enforce: set[str]) -> str:
    def is_exempt(f: Finding) -> bool:
        return any(f.path.startswith(p) for p in exempt)

    enforced = [f for f in findings if not is_exempt(f)]
    not_enforced = [f for f in findings if is_exempt(f)]
    act = Counter(f.check_id for f in enforced if f.severity != "notice")
    older = Counter(f.check_id for f in enforced if f.severity == "notice")
    skipped = Counter(f.check_id for f in not_enforced)
    ids = sorted(set(CHECKS) | set(act) | set(older) | set(skipped))

    def name_cell(i: str) -> str:
        name, summary = CHECKS.get(i, ("", ""))
        fails = " <strong>Fails a pull request.</strong>" if i in enforce else ""
        if i in PR_ONLY:
            fails += " Runs on pull requests only."
        return (f'<td><a href="https://github.com/safesoftware/FMEData/blob/main/CHECKS.md#{i.lower()}">{_e(i)}</a>'
                f" {_e(name)}<br><small>{_e(summary)}.{fails}</small></td>")

    count_rows = [[
        name_cell(i),
        f'<td class="num">{act[i]}</td>', f'<td class="num">{older[i]}</td>', f'<td class="num">{skipped[i]}</td>',
    ] for i in ids]
    order = {"error": 0, "warning": 1, "notice": 2}
    enforced.sort(key=lambda f: (order[f.severity], f.check_id, f.path))
    return (
        "<h2>Summary</h2>"
        + _table("counts", ["Check", "To act on", "Older course versions and notices", "Not enforced"],
                 count_rows, filter_box=False)
        + f"<h2>Findings ({len(enforced)})</h2>"
        + _table("findings", ["Severity", "Check", "Where", "Finding"], _finding_rows(enforced))
        + f"<details><summary>Not enforced ({len(not_enforced)}): {_e(', '.join(exempt))}</summary>"
        + _table("exempt", ["Severity", "Check", "Where", "Finding"], _finding_rows(not_enforced))
        + "</details>"
    )


def _broken_rows(lessons: list[Lesson], findings: list[Finding], statuses: dict[str, int | None],
                 cfg: Config) -> list[list[str]]:
    rows, seen = [], set()
    for lesson in lessons:
        for ref in [*lesson.web_refs, *[r for r in lesson.s3_refs if not r.rel]]:
            key = (lesson.rel_html, ref.raw)
            if ref.raw not in statuses or key in seen:
                continue
            seen.add(key)
            kind = classify_url(ref.raw, statuses[ref.raw], cfg)
            if kind != "ok":
                rows.append((lesson, ref.raw, str(statuses[ref.raw] or "no response"), kind))
    by_html = {l.rel_html: l for l in lessons}
    for f in findings:
        if f.check_id == "FT002" and f.path in by_html and "returned" not in f.message:
            rows.append((by_html[f.path], f.message.split(" ", 1)[0], "not in FMEData", "broken"))
    rows.sort(key=lambda r: (r[3] != "broken", r[0].version, r[0].course, r[0].title))
    return [[
        f"<td>{_e(l.version)}</td>", f"<td>{_e(l.course)}</td>", f"<td>{_e(l.title)}</td>",
        f'<td><a href="{_e(url)}">{_e(url)}</a></td>', f"<td>{_e(status)}</td>", f"<td>{_e(kind)}</td>",
    ] for l, url, status, kind in rows]


def build_reports(lessons: list[Lesson], findings: list[Finding], statuses: dict[str, int | None],
                  idx: dict[str, list[str]], out: Path, generated_at: datetime, fmetraining_sha: str = "",
                  exempt: list[str] | None = None, cfg: Config | None = None, fmedata_sha: str = "",
                  current_idx: dict[str, list[str]] | None = None) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    exempt = exempt or []
    cfg = cfg or Config()
    (out / "index.html").write_text(
        _page("FMEData checks", generated_at, _index_body(findings, exempt, cfg.enforce)), encoding="utf-8")
    broken = _broken_rows(lessons, findings, statuses, cfg)
    (out / "broken-links.html").write_text(_page("Broken links in FME Academy lessons", generated_at,
        f"<p>{len(broken)} links. Bot-refused links are sites that block automated checks; open them to confirm.</p>"
        + _table("links", ["Release", "Course", "Lesson", "Link", "Status", "Kind"], broken)), encoding="utf-8")
    payload = {
        "generated_at": generated_at.isoformat(),
        "fmetraining_sha": fmetraining_sha,
        "fmedata_sha": fmedata_sha,
        "lesson_index": idx,
        "current_index": current_idx if current_idx is not None else idx,
        "findings": [{k: redact(v) if isinstance(v, str) else v for k, v in asdict(f).items()} for f in findings],
    }
    (out / "findings.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
