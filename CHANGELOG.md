# Changelog

## 2026-10-31
- 2026-10-31: Post-hoc stress test (`eval/robustness.py`): 27 settings plus a beta-binomial null. Frozen #22 holds across volume floor and shrinkage, not across the dirt threshold; calibrated null gives 3 alerts (5.2 expected), Clase #12 but below the alert line. Shown on the page (06 Method) and in README. Tests: 4 → 8 (template rule, spike month, live mode, no other names).
- Project setup: Python 3.13.3 venv, pinned requirements (pybaseball 2.2.7, pandas 3.1.0, pyarrow 26.0.0, numpy 2.5.4, scikit-learn 1.9.1, streamlit 1.66.1, plotly 7.1.0), `.gitignore` (raw data excluded).
- Looked up MLBAM ids: Emmanuel Clase = 661403, Luis L. Ortiz (CLE 2025) = 682847.
- Added `data/labels/court_named_pitches.csv`: 18 Clase pitches and 2 Ortiz game-level rows, as alleged in the Sept 18 2026 EDNY filing (case 25-CR-346), per SBD/TSN reporting. These are allegations, not findings.
- Pulled pitch-level Statcast for Clase and Ortiz 2023-2025 (`scripts/pull_pitchers.py`).
- Matched all 18 Clase labels to exactly one Statcast row each (`scripts/match_labels.py` -> `data/labels/matched.csv`); Vavra label checked at pitch 1 and 2.
- Full-league Statcast pull 2023-2025 (regular season + postseason) in monthly chunks (`scripts/pull_statcast.py` -> `data/raw/statcast_{year}.parquet`, not committed).
- Pre-registered PIM v1 pitch-level surprise score (`pim/score.py`, commit 5fa3b3e) before looking at label ranks.
- Eval 1 (`eval/within_pitcher.py`): v1 LOSES to the simple spiked-ball rule within Clase (AP 0.10 vs 0.20; 2 vs 5 named pitches in top 18). 6 of 18 named pitches were not balls. Result kept and reported.
- Pivot: pattern monitor (`pim/monitor.py`), template taken from the DOJ indictment text (first pitch, ball in the dirt). Frozen before the league-wide eval.
- Streamlit app (`app.py`), lean app requirements, golden-path tests (no look-ahead, labels matched, baseline sanity, monitor volume).
- UI rebuild: animated story page (`web/template.html` -> `docs/index.html` via `scripts/build_web.py`, d3 v7.9.0 inlined), embedded in Streamlit; upload tab kept.
- Full-league pull complete: 2023 = 732,562 pitches (2,471 games), 2024 = 724,767 (2,472), 2025 = 726,773 (2,477), regular season + postseason. Slim zstd copies in `data/slim/statcast_{year}.parquet` (16.8 / 17.3 / 17.4 MB). Clase counts in league data match the per-pitcher pull (1,133 / 1,115 / 754).
- Added CC-licensed Wikimedia Commons photos in `web/img/` with `CREDITS.md`.
- League eval run on 2,175,365 pitches (frozen code, no changes): Clase May 2025 ranks #22 of 8,339 pitcher-months; 27 alerts at p<=0.001 (1.08/month); 1 of 7 named months caught. Results baked into page and README.
