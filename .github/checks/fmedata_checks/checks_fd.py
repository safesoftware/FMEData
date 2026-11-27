"""Checks on the FMEData repository itself (FD = FMEData)."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from typing import Callable

from .gitdiff import Change
from .model import Config, Finding
from .refs import Ref, decode_fme
from .tree import RepoTree
from .workspace import Workspace

Fetch = Callable[[str], "int | None"]

# Workspaces write their results under Output/, so those paths are destinations, not data.
OUTPUT_PREFIX = "Output/"
WORKSPACE_EXT = (".fmw", ".fmwt")


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
    # A literal value, not a reference such as ${{ secrets.NAME }}: AWS secret keys are 40 base64 characters.
    (re.compile(r"aws_secret_access_key\s*[=:]\s*[\"']?[A-Za-z0-9/+]{40}", re.I), "an AWS secret key setting"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}"), "a GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
_ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
_USER_DIR = re.compile(
    r"c:[\\/]users[\\/](?!(?:Public|Default|Default User|All Users)(?:[\\/\"'<>\s]|$))"
    r"[^\\/\s\"'<>…][^\\/\"'<>]*?(?:[\\/\"'<>\s]|$)",
    re.I)
# Image density suffixes ("icon@2x.png") and git remotes ("git@github.com:") look like addresses but aren't.
_NOT_EMAIL_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "tif", "tiff"}
_NOT_EMAIL_USERS = {"git"}


def _personal_data(text: str) -> str | None:
    for m in _EMAIL.finditer(text):
        address = m.group(0).lower()
        user, _, domain = address.partition("@")
        if (any(domain == d or domain.endswith("." + d) for d in _ALLOWED_EMAIL_DOMAINS) or domain.rsplit(".", 1)[-1] in _NOT_EMAIL_TLDS
                or user in _NOT_EMAIL_USERS):
            continue
        return "an email address"
    if _USER_DIR.search(text):
        return "a personal C:\\Users\\… folder"
    return None


def fd006(path: str, added: list[tuple[int, str]]) -> list[Finding]:
    """Added lines carry no secrets, email addresses, or personal user folders (the repo is public).

    Workspaces write some characters as tokens (<at>, <backslash>), so their text is also checked decoded.
    Personal data found only that way is a warning: it's usually a re-save of a workspace that already had it.
    """
    is_workspace = path.endswith(WORKSPACE_EXT)
    found = []
    for n, text in added:
        decoded = decode_fme(text) if is_workspace else text
        what = next((label for rx, label in _SECRET_PATTERNS if rx.search(decoded)), None)
        severity = "error"
        # FME records the command line it saved from as a plain "#" comment; FD003 reports that as a notice.
        fme_comment = is_workspace and text.startswith("#") and not text.startswith("#!")
        if what is None and not fme_comment:
            what = _personal_data(text)
            if what is None and decoded != text:
                what = _personal_data(decoded)
                severity = "warning"
        if what:
            found.append(Finding("FD006", path, n, f"this line adds {what}; the repository is public", severity))
    return found


def _wildcard_match(path: str, key: str) -> bool:
    """* and ? match within one folder level; [ and ] are literal characters."""
    if not any(ch in key for ch in "*?") or path.count("/") != key.count("/"):
        return False
    return fnmatch.fnmatchcase(path, key.replace("[", "[[]"))


# Folder-based dataset formats: the folder is one dataset, so its files belong to it.
_DATASET_FOLDER = re.compile(r"\.gdb$", re.I)


def _in_dataset_folder(path: str, key: str) -> bool:
    """A linked file geodatabase folder (CommunityMap.gdb) is one dataset; its files belong to it.

    Other folders (Data, Data/Parks, Esri.Training) don't count, so a lesson linking C:\\FMEData\\Data can't
    block every deletion under it.
    """
    return path.startswith(key + "/") and bool(_DATASET_FOLDER.search(key))


def _linked(removed: str | None, idx: dict[str, list[str]], exact_only: bool = False) -> list[str]:
    """Lessons linking a path, as lessons spell it: exactly, in another case, by a wildcard, or by its dataset folder.

    exact_only (a case-only rename): lessons spelled like the new name still work, so matching is case-sensitive.
    """
    if not removed:
        return []
    if exact_only:
        hits = {label for key, labels in idx.items()
                if key == removed or _wildcard_match(removed, key) or _in_dataset_folder(removed, key)
                for label in labels}
        return sorted(hits)
    low = removed.lower()
    hits = {label for key, labels in idx.items()
            if key.lower() == low or _wildcard_match(low, key.lower()) or _in_dataset_folder(low, key.lower())
            for label in labels}
    return sorted(hits)


def fd010(changes: list[Change], idx: dict[str, list[str]], stale: bool,
          current: dict[str, list[str]] | None = None, cfg: Config | None = None) -> list[Finding]:
    """A change that deletes or renames a file that lessons still link.

    It fails only when a lesson in a course's latest version links the file (current); links from older
    course versions alone give a warning. Without a current index, every linking lesson counts.
    """
    allow = cfg.allow_paths if cfg else {}
    found = []
    for c in changes:
        removed = c.path if c.status == "D" else c.old_path if c.status == "R" else None
        # After a case-only rename, lessons spelled like the new name still work; only the old spelling breaks.
        exact = c.status == "R" and removed is not None and removed.lower() == c.path.lower()
        lessons = _linked(removed, idx, exact)
        if not lessons or removed in allow:
            continue
        live = lessons if current is None else _linked(removed, current, exact)
        shown_from = live or lessons
        shown = "; ".join(shown_from[:3]) + (f"; and {len(shown_from) - 3} more" if len(shown_from) > 3 else "")
        if live:
            msg = (f"removes {removed}, still linked by {len(live)} current lesson(s): {shown}. "
                   "Restore it, or update those lessons in Skilljar first")
        else:
            msg = (f"removes {removed}, linked only by {len(lessons)} lesson(s) in older course versions: {shown}")
        if stale:
            found.append(Finding("FD010", removed, None, msg + " (lesson index is stale; check the report)", "warning"))
        else:
            found.append(Finding("FD010", removed, None, msg, "error" if live else "warning"))
    return found



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


def folder_zips(tree: RepoTree) -> dict[str, str]:
    """Folder-dataset zips: a .zip named after a folder beside it (Data/Parks.zip for Data/Parks)."""
    return {z: z[:-4] for z in sorted(tree.all_files()) if z.lower().endswith(".zip") and tree.is_dir(z[:-4])}


def fd012_changes(changes: list[Change], tree: RepoTree) -> list[Finding]:
    """A pull request that changes a folder-dataset folder also updates its zip."""
    touched = {c.path for c in changes} | {c.old_path for c in changes if c.old_path}
    found = []
    for zip_rel, folder in folder_zips(tree).items():
        if zip_rel not in touched and any(p.startswith(folder + "/") for p in touched):
            found.append(Finding("FD012", zip_rel, None,
                                 f"this change updates {folder}/ but not {zip_rel}; re-zip the folder and commit "
                                 "the zip, because lessons link the zip", "warning"))
    return found


def _last_change(repo, rel: str) -> tuple[str, str]:
    """The last commit that touched rel, and its date."""
    out = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=false", "--literal-pathspecs", "log", "-1", "--format=%H %cs",
                          "--", rel], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()
    return (out[0], out[1]) if len(out) == 2 else ("", "")


def _is_ancestor(repo, older: str, newer: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
                          capture_output=True).returncode == 0


def fd012_history(repo, tree: RepoTree) -> list[Finding]:
    """A folder-dataset zip isn't older than the last change to its folder (by commit order, not clock time)."""
    found = []
    for zip_rel, folder in folder_zips(tree).items():
        folder_commit, folder_day = _last_change(repo, folder + "/")
        zip_commit, zip_day = _last_change(repo, zip_rel)
        # Stale unless the zip's last commit already contains the folder's last change (parallel branches count).
        if folder_commit and zip_commit and folder_commit != zip_commit and not _is_ancestor(repo, folder_commit, zip_commit):
            found.append(Finding("FD012", zip_rel, None,
                                 f"{folder}/ has changes (last on {folder_day}) that {zip_rel} (last updated "
                                 f"{zip_day}) doesn't include; re-zip the folder and commit the zip", "warning"))
    return found


# FD004. Names aren't standardized yet, so "complete" has many spellings (-complete, --complete, _Completed,
# -Complete, Complete, _Completo, _complete, .Complete), sometimes followed by more ("-complete-advanced").
_COMPLETE_WORD = re.compile(r"(?P<sep>-{1,2}|_|\.|\s)?(?P<word>completed?|completo|complet)(?=[-_.\s]|$)", re.I)
# Words a starting workspace's name may carry where the complete one says "complete".
_START_WORDS = ("", "start", "starting", "begin", "beginning", "initial", "inicio", "blank")


def _squash(name: str) -> str:
    """A name without case or separators, so "Ex3.1_Writing" and "ex3.1-writing" compare equal."""
    return re.sub(r"[-_\s]+", "", name).lower()


def _complete_parts(stem: str) -> tuple[str, str] | None:
    # Each "complete" in the name is a candidate, so "Ex1-Incomplete-Complete" pairs on its second one.
    for m in _COMPLETE_WORD.finditer(stem):
        # Without a separator, only a capitalized "Complete" starts a suffix ("incomplete" is a word).
        if not m.group("sep") and not m.group("word")[0].isupper():
            continue
        base = _squash(stem[:m.start()])
        if base:
            return base, _squash(stem[m.end():]).lstrip(".")
    return None


def complete_base(stem: str) -> str | None:
    """The squashed name a complete workspace shares with its starting one, or None if it isn't a complete one."""
    parts = _complete_parts(stem)
    return parts[0] + parts[1] if parts else None


def _stem(rel: str) -> tuple[str, str]:
    folder, _, name = rel.rpartition("/")
    return folder, name.rsplit(".", 1)[0]


def starting_partners(rel: str, paths) -> list[str]:
    """Workspaces in rel's folder named like rel with "complete" removed or swapped for a start word."""
    folder, stem = _stem(rel)
    parts = _complete_parts(stem)
    if parts is None:
        return []
    base, tail = parts
    wanted = {name for w in _START_WORDS for name in (base + w + tail, base + tail + w, w + base + tail)}
    found = []
    for p in paths:
        other_folder, other = _stem(p)
        if (p != rel and p.endswith(WORKSPACE_EXT) and other_folder == folder and _complete_parts(other) is None
                and _squash(other) in wanted):
            found.append(p)
    return found


def fd004(paths, exercises, tree: RepoTree, only: set[str] | None = None,
          renamed: dict[str, str] | None = None) -> list[Finding]:
    """A complete workspace whose exercise starts from a workspace has that starting workspace beside it.

    Only the exercise says whether one is needed: many start from a blank canvas or from an earlier exercise's
    result. So a complete workspace without a starting partner is reported only when a lesson listing it as the
    complete workspace starts from a workspace that isn't in the repository, or opens one in Step 1 without
    listing it. Complete workspaces no lesson lists aren't guessed at.

    exercises come from the lessons (nightly) or from the published findings.json (pull requests). only limits
    the check to some complete workspaces; renamed maps a renamed workspace to its old name, which lessons still use.
    """
    paths = [p for p in paths if p.endswith(WORKSPACE_EXT)]
    renamed = renamed or {}
    by_complete: dict[str, list] = {}
    for ex in exercises:
        for rel in ex.complete:
            by_complete.setdefault(rel.lower(), []).append(ex)
    found = []
    for rel in paths:
        # Lessons type paths by hand and Windows ignores case, so a lesson's spelling may differ from the repo's.
        listing = by_complete.get(rel.lower(), []) + by_complete.get(renamed.get(rel, "").lower(), [])
        if ((only is not None and rel not in only) or not listing or complete_base(_stem(rel)[1]) is None
                or starting_partners(rel, paths)):
            continue
        reasons, current = [], False
        for ex in listing:
            missing = [s for s in ex.starting if tree.resolve(s) == "missing"]
            if ex.starting and len(missing) == len(ex.starting):
                reasons.append(f"{ex.label} starts from {missing[0]}, which isn't in FMEData")
            elif (not ex.starting and ex.step1_start
                  and not any(tree.resolve(w) != "missing" for w in ex.step1_workspaces
                              if w.lower() not in {c.lower() for c in ex.complete})):
                # Step 1 naming a workspace that exists (often an earlier exercise's result) is a start, too.
                reasons.append(f"{ex.label} opens a starting workspace in Step 1 but doesn't list one")
            else:
                continue
            current = current or ex.current
        if reasons:
            more = f" (and {len(reasons) - 1} more lesson(s))" if len(reasons) > 1 else ""
            found.append(Finding("FD004", rel, None,
                                 f"no starting workspace beside this complete one, but {reasons[0]}{more}. "
                                 "Add the starting workspace next to it, or fix the lesson",
                                 "warning" if current else "notice"))
    return found


def fd004_changes(changes: list[Change], exercises, tree: RepoTree) -> list[Finding]:
    """FD004 on a pull request: complete workspaces it adds or renames, and those whose starting workspace it removes."""
    only = {c.path for c in changes if c.status in ("A", "R") and c.path.endswith(WORKSPACE_EXT)}
    removed = {c.path if c.status == "D" else c.old_path for c in changes if c.status in ("D", "R")}
    removed_low = {r.lower() for r in removed}
    paths = [p for p in tree.all_files() if p.endswith(WORKSPACE_EXT)]
    # The workspaces before the PR, so a removed starting workspace can still be paired with its complete one.
    before = {p.lower(): p for p in [*paths, *(r for r in removed if r.endswith(WORKSPACE_EXT))]}
    for ex in exercises:
        # A starting workspace the lesson lists or Step 1 names, or (Step 1 cases) the one beside the complete one.
        hit = removed_low & {s.lower() for s in (*ex.starting, *ex.step1_workspaces)}
        hit = hit or any(p.lower() in removed_low for c in ex.complete if c.lower() in before
                         for p in starting_partners(before[c.lower()], before.values()))
        if hit:
            only.update(before.get(c.lower(), c) for c in ex.complete)
    renamed = {c.path: c.old_path for c in changes if c.status == "R" and c.old_path}
    return fd004(paths, exercises, tree, only=only, renamed=renamed)


def _dataset(rel: str) -> str:
    """A file's dataset: its folder and name up to the first dot (Parks.shp, Parks.dbf, and Parks.prj are one)."""
    folder, _, name = rel.rpartition("/")
    return f"{folder}/{name.split('.', 1)[0]}".lower()


def fd007(tree: RepoTree, refs) -> list[Finding]:
    """Data files under Data/ that no workspace or lesson references. Report only; a person decides what to remove.

    A reference uses the whole dataset: a file's same-named siblings (a shapefile's parts), everything in a
    referenced folder, a folder dataset and its zip (Data/Parks and Data/Parks.zip), and a zip whose folder a
    path reads into (Data/City/CityProperties/CityProperties.shp uses Data/City/CityProperties.zip). Matching
    ignores case, because Windows does. A reference to Data itself uses nothing.
    """
    files = sorted(f for f in tree.all_files() if f.startswith("Data/"))
    low = {f.lower(): f for f in files}
    used_files: set[str] = set()
    used_prefixes: set[str] = set()
    used_datasets: set[str] = set()
    patterns: list[str] = []
    for ref in refs:
        r = ref.replace("\\", "/").strip("/").lower()
        if not r.startswith("data/"):
            continue
        if any(ch in r for ch in "*?["):
            patterns.append(r)
            continue
        used_prefixes.add(r + "/")
        parts = r.split("/")
        for i in range(2, len(parts) + 1):
            head = "/".join(parts[:i])
            if head + ".zip" in low:  # a folder dataset's zip, or the zip a path reads into
                used_files.add(head + ".zip")
            if head.endswith(".zip"):  # a zip's folder dataset
                used_prefixes.add(head[:-4] + "/")
        if r in low:
            used_files.add(r)
            used_datasets.add(_dataset(low[r]))
    for f in files:
        if any(fnmatch.fnmatchcase(f.lower(), p) for p in patterns):
            used_datasets.add(_dataset(f))
    unused = [f for f in files
              if not (f.lower() in used_files or _dataset(f) in used_datasets
                      or any(f.lower().startswith(p) for p in used_prefixes))]
    return _unused_findings(files, unused)


def _unused_findings(files: list[str], unused: list[str]) -> list[Finding]:
    """One finding per wholly unused folder (the topmost below Data/), and one per other unused dataset."""
    unused_set = set(unused)
    by_folder: dict[str, list[str]] = {}
    for f in files:
        parts = f.split("/")
        for i in range(2, len(parts)):
            by_folder.setdefault("/".join(parts[:i]), []).append(f)
    whole = sorted(d for d, fs in by_folder.items() if all(f in unused_set for f in fs))
    whole = [d for d in whole if not any(d.startswith(o + "/") for o in whole)]
    found, done = [], set()
    for d in whole:
        fs = by_folder[d]
        zip_rel = d + ".zip"
        also = f", nor its zip {zip_rel}" if zip_rel in unused_set else ""
        found.append(Finding("FD007", d + "/", None,
                             f"no workspace or lesson uses the {len(fs)} file(s) in this folder "
                             f"({len({_dataset(f) for f in fs})} datasets){also}. Check that nothing else needs "
                             "them before removing them", "notice"))
        done.update(fs)
        if also:
            done.add(zip_rel)
    groups: dict[str, list[str]] = {}
    for f in unused:
        if f not in done:
            groups.setdefault(_dataset(f), []).append(f)
    for fs in groups.values():
        where = fs[0] if len(fs) == 1 else f"{fs[0].rsplit('.', 1)[0]}.*"
        what = "this file" if len(fs) == 1 else f"these {len(fs)} files"
        found.append(Finding("FD007", where, None,
                             f"no workspace or lesson uses {what}. Check that nothing else needs it before removing it",
                             "notice"))
    return sorted(found, key=lambda x: x.path)
