"""Copy Waveshare's model files into epdlib again and rewrite ``vendor/UPSTREAM.txt``.

Usage (needs ``git`` and the internet)::

    uv run python tools/update_waveshare.py            # Waveshare's newest version
    uv run python tools/update_waveshare.py <commit>   # a given version

It downloads only Waveshare's Python folder, replaces every ``epd*.py`` file in
``src/epdlib/drivers/waveshare/vendor/`` with Waveshare's, and prints which files are new,
changed or gone. epdlib's own ``epdconfig.py`` and ``__init__.py`` are not touched. Then
add or remove rows in ``_TABLE`` (``src/epdlib/drivers/waveshare/__init__.py``) and in the
table in ``docs/waveshare.md``, and run the tests.
"""

from __future__ import annotations

import re
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


class UpdateError(Exception):
    pass


def git(*args: str, cwd: Path) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        raise UpdateError("git is not installed") from None
    if result.returncode:
        raise UpdateError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def model_files(folder: Path) -> dict[str, bytes]:
    """Waveshare's model files in ``folder`` (not links, not the helper file)."""
    return {
        p.name: p.read_bytes()
        for p in folder.glob("epd*.py")
        if p.name != "epdconfig.py" and not p.is_symlink()
    }


def main(commit: str | None = None, *, repo: str = REPO, vendor: Path = VENDOR) -> None:
    if commit is not None and not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise UpdateError(f"not a commit id: {commit!r}")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        git("clone", "--quiet", "--filter=blob:none", "--sparse", repo, "ep", cwd=work)
        work /= "ep"
        git("sparse-checkout", "set", FOLDER, cwd=work)
        if commit:
            git("checkout", "--quiet", commit, cwd=work)
        full, date = git("log", "-1", "--format=%H %cs", cwd=work).split()
        source = work / FOLDER
        new = model_files(source)
        if not new:
            raise UpdateError(f"no model files in {FOLDER} at {full}")
        # Fingerprints first, so a failure leaves the vendor folder as it was.
        lines = [
            f"{git('hash-object', str(source / name), cwd=work)} {name}" for name in sorted(new)
        ]

    old = model_files(vendor)
    for name in old.keys() - new.keys():
        (vendor / name).unlink()
    for name, data in new.items():
        (vendor / name).write_bytes(data)
    header = HEADER.format(folder=FOLDER, commit=full, date=date)
    (vendor / "UPSTREAM.txt").write_text(header + "\n".join(lines) + "\n")
    print(f"Waveshare commit {full} ({date}): {len(new)} files")
    for label, names in (
        ("new", new.keys() - old.keys()),
        ("changed", {n for n in new.keys() & old.keys() if new[n] != old[n]}),
        ("gone", old.keys() - new.keys()),
    ):
        if names:
            print(f"  {label}: {', '.join(sorted(names))}")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit(__doc__)
    try:
        main(*sys.argv[1:])
    except UpdateError as error:
        sys.exit(f"update_waveshare: {error}")
