# Releasing

A new epdlib version reaches PyPI through the `release` workflow (`.github/workflows/release.yml`). It runs when a GitHub release is published, and uploads only after txoof approves it.

PyPI uses "trusted publishing": it accepts uploads only from the workflow file `release.yml` in `txoof/epdlib`, running in the GitHub environment `pypi`. No password or token is stored in GitHub. The `pypi` environment requires txoof's approval before the upload job starts.

## Version numbers

The version is written by hand in `pyproject.toml` (`version = ...`), following [Python's version rules](https://packaging.python.org/en/latest/specifications/version-specifiers/):

- `1.0.0a1`, `1.0.0a2`: alpha pre-releases (test versions; the interface may still change).
- `1.0.0rc1`: release candidate (meant to become the final version unless a problem is found).
- `1.0.0`: final release.

`pip install epdlib` skips pre-releases, so users get one only when they ask for it, for example with `pip install "epdlib>=1.0.0a1"`.

A version can be uploaded to PyPI only once. If something is wrong with a published version, publish the next number; do not try to replace it.

## Steps

1. Open a PR that sets the new version in `pyproject.toml` and runs `uv lock` (the lock file holds epdlib's own version too). Merge it.
2. On GitHub, open **Releases**, then **Draft a new release**.
3. Create a new tag named after the version with a `v` in front (for version `1.0.0a1`: tag `v1.0.0a1`) on `main`. The workflow stops with an error if the tag and the version in `pyproject.toml` do not match.
4. For a pre-release, tick **Set as a pre-release**. Write what changed, then **Publish release**.
5. The workflow checks the tag, runs the tests, builds the package and checks it installs. Then it waits in **Actions** for approval: open the run and click **Review deployments**, tick `pypi`, **Approve and deploy**.
6. Check https://pypi.org/project/epdlib/ shows the new version.

## If the upload fails

- "invalid-publisher" or a trusted-publishing error: on PyPI, open the epdlib project, **Settings**, **Publishing**, and check the trusted publisher says owner `txoof`, repository `epdlib`, workflow `release.yml`, environment `pypi`.
- Tag and version do not match: delete the release and its tag on GitHub, fix the version or the tag, and start again from step 2.
