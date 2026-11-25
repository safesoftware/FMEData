# Branches and the yearly cycle

`main` holds the current year's data and workspaces. It's what the FME Academy's current courses link, and
every push to it publishes to <https://s3.amazonaws.com/FMEData/FMEData/index.html> and `FMEData.zip`.

Each spring, when the next year's course updates begin, `main` is archived to a branch named for its year, and
that year's files are published as one zip:

| Branch | Holds | Published as |
|---|---|---|
| `main` | The current year | `s3://FMEData/FMEData/` and `FMEData.zip` |
| `2026`, `2025`, ... | That year, archived | `FMEData2026.zip`, `FMEData2025.zip`, ... |
| `2027` (before rollover) | Next year's work, kept off `main` until rollover | Nothing until it's merged |

## Archived content

Archived course versions live on S3, not Skilljar. A learner taking one downloads that year's zip (for example
<https://s3.amazonaws.com/FMEData/FMEData2025.zip>), extracts it so its contents sit in `C:\FMEData`, and the
workspaces and data work from their local paths. Links aren't versioned: lessons always link `main`, and most S3
data links in older workspaces keep working because data rarely changes between years.

## Rollover, step by step

1. **Dry run.** In Actions, run **Yearly rollover** with `year` set to the year being archived (for example
   `2026`), `mode` set to `archive`, and `dry_run` on. It checks that the year branch doesn't exist yet and builds
   the zip without publishing anything.
2. **Archive.** Run it again with `dry_run` off. It creates the year branch from `main` and uploads
   `FMEData<year>.zip`. The run summary lists the next steps.
3. **Lock the archive.** Add the year branch to the archived-years branch ruleset (Settings > Rules), so it only
   changes through a pull request.
4. **Merge next year's work.** If a branch for next year exists, open the pull request the run summary links to,
   which merges it into `main`. The checks run on it like any other pull request, and FD010 lists every current
   lesson linking a file the new year removes or renames.

To fix something in an archived year, open a pull request into its branch, then run **Yearly rollover** with
`mode` set to `rezip` to rebuild and re-upload that year's zip.

## Checks on year branches

The checks in [CHECKS.md](CHECKS.md) run on pull requests into year branches too, except FD010: lessons link
`main`, so only changes landing on `main` can break them.
