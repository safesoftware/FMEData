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

### FD006

**A change adds something that shouldn't be public.** This repository is public, so its files, its pull requests,
and its Actions logs can be read by anyone. FD006 looks at the lines a pull request adds for access keys and
tokens, private keys, email addresses (other than `@example.com`, `@example.org`, and `@example.net`), and personal
`C:\Users\<name>` folders. It's always enforced, in every folder.

Fix: remove the value from the file. If it was a real key or token, it's already exposed: revoke it and issue a new
one, because deleting it in a later commit leaves it in the history. FME's own header comment in a workspace
(the command line recorded on save) is reported by FD003 instead.

### FD010

**A pull request deletes or renames a file that FME Academy lessons still link.** Lessons link files in this
repository by `C:\FMEData` path and by S3 URL. When `main` changes, the S3 copy changes with it, so a removed or
renamed file breaks every lesson that links it. The finding names the lessons, from the nightly report's lesson
index.

Fix: keep the old file until the lessons are updated in Skilljar, or update the lessons first and then remove it.
If the lesson index is more than a week old, FD010 only warns, because its list may be out of date.
