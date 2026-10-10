# Working on epdlib v1

These rules apply to every person and agent working in this repository. The process is the same as in txoof/PaperPi.

## Communication
- Write plainly: no metaphors, figures of speech or jargon. Explain a technical term the first time it is used.
- When guiding the maintainer (txoof) through manual steps, give one short step at a time.

## What epdlib is, and is not
- epdlib draws layouts and sends images to displays. It must work with **any frame-buffered display** (a display that shows a complete image sent to it from memory), not only the ones PaperPi uses.
- **epdlib never imports or depends on PaperPi**, and has no PaperPi ideas in it (plugins, priorities, schedules).
- Drawing must work **without hardware**: importing the layout code must not import GPIO or SPI libraries (the libraries that control the Raspberry Pi's pins and the wired connection to the display). Hardware libraries are only imported by the driver that needs them.
- epdlib is published on PyPI. Changes to its public interface need a note in the changelog once one exists (M3).

## The old code (v0.6)
- v0.6 lives on branch `v0.6` (tag `v0.6-final`) and on PyPI as 0.6.5.2. Read it to understand how something behaved.
- **Do not copy code from v0.6.** Write new code. Good ideas are carried over through the inventory and design notes (milestone M1 in txoof/PaperPi), not by copying.

## Waveshare's files
- The `epd*.py` files in `src/epdlib/drivers/waveshare/vendor/` are Waveshare's, copied unchanged (`UPSTREAM.txt` says from where). **Never edit them**, not even to fix a bug: a test checks them. A model whose file is broken is removed from `MODELS`, added to `NOT_WORKING`, listed as not working in `docs/waveshare.md`, and reported to Waveshare. Copy them again only with `tools/update_waveshare.py`.
- `epdconfig.py` in that folder is epdlib's own replacement for Waveshare's helper file, and is changed like any other code.

## Related repositories
- `txoof/PaperPi`: the main user of epdlib, developed alongside it, at `~/src/PaperPi`. The overall plan and milestones M0–M10 are tracked there; epdlib has the milestones that need epdlib work.

## How work is tracked
- **GitHub Issues are the only to-do list.** Every change starts from an issue in a milestone.
- Exception: Dependabot (GitHub's bot for dependency updates) opens update PRs without an issue. Agents do not claim or change them; txoof reviews and merges them.
- Each issue has an **Area**: the folders it is allowed to change (see the area map below).
- **Do not start** an issue that is already claimed (has the `in-progress` label), or whose Area overlaps a claimed issue. Check with:
  ```bash
  gh issue list -R txoof/epdlib --label in-progress
  ```
- **Claim an issue before starting:**
  ```bash
  gh issue edit <n> -R txoof/epdlib --add-label in-progress
  gh issue comment <n> -R txoof/epdlib --body "claimed by epdlib-<n>-<short-name>"
  ```
  Then move its card on the project board to **In Progress** (see "Project board" below).
- **Release a claim** when the PR is merged (GitHub closes the issue) or when you stop working on it:
  ```bash
  gh issue edit <n> -R txoof/epdlib --remove-label in-progress
  gh issue comment <n> -R txoof/epdlib --body "released: <reason>"
  ```
  If you stop without finishing, move its card back to **Todo**.
- Shared files (`pyproject.toml`, `uv.lock`, `.python-version`, `.github/`) are used by everyone, so take care when changing them:
  - A PR may change `pyproject.toml` and `uv.lock` when its own work needs it (for example a new dependency), so related changes stay together. First check that no other open PR changes them:
    ```bash
    for n in $(gh pr list -R txoof/epdlib --json number --jq '.[].number'); do gh pr diff $n -R txoof/epdlib --name-only | grep -qxE 'pyproject.toml|uv.lock' && echo "PR $n"; done
    ```
    Once your own PR is open, it shows up in this list too.
  - The other shared files are changed only in their own small issue.

## Project board
All PaperPi and epdlib work is shown on one board, where each issue or PR is a card (one entry on the board) in a column: https://github.com/users/txoof/projects/4 (columns Todo, In Progress, In Review, Done).
- PaperPi issues and PRs are added automatically. **epdlib issues and PRs are not** (GitHub's free plan allows automatic adding from one repo only), so agents add them.
- GitHub moves cards to **Done** when an issue is closed or a PR is merged. Agents move cards at the other steps:

| When | Set the issue (and its PR) to |
|---|---|
| You create an issue | Todo |
| You claim it | In Progress |
| You open its PR | In Review |
| You release a claim without finishing | Todo |

Add or move a card (adding a card that is already on the board just returns it, so the same commands do both):
```bash
item=$(gh project item-add 4 --owner txoof --url <issue-or-PR-URL> --format json --jq .id)
gh project item-edit --project-id PVT_kwHOANmg6c4BlqOG --id "$item" \
  --field-id PVTSSF_lAHOANmg6c4BlqOGzhkWLj8 --single-select-option-id <column-id>
```
Column IDs: Todo `f75ad846`, In Progress `47fc9ee4`, In Review `b470c173`, Done `98236657`.

## Area map
| Area | Folders |
|---|---|
| layout | `src/epdlib/` (except the folders below) |
| drivers | `src/epdlib/drivers/` (one sub-area per driver: `drivers/it8951`, `drivers/waveshare`; `tools/update_waveshare.py` belongs to `drivers/waveshare`) |
| docs | `docs/` |
| ci | `.github/`, `pyproject.toml`, `uv.lock`, `.python-version` |

This map grows as the code grows. Update it in the same PR that adds a new area.

## Worktrees and branches
A worktree is a separate folder with its own copy of the repo, so several agents can work at the same time without touching each other's files.
- One worktree per issue, on branch `<n>-<short-name>`:
  ```bash
  git -C ~/src/epdlib fetch origin
  git -C ~/src/epdlib worktree add -b <n>-<short-name> ~/src/wt/epdlib-<n>-<short-name> origin/main
  ```
- Never work directly on `main`.
- After the PR is merged, remove the worktree:
  ```bash
  git -C ~/src/epdlib worktree remove ~/src/wt/epdlib-<n>-<short-name>
  ```

## Pull requests
1. Open a PR that links the issue (`Closes #<n>`, or `Part of #<n>` when the issue needs several PRs). Fill in the PR template, including test results and before/after images for anything visual. The PR title becomes the commit message on `main` (PRs are squash-merged), so write it as one.
2. Review agents check the PR and post their findings as PR comments: code quality, unit tests, security, documentation.
3. Fix the findings, or explain in a reply why not.
4. **Only txoof approves and merges. Agents never merge, never approve, and never push to `main`.** GitHub branch protection enforces this.

### Size of a PR
Every PR costs txoof review time. Too many small PRs and too few huge ones both waste it.
- **Aim for 300–600 changed lines** (code, tests and docs together; images don't count). This is a guideline and an upper bound: a PR may go a little over, but never much larger. Above about 800 lines, split the work.
- **Each PR does one thing that works on its own**, with its tests and docs. `main` is never left half-built.
- **No PR for one small change** (a typo, a one-line rule). Put it in the next related PR.
- **Plan the split before coding.** Show the planned PRs to txoof together with the design questions. One issue may need several PRs; list them in the issue, and each PR says "Part of #n".
- **Review fixes:** small fixes go into the same PR. Fixes that add a new feature go into a follow-up PR, so the first one doesn't keep growing.
- See the size with `git diff --shortstat origin/main...HEAD`.

## Tools and commands
- Supports Python 3.11 and newer; develop with 3.13 (`.python-version`). CI tests 3.11 and 3.13.
- `uv sync`: install. `uv run pytest`: tests. `uv run ruff check .` and `uv run ruff format .`: code style.
- Plain `.py` files only. No Jupyter notebooks in the repo.
- Tests that need a real display are marked `@pytest.mark.hardware`. They are skipped by default; run them on the Pi with `uv run pytest -m hardware`.

## Agent identity (on the development Pi)
Agents run as the GitHub account `txoof-bot`. This is set in `~/src/.claude/settings.json`, which is not part of this repo, so **start Claude Code from `~/src`**, not from inside a repo folder.
