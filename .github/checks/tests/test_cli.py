import json
import subprocess
from pathlib import Path

from fmedata_checks.__main__ import main


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "Data").mkdir()
    (repo / "Data" / "Parks.shp").write_text("x", encoding="utf-8")
    (repo / "Workspaces").mkdir()
    (repo / "Workspaces" / "a.fmw").write_text("DEFAULT_MACRO S C:\\FMEData\\Data\\Parks.shp\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "branch", "base")
    return repo


def config(tmp_path: Path, ignore: str = "") -> Path:
    p = tmp_path / "checks.toml"
    p.write_text(f'enforce = []\n{ignore}[exempt]\n"Resources/" = "shared"\n', encoding="utf-8")
    return p


def run_pr(repo: Path, tmp_path: Path, capsys) -> tuple[int, str]:
    code = main(["pr", "--repo", str(repo), "--base", "base", "--index", str(tmp_path / "none.json"),
                 "--config", str(config(tmp_path))])
    return code, capsys.readouterr().out


def test_cli_pr_secret_fails(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "notes.txt").write_text("key " + "AKIA" + "ABCDEFGHIJKLMNOP\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "oops")
    code, out = run_pr(repo, tmp_path, capsys)
    assert code == 1
    assert "::error file=notes.txt,line=1::FD006" in out


def test_cli_pr_warning_only_passes(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "Workspaces" / "b.fmw").write_text("DEFAULT_MACRO S C:\\FMEData\\Data\\Gone.shp\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add b")
    code, out = run_pr(repo, tmp_path, capsys)
    assert code == 0
    assert "::warning file=Workspaces/b.fmw,line=1::FD001" in out
    assert "a.fmw" not in out  # unchanged workspaces aren't checked on a PR


def test_cli_pr_exempt_folder_silent(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "Resources").mkdir()
    (repo / "Resources" / "c.fmw").write_text("DEFAULT_MACRO S C:\\FMEData\\Data\\Gone.shp\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add c")
    code, out = run_pr(repo, tmp_path, capsys)
    assert code == 0 and "Resources/c.fmw" not in out


def test_cli_pr_new_names_flagged(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    for name in ("x_Complete.fmw", "exercise-y.fmw"):
        (repo / "Workspaces" / name).write_text("DEFAULT_MACRO S 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "names")
    code, out = run_pr(repo, tmp_path, capsys)
    assert code == 0
    assert "::warning file=Workspaces/x_Complete.fmw::FD011 rename to Workspaces/x-complete.fmw" in out
    assert "::warning file=Workspaces/exercise-y.fmw::FD005" in out


def test_cli_lessons_reports_version_and_legacy(tmp_path: Path):
    repo = make_repo(tmp_path)
    (repo / "Workspaces" / "exercise-z-complete.fmw").write_text(
        '#!   LAST_SAVE_BUILD="FME(R) 2026.2.0.0 (20260617 - Build 26333 - WIN64)"\nX\n', encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "z")
    archive = tmp_path / "FMETraining"
    page = archive / "2026.2" / "adv" / "Course 2025.1" / "Exercise_ Z" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<h2>Resources</h2><p>Complete workspace | C:\\FMEData\\Workspaces\\exercise-z-complete.fmw</p>",
                    encoding="utf-8")
    out = tmp_path / "out"
    main(["lessons", "--repo", str(repo), "--fmetraining", str(archive), "--out", str(out),
          "--no-network", "--config", str(config(tmp_path))])
    ids = {f["check_id"] for f in json.loads((out / "findings.json").read_text(encoding="utf-8"))["findings"]}
    assert {"FT006", "FT007", "FD005"} <= ids


def test_cli_pr_index_none_skips_fd010(tmp_path: Path, capsys):
    # PRs into a year branch: lessons link main, so FD010 doesn't apply there.
    repo = make_repo(tmp_path)
    git(repo, "rm", "-q", "Data/Parks.shp")
    git(repo, "commit", "-q", "-m", "remove")
    index = tmp_path / "findings.json"
    index.write_text(json.dumps({"generated_at": "2999-01-01T00:00:00+00:00",
                                 "lesson_index": {"Data/Parks.shp": ["L"]},
                                 "current_index": {"Data/Parks.shp": ["L"]}}), encoding="utf-8")
    cfg = str(config(tmp_path))
    assert main(["pr", "--repo", str(repo), "--base", "base", "--index", str(index), "--config", cfg]) == 0
    assert "FD010" in capsys.readouterr().out
    assert main(["pr", "--repo", str(repo), "--base", "base", "--index", "none", "--config", cfg]) == 0
    assert "FD010" not in capsys.readouterr().out


def test_shipped_config_enforces_fd010():
    from fmedata_checks.__main__ import DEFAULT_CONFIG
    from fmedata_checks.model import load_config
    cfg = load_config(DEFAULT_CONFIG)
    assert {"FD006", "FD010"} <= cfg.enforce
    assert "Resources/" in cfg.exempt and "Clone of *" in cfg.ignore_courses


def test_cli_lessons_flags_copies_and_step1(tmp_path: Path):
    repo = make_repo(tmp_path)
    archive = tmp_path / "FMETraining"
    for course in ("Clone of Course 2025.0", "Course 2026.2"):
        page = archive / "2026.2" / "adv" / course / "Exercise_ A" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text("<h2>Resources</h2><p>Starting workspace | C:\\FMEData\\Workspaces\\a.fmw</p>"
                        "<p>Complete workspace | C:\\FMEData\\Workspaces\\a.fmw</p>"
                        "<h3>1) Start Workbench</h3><p>Open the starting workspace.</p>", encoding="utf-8")
    out = tmp_path / "out"
    main(["lessons", "--repo", str(repo), "--fmetraining", str(archive), "--out", str(out),
          "--no-network", "--config", str(config(tmp_path, ignore='ignore_courses = ["Clone of *"]\n'))])
    found = json.loads((out / "findings.json").read_text(encoding="utf-8"))["findings"]
    assert [f["path"] for f in found if f["check_id"] == "FT009"] == ["2026.2/adv/Clone of Course 2025.0"]
    assert [f["path"] for f in found if f["check_id"] == "FT008"] == ["2026.2/adv/Course 2026.2/Exercise_ A/index.html"]


def test_cli_lessons_no_network(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    archive = tmp_path / "FMETraining"
    page = archive / "2026.2" / "adv" / "Course 2026.2" / "Exercise_ A" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<h2>Resources</h2><p>Complete workspace | C:\\FMEData\\Workspaces\\a.fmw</p>"
                    "<h2>Steps</h2><p>C:\\FMEData\\Data\\Gone.shp</p>", encoding="utf-8")
    out = tmp_path / "out"
    code = main(["lessons", "--repo", str(repo), "--fmetraining", str(archive), "--out", str(out),
                 "--no-network", "--config", str(config(tmp_path))])
    assert code == 0
    assert (out / "index.html").exists() and (out / "broken-links.html").exists()
    data = json.loads((out / "findings.json").read_text(encoding="utf-8"))
    assert any(f["check_id"] == "FT001" and "Data/Gone.shp" in f["message"] for f in data["findings"])
    assert "Workspaces/a.fmw" in data["lesson_index"]
