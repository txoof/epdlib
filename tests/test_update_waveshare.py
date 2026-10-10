"""tools/update_waveshare.py, run against a small local git repository instead of Waveshare's."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "update_waveshare", ROOT / "tools/update_waveshare.py"
)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def git(*args, cwd):
    command = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args]
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def upstream(tmp_path):
    repo = tmp_path / "upstream"
    folder = repo / update.FOLDER
    folder.mkdir(parents=True)
    (folder / "epdA.py").write_text("A = 2\n")
    (folder / "epdB.py").write_text("B = 1\n")
    (folder / "epdconfig.py").write_text("waveshare's helper\n")
    git("init", "-q", cwd=repo)
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "files", cwd=repo)
    return repo


@pytest.fixture
def vendor(tmp_path):
    folder = tmp_path / "vendor"
    folder.mkdir()
    (folder / "epdA.py").write_text("A = 1\n")
    (folder / "epdC.py").write_text("C = 1\n")
    (folder / "epdconfig.py").write_text("ours\n")
    return folder


def test_copies_new_and_changed_files_and_removes_gone_ones(upstream, vendor, capsys):
    update.main(repo=str(upstream), vendor=vendor)
    assert sorted(p.name for p in vendor.iterdir()) == [
        "UPSTREAM.txt",
        "epdA.py",
        "epdB.py",
        "epdconfig.py",
    ]
    assert (vendor / "epdA.py").read_text() == "A = 2\n"
    assert (vendor / "epdconfig.py").read_text() == "ours\n"  # epdlib's own, untouched
    out = capsys.readouterr().out
    assert "new: epdB.py" in out and "changed: epdA.py" in out and "gone: epdC.py" in out

    commit = git("rev-parse", "HEAD", cwd=upstream).strip()
    text = (vendor / "UPSTREAM.txt").read_text()
    assert commit in text
    listed = [line.split() for line in text.splitlines() if line and not line.startswith("#")]
    expected = [
        git("hash-object", str(vendor / n), cwd=upstream).strip() for n in ("epdA.py", "epdB.py")
    ]
    assert listed == [[expected[0], "epdA.py"], [expected[1], "epdB.py"]]


@pytest.mark.parametrize("commit", ["--orphan=x", "main", "abc"])
def test_refuses_anything_but_a_commit_id(commit, vendor):
    with pytest.raises(update.UpdateError, match="not a commit id"):
        update.main(commit, vendor=vendor)


def test_a_failing_git_leaves_the_vendor_folder_alone(tmp_path, vendor):
    before = {p.name: p.read_text() for p in vendor.iterdir()}
    with pytest.raises(update.UpdateError, match="git clone failed"):
        update.main(repo=str(tmp_path / "nothing-here"), vendor=vendor)
    assert {p.name: p.read_text() for p in vendor.iterdir()} == before
