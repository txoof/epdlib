"""Copy Waveshare's model files into epdlib again and rewrite ``vendor/UPSTREAM.txt``.

Usage (from the repository root; needs ``git`` and the internet)::

    uv run python tools/update_waveshare.py            # Waveshare's newest version
    uv run python tools/update_waveshare.py <commit>   # a given version

It downloads only Waveshare's Python folder, replaces every ``epd*.py`` file in
``src/epdlib/drivers/waveshare/vendor/`` with Waveshare's, and prints which files are new,
changed or gone. epdlib's own ``epdconfig.py`` and ``__init__.py`` are not touched. Then
add or remove rows in ``MODELS`` (``src/epdlib/drivers/waveshare/__init__.py``) and run the
tests.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/waveshareteam/e-Paper.git"
FOLDER = "RaspberryPi_JetsonNano/python/lib/waveshare_epd"
VENDOR = Path(__file__).resolve().parents[1] / "src/epdlib/drivers/waveshare/vendor"

HEADER = """\
# Waveshare's files in this folder are copied unchanged from
# https://github.com/waveshareteam/e-Paper, folder {folder},
# commit {commit} ({date}). They are MIT-licensed
# (the licence text is at the top of each file). Never edit them: a test checks them.
# epdconfig.py and __init__.py are epdlib's own and are not listed.
# To copy them again: tools/update_waveshare.py.
#
# Each line: the file's git fingerprint (`git hash-object <file>`, the same as GitHub's
# "sha" for the file at that commit), then the file name.
"""


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def main(commit: str | None = None) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        git("clone", "--quiet", "--filter=blob:none", "--sparse", REPO, "ep", cwd=work)
        work /= "ep"
        git("sparse-checkout", "set", FOLDER, cwd=work)
        if commit:
            git("checkout", "--quiet", commit, cwd=work)
        full, date = git("log", "-1", "--format=%H %cs", cwd=work).split()
        source = work / FOLDER

        old = {p.name: p.read_bytes() for p in VENDOR.glob("epd*.py") if p.name != "epdconfig.py"}
        new = {p.name: p.read_bytes() for p in source.glob("epd*.py") if p.name != "epdconfig.py"}
        for name in old.keys() - new.keys():
            (VENDOR / name).unlink()
        lines = []
        for name in sorted(new):
            (VENDOR / name).write_bytes(new[name])
            lines.append(f"{git('hash-object', str(VENDOR / name), cwd=work)} {name}")

    header = HEADER.format(folder=FOLDER, commit=full, date=date)
    (VENDOR / "UPSTREAM.txt").write_text(header + "\n".join(lines) + "\n")
    print(f"Waveshare commit {full} ({date}): {len(new)} files")
    for label, names in (
        ("new", new.keys() - old.keys()),
        ("changed", {n for n in new.keys() & old.keys() if new[n] != old[n]}),
        ("gone", old.keys() - new.keys()),
    ):
        if names:
            print(f"  {label}: {', '.join(sorted(names))}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
