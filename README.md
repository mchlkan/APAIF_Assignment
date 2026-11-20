# Applied Programming & AI Fundamentals — Individual Assignment

Nova SBE, Applied Programming & AI Fundamentals. This repository contains three projects, one folder each:

| # | Project | What it is | Folder |
|---|---|---|---|
| 1 | Momentum Dash replica | A Chrome new-tab dashboard: daily photo, clock, focus, Pomodoro timer, streak, weather, quotes, to-dos | [`momentum-dash/`](momentum-dash/) |
| 2 | Books to Scrape | _In progress_ | _tbd_ |
| 3 | TVmaze API | _In progress_ | _tbd_ |

Each project folder has its own `README.md` (purpose, data, persistence, usage, setup, learning, limitations) and an `AUDIT.md` documenting the pre-publication audit.

## Environment
Python projects use one conda environment for the Python version only; packages are installed with pip from each project's `requirements.txt`:

```bash
conda create -n apaif python=3.12
conda activate apaif
pip install -r <project>/requirements.txt
```

Any Python 3.12 virtual environment works as well. The Momentum Dash extension needs no Python.
