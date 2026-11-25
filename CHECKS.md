# FMEData checks

Every pull request to this repository runs automated checks on the workspaces and data it changes. A nightly
job also checks the FME Academy lesson pages against this repository and publishes a report:
<https://s3.amazonaws.com/FMEData/reports/index.html>.

This page lists every check: what it looks for, why, and how to fix a failure.

## How to read a failure

A failure looks like this, both in the job log and next to the line in the pull request's "Files changed" tab:

```
FD001 C:\FMEData\Data\Parks\Park.shp not found (see CHECKS.md#fd001)
```

The first word is the check's id. Find its section below. It says how to fix the problem or, if the finding is
intentional, how to record an exception.

- **Error:** fails the pull request. Only checks listed under `enforce` in `.github/checks/checks.toml` can fail
  one, plus FD006, which always can.
- **Warning:** shown on the pull request; doesn't block it.
- **Notice:** listed in the nightly report only.

## Folders that aren't enforced

`Resources/` and partner folders such as `Workspaces/AcceleratorES/` are shared with other teams and partners,
so their findings appear only as notices in the report's "Not enforced" section. Two exceptions apply
everywhere: FD006 (public safety) and FD010 (removing a file a lesson links). The list is `[exempt]` in
`.github/checks/checks.toml`.

## Recording an exception

When a finding is intentional, add an entry to `[allow.paths]` or `[allow.urls]` in `.github/checks/checks.toml`,
with the reason:

```toml
[allow.paths]
"Data/Orthophotos.zip" = "Hosted outside the repo because of its size"
```

An entry without a reason is rejected.

## Running the checks yourself

```
cd .github/checks
python -m pip install pytest
python -m pytest
python -m fmedata_checks pr --repo ../.. --base origin/main
```

## Checks

### FD001

**A workspace's `C:\FMEData` path doesn't match a file in this repository.** Learners extract FMEData to
`C:\FMEData`, so a path that isn't in the repository fails on their machine. "Differs only in case" means the
file exists with different capitalization: Windows doesn't mind, but the S3 copy is case-sensitive.

Fix: add the missing file under `Data/` (or wherever the path points), or correct the path in the workspace and
save it. Paths under `Output/` are ignored, because workspaces write their results there.

### FD002

**A workspace's FMEData S3 URL doesn't resolve.** URLs under `https://s3.amazonaws.com/FMEData/FMEData/` are this
repository's `main` branch, so they're checked against the repository. Other FMEData URLs, such as
`https://s3.amazonaws.com/FMEData/Orthophotos.zip`, are checked over the network in the nightly job only.

Fix: as for FD001. If the file is deliberately hosted outside the repository, add the URL to `[allow.urls]`.

### FD003

**A workspace reads data from a personal `C:\Users\<name>` folder.** No learner has that folder, and the path puts
a person's user name in a public repository. The check never prints the name.

Fix: move the data into FMEData and point the workspace at `C:\FMEData\...` or its S3 URL. A user path in the
workspace's header comment (the command line FME records when it saves) is only a notice; it disappears when the
workspace is saved from `C:\FMEData`.

### FD005

**A workspace is still named `exercise-...`.** The `exercise-` prefix is being phased out. Existing names are
listed in the report as notices; a pull request that adds a new one gets a warning.

Fix: drop the prefix when the workspace is next updated, and update the lessons that link it (FD010 lists them).

### FD006

**A change adds something that shouldn't be public.** This repository is public, so its files, its pull requests,
and its Actions logs can be read by anyone. FD006 looks at the lines a pull request adds for access keys and
tokens, private keys, email addresses (other than `@example.com`, `@example.org`, and `@example.net`), and personal
`C:\Users\<name>` folders. It's always enforced, in every folder.

Fix: remove the value from the file. If it was a real key or token, it's already exposed: revoke it and issue a new
one, because deleting it in a later commit leaves it in the history. FME's own header comment in a workspace
(the command line recorded on save) is reported by FD003 instead. In workspaces, FME writes some characters as
tokens (`<at>` for `@`, `<backslash>` for `\`); an email address or user folder found only that way is a warning,
not a failure, because it's usually a re-save of a workspace that already contained it.

### FD010

**A pull request deletes or renames a file that FME Academy lessons still link.** Lessons link files in this
repository by `C:\FMEData` path and by S3 URL. When `main` changes, the S3 copy changes with it, so a removed or
renamed file breaks every lesson that links it. The finding names the lessons, from the nightly report's lesson
index.

It fails the pull request when a lesson in a course's latest version links the file. When only older course
versions link it, it's a warning: learners on archived content use that year's `FMEData<year>.zip`. If the lesson
index is more than a week old, FD010 only warns, because its list may be out of date.

Fix: keep the old file until the lessons are updated in Skilljar, or update the lessons first and then remove it.
For a deliberate removal while the lesson updates are in progress, add the path to `[allow.paths]` with a reason,
and remove the entry once the lessons are fixed.

### FD011

**A complete workspace's name doesn't end in `-complete`.** Today the same suffix is spelled several ways
(`-Complete`, `_Completed`, `_Complete`, `Complete`, `--complete`, `_complete`), which makes pairs hard to find and
links easy to get wrong. The finding gives the name to use. Accepted endings are `complete_suffixes` in
`.github/checks/checks.toml`.

Fix: rename the file (`git mv`) and update the lessons that link it; FD010 lists them on the pull request. Existing
names are notices in the report until they've been renamed; then FD011 is enforced.

## Lesson checks

These run nightly against the FME Academy lesson archive (<https://github.com/safesoftware/FMETraining>) and appear
in the report, never on a pull request. Lessons are edited in Skilljar; the archive picks up the change after
the next weekly scrape. Findings in a course's latest version are warnings; older versions are notices, because
learners on archived content use that year's `FMEData<year>.zip` and its local paths. Courses whose names match
`ignore_courses` in `.github/checks/checks.toml` (Skilljar copies such as "Clone of …" and test courses) are
skipped.

**How a course's version is read.** From its name, which ends in the FME version it teaches ("Compare Workspaces
2026.2"), the same version Skilljar's tags and labels carry. A course's newest version in the archive is its
latest. Versions are never read from Academy URLs: live courses' URLs have no version, and only archived courses'
URLs carry one. A course whose name has no version, such as "MCP and FME", is treated as archived, so its findings
are notices and FD010 only warns about its links. Adding the version to the course name makes it current.

### FT001

**A lesson's `C:\FMEData` path doesn't match a file in this repository.** Fix: correct the path in the lesson, or
add the file here.

### FT002

**A lesson's FMEData S3 link doesn't resolve.** Links under `FMEData/FMEData/` are checked against this repository;
other FMEData links are checked over the network. Fix: correct the link in the lesson, or restore the file.

### FT003

**An exercise's Resources section doesn't list a complete workspace, or lists one that isn't in this repository.**
A starting workspace is optional, because some exercises start from a blank workspace. "Lesson not parsed" means
the page has no Resources section, so the check couldn't read it. Fix: add or correct the workspace link in the
lesson's Resources section.

### FT005

**A web link in a lesson is broken (the site answered 4xx or 5xx).** Sites that refuse automated requests
(listed under `bot_refusers`, such as support.safe.com) and `localhost` links are listed separately in the report,
not as broken. Fix: update or remove the link in the lesson.

### FT006

**A workspace linked from a lesson was saved in a newer FME version than the course teaches.** A course named
"... 2025.1" is taken in FME 2025.1, which can't open a workspace saved in 2026.2. The report also notes, as a
notice, a workspace that hasn't been saved since before the course's previous version.

Fix: save the workspace in the course's FME version, or update the course.

### FT007

**A lesson links a workspace with the legacy `exercise-` prefix.** See FD005. Fix: when the workspace is renamed,
update the lesson's links.

### FT008

**An exercise that starts from a workspace doesn't say where to find it.** When an exercise opens a starting
workspace, Step 1 gives its full `C:\FMEData` path and the Resources section lists it. FT008 reports Step 1
opening a starting workspace without its path, Step 1 naming a workspace that Resources doesn't list, and Step 1
and Resources naming different workspaces. Exercises that start from a blank workspace aren't affected.

Fix: in Step 1, give the workspace's name and full path, for example "Open the starting workspace
(`C:\FMEData\Workspaces\<folder>\<name>.fmw`)", and list the same file under Resources.

### FT009

**A Skilljar course copy or test course is in the lesson archive.** Course names matching `ignore_courses` in
`.github/checks/checks.toml` (such as "Clone of ..." or containing "TEST") are skipped by the other lesson checks
and listed here, because they shouldn't be in the public archive at all.

Fix: delete or unpublish the copy in Skilljar so the export no longer includes it.
