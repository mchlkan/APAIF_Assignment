# Audit: Books to Scrape

Pre-publication audit of this folder, as required by the assignment. This file is sanitized: it records what was
checked and what was done, but no secret values or personal details.

## How the audit was run

| | |
|---|---|
| **Tool** | Claude Code (Anthropic). The auditor is a separate, read-only agent (Claude Sonnet 5.5) |
| **Setup** | A fresh agent with **no context** from building the project, started in `books-to-scrape/`, **read-only**: no file changes, no code execution, no commits, never printing `.env` values |
| **Prompt** | The course audit prompt, word for word |
| **Scope** | All tracked files in `books-to-scrape/`, untracked and ignored files, the root `.gitignore` and `README.md`, and the Git history of all local branches, searched for key patterns |

**What the prompt checks:**
- Secrets, credentials and personal data
- Files that should be excluded (local config, caches, dependency folders, generated files)
- `.gitignore` rules
- Dependencies, setup instructions and config examples
- README coverage (purpose, data collection, persistence, user interaction, setup, learning, limitations)

The raw report of each run was kept outside the repository. Below is the sanitized summary, with my decision on each
finding.

## Run 1: 23 Nov 2026 (commit `003c5eb`)

**Result:** no secret is tracked and none was ever committed. The Supabase keys live in `.env`, which is ignored; only
the placeholder template `.env.example` is tracked. No key-like value (Supabase publishable/secret keys, JWTs, a real
project URL) appears in any commit; the only matches are obvious test placeholders in `tests/test_foundation.py`.
Caches, `.env` and Streamlit's `secrets.toml` are ignored, and the sample data is synthetic.

### Findings and decisions

| # | Finding | Type | Decision | What I did |
|---|---|---|---|---|
| 1.1 | README links `AUDIT.md`, which didn't exist yet | Confirmed | **Fixed** | This file |
| 1.2 | README "Learning" section is still a placeholder | Confirmed | **Open (planned)** | I write it myself, in my own words, before submitting |
| 1.3 | The clone URL shows the repository is public under my GitHub handle | Note | **No change** | Intended: the repository is public for the submission |
| 1.4 | README says the secret key is never uploaded to Streamlit Cloud; not verifiable from the files | Possible | **Verified by me** | The deployment's secrets contain only the URL and the publishable key |
| 1.5 | README says the app's key can only read (Row Level Security); only `schema.sql` was read | Possible | **Already verified** | Tested against the live project on 23 Nov: an insert with the publishable key was rejected (`permission denied`), the secret key could write |
| 1.6 | Live demo URL not checked | Possible | **Already verified** | Opened it: all 1,000 books load and the theme is applied |
| 1.7 | Pinned package versions not checked | Possible | **Already verified** | Installed from `requirements.txt` in a clean conda environment; `pip install --dry-run -r requirements.txt` resolves |
| 1.8 | Screenshots not viewed for sensitive content | Could not verify | **Verified by me** | Both show only the page content: no address bar, project URL or keys |
| 1.9 | Add a licence | Recommendation | **No change** | The repository's `LICENSE` is at the root, outside the audited folder |
| 1.10 | `docs/plan.md` includes agent briefing details | Recommendation | **Keep** | It is tracked on purpose: it documents the decisions and the multi-agent build process |
| 1.11 | Remote refs not checked | Could not verify | **Checked** | `origin` has only `main` and `momentum-dash` (project 1) |

## Run 2: 23 Nov 2026

_In progress: filled in after the run._

## Verification

- **Tests:** 40 offline tests pass (`python -m pytest -q`): parser on saved pages, database helpers with a fake client,
  data functions on the sample CSV, configuration errors.
- **Database access rules:** checked against the live Supabase project: the publishable key reads all three tables but
  cannot insert; the secret key can insert and delete.
- **Data:** after the full scrape, 1,000 books in 50 categories, no missing prices, all ratings 1–5; the run log
  shows an incremental re-run skipping already stored books.
- **App:** checked with Streamlit's testing tools in sample and Supabase mode, by hand in the browser, and on the live
  deployment.
- **Ignore rules** checked with `git check-ignore -v`: `.env`, `__pycache__/`, `.pytest_cache/` and `.agents/` are
  ignored; `.env.example` is not.

## Remaining limitations

- **The audit can't prove the project is safe.** The secret search is pattern-based, and the auditor ran no code.
  Runtime behaviour was tested separately (see *Verification*).
- **Free hosting:** the live demo depends on free Supabase and Streamlit tiers, which pause or sleep when idle. The
  README explains the local setup and sample mode as the fallback.
- **GitHub settings** (visibility, push protection) are not checked by the auditor. Push protection was enabled during
  project 1; I check that the repository opens when logged out before submitting.
