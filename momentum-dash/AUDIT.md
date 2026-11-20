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
| 1.2 | The default branch `main` didn't contain the project yet, so a fresh clone couldn't follow the README setup | Confirmed | **Fixed** | Merged into `main` with a merge commit (`12a438c`) after run 2, then verified with a fresh clone (see *Verification*) |
| 1.3 | Root README promises an `AUDIT.md`, but none existed | Confirmed | **Fixed** | This file |
| 1.4a | `LICENSE` contained a student number | Possible | **Partly fixed** | The current `LICENSE` shows my first name only. The number stays in the Git history (initial commit `09037b0`: the old `LICENSE` and the commit's author name). See *Remaining limitations* |
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

The fixes are in commit `2b5656b` ("Momentum: address audit 1 findings"); 1.3 is this file (`ef33fd6`); 1.2 is the merge `12a438c`.

## Run 2: 20 Nov 2026 (commit `b5d0125`, after the run-1 fixes)

Same setup: a new session without context, the same prompt, plus the instruction to check that the docs match the repository.

**Result:** all run-1 fixes were confirmed. Still no secret anywhere in the history, and no metadata in the images. New or remaining points:

| # | Finding | Type | Decision | What I did |
|---|---|---|---|---|
| 2-1 | `main` still without the project; `AUDIT.md` sections empty | Confirmed | **Fixed** | Merged into `main` (`12a438c`), completed this file |
| 2-2 | The student number is also in the **author name** of the initial commit, not only in `LICENSE` | Confirmed | **Documented** | See *Remaining limitations* |
| 2-3 | README claimed that only the city name leaves the browser, but coordinates, an Unsplash download ping, image requests and the IP address do too | Confirmed | **Fixed** | README lists exactly what is sent to whom |
| 2-4 | Script docstrings still said `python` | Confirmed | **Fixed** | Changed to `python3` |
| 2-5 | No Chrome version stated | Possible | **Fixed** | README says "a current version of Chrome" |
| 2-6 | Screenshot photo credit not covered by the README | Possible | **Fixed** | Caption under the screenshot |
| 2-7 | `.env.*` variants not ignored (relevant for the next projects) | Possible | **Fixed** | `.env.*` ignored, `.env.example` allowed |
| 2-8 | Project tree in the README left out `README.md` and `AUDIT.md` | Possible | **Fixed** | Added |
| 2-9 | Open-Meteo credit (CC BY 4.0) was only a tooltip | Possible | **Fixed** | Visible "Weather data by Open-Meteo.com" in the page |
| 2-10 | Repository is in iCloud Drive (`.icloud` placeholder files) | Possible | **Fixed** | `*.icloud` ignored |

Fixes in commit `2c6e81d`.

## Run 3: 20 Nov 2026 (default branch `main` @ `12a438c`)

Final check on the default branch, the way the repository will be published.

**Result:** no secret is tracked. The auditor also searched the full history for the exact value of the local key and found 0 matches. Every file the code references exists on `origin/main`, the README facts match the code, and all run-1 fixes are present. Remaining points:

| # | Finding | Type | Decision | What I did |
|---|---|---|---|---|
| 3-1 | `AUDIT.md` still described the merge as planned and had placeholders | Confirmed | **Fixed** | This version |
| 3-2 | Student number in the history; 1.4a was marked "Fixed" | Confirmed | **Documented accurately** | 1.4a changed to "Partly fixed"; see *Remaining limitations* |
| 3-3 | README said "click the photo credit to open the photo", but the credit linked only to the photographer and Unsplash | Confirmed | **Fixed** | "Photo" in the credit now links to the photo page |
| 3-4 | README said I made all commits myself, but some commits carry a `Co-Authored-By: Claude` line | Possible | **Fixed** | README now explains that in the final rounds I let Claude Code commit on my behalf |
| 3-5 | `python3 -m http.server` would serve the folder, including `config.js`, to the local network | Possible | **Fixed** | README uses `--bind 127.0.0.1` |
| 3-6 | `config.js` rule depends on the folder name in the root `.gitignore` | Possible | **Fixed** | Added `momentum-dash/.gitignore` with `config.js` |
| 3-7 | Root README: "needs no Python" ignores the optional scripts | Confirmed | **Fixed** | Mentions Python 3.9+ for `tools/` |
| 3-8 | Screenshots were taken before the Open-Meteo credit line was added | Confirmed (minor) | **Won't fix** | Only the credit line is missing; everything else is current |
| 3-9 | First name in the README and screenshots | Possible | **Won't fix** | As in run 1 (2.6): already public on the repository |
| 3-10 | Merged branch `momentum-dash` still exists on GitHub | Possible | **Won't fix** | Its commits are part of `main` anyway; the branch shows the workflow |
| 3-11 | Enable GitHub secret scanning / push protection | Recommendation | **Michael** | A GitHub setting, outside the code |

Fixes in the commit that adds this version of `AUDIT.md`.

## Verification

- **Fresh clone (20 Nov 2026):**
  - Cloned `https://github.com/mchlkan/APAIF_Assignment.git` into an empty temporary folder. The default branch was `main`, with `momentum-dash/` complete and no `config.js`.
  - `manifest.json` is valid JSON. The bundled fallback photos and screenshots are present.
  - Served the cloned folder on localhost and opened it. The first-run name prompt appeared; with **no key**, a bundled fallback photo appeared with its credit; the weather loaded; all four boxes were placed.
- **Ignore rules** checked with `git check-ignore -v`: `config.js` (by both the root and the project `.gitignore`), `*.pem`, `*.crx`, `.claude/`, `.env.local` and `*.icloud` are ignored; `.env.example` is not.
- **Manual tests in Chrome:** all features were tested in the real extension during development (see README).

## Remaining limitations

- **Personal data in earlier commits:**
  - The initial commit (`09037b0`) contains my student number, in the old `LICENSE` and in the commit's author name.
  - The commits before `2b5656b` contain my personal email address.
  - The current files are clean, and new commits use the GitHub noreply address.
  - Removing these values from the history would need a rewrite (`git filter-repo`) and a force-push. For now this is left as is and documented here.
- **The audit can't prove the project is safe.** The secret search is pattern-based, and the auditor ran no code. Runtime behaviour was tested separately and manually (see README, *Limitations*).
- **GitHub settings were not checked by the auditor,** such as repository visibility and secret scanning. I check that the repository opens when logged out before submitting.
