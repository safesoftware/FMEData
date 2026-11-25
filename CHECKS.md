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
