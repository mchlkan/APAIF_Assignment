# Audit: Verdant Tab (Momentum Dash replica)

Pre-publication audit of this folder, as required by the assignment. This file is sanitized: it records what was checked and what was done, but no secret values or personal details.

## How the audit was run

| | |
|---|---|
| **Tool** | Claude Code (Anthropic, model Claude Opus 5.5) |
| **Setup** | A fresh assistant session with **no context** from building the project, started in `momentum-dash/`, **read-only**: no file changes, no code execution, no commits |
| **Prompt** | The course audit prompt, word for word |
| **Scope** | All tracked files in `momentum-dash/`, untracked and ignored files, the repository's root `.gitignore`, `README.md` and `LICENSE`, and the full Git history of all branches, searched for secrets |

**What the prompt checks:**
- Secrets, credentials and personal data
- Files that should be excluded (local config, caches, dependency folders, generated files)
- `.gitignore` rules
- Dependencies, setup instructions and config examples
- README coverage (purpose, data collection, persistence, user interaction, setup, learning, limitations)

The raw report of each run was kept outside the repository. Below is the sanitized summary, with my decision on each finding.

## Run 1: 20 Nov 2026 (commit `e1da38a`)

**Result:** no secret is tracked and none was ever committed. The Unsplash key lives in `config.js`, which is ignored; only the placeholder template `config.example.js` is tracked. The run found 3 confirmed issues, 2 possible concerns and 8 recommendations.

### Findings and decisions

| # | Finding | Type | Decision | What I did |
|---|---|---|---|---|
| 1.1 | README links a screenshot that doesn't exist (`docs/` was empty) | Confirmed | **Fixed** | Added `docs/screenshot.jpg` and `docs/screenshot-edit-mode.jpg`: page only, demo to-dos, no real location; compressed to under 200 KB each |
| 1.2 | The default branch `main` didn't contain the project yet, so a fresh clone couldn't follow the README setup | Confirmed | **To fix (planned)** | Merge the project into `main` via pull request after the re-check, then verify with a fresh clone (see *Verification*) |
| 1.3 | Root README promises an `AUDIT.md`, but none existed | Confirmed | **Fixed** | This file |
| 1.4a | `LICENSE` contained a student number | Possible | **Fixed** | The copyright line now shows my first name only |
| 1.4b | Commit metadata contains my personal email address | Possible | **Partly fixed** | I switched to GitHub's private noreply address, so all commits from the audit fixes onward use it. I did **not** rewrite the already-published history: that needs a force-push, which is risky and makes the Git history harder to follow. See *Remaining limitations* |
| 1.5 | A real API key exists locally in `config.js` | Possible | **No change needed** | It is ignored and was never committed. I confirmed in the Unsplash dashboard that it is the *Access Key*, which is designed for client-side use, not the Secret Key |
| 2.1 | `.gitignore` didn't cover `*.pem` / `*.crx` (Chrome's "Pack extension" output; the `.pem` is a private signing key), editor folders, `node_modules/` or archives | Recommendation | **Fixed** | Added these rules |
| 2.2 | `lib/` (from the Python `.gitignore` template) would silently hide a future JavaScript `lib/` folder | Recommendation | **Fixed** | Narrowed to `/lib/` |
| 2.3 | Stray empty `.Rhistory` file in the folder (it was ignored) | Recommendation | **Fixed** | Deleted |
| 2.4 | MIT licence vs the bundled Unsplash photos | Recommendation | **Fixed** | README states that the photos are under the Unsplash License, not MIT |
| 2.5 | README used `python …`, but macOS often only has `python3`; the scripts need Python 3.9+ | Recommendation | **Fixed** | README now says `python3` and "Python 3.9+" |
| 2.6 | First name in the README and code comments; default weather city "Lisbon" | Recommendation | **Mostly won't fix** | Lisbon is the university's city, not private. My name is public on the repository anyway. I removed it from two code comments |
| 2.7 | A few quotes are by modern authors | Recommendation | **Won't fix** | Short, attributed quotations with low risk; noted in the README |
| 2.8 | Only two specific files in the local `.claude/` tool folder were ignored | Recommendation | **Fixed** | All of `.claude/` is ignored |

All fixes are in commit `2b5656b` ("Momentum: address audit 1 findings"), except 1.2 (the pull request to `main`) and 1.3 (this file).

## Run 2: re-check after the fixes

_Results are added after the second run._

## Verification

_The fresh-clone test is added after the merge into `main`._

## Remaining limitations

- **The email address in earlier commits stays visible.** Commits made before the audit still contain my personal email address in their metadata. Removing it would need a history rewrite and force-push. I accepted this consciously; new commits use the noreply address.
- **The audit can't prove the project is safe.** The secret search is pattern-based, and the auditor ran no code. Runtime behaviour was tested separately and manually (see README, *Limitations*).
- **GitHub settings were not checked by the auditor,** such as repository visibility and secret scanning. I check that the repository opens when logged out before submitting.
