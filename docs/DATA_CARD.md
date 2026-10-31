# Data card

| Dataset | Source | Rows | Range | Licence / terms | In git? |
|---|---|---|---|---|---|
| League pitches | Baseball Savant Statcast via pybaseball (`scripts/pull_statcast.py`), regular season + postseason | 2023: 732,562 · 2024: 724,767 · 2025: 726,773 | 2023-03-30 to 2025-11-01 | MLB Advanced Media terms; non-commercial research | Slim columns only (`data/slim/`, zstd parquet) |
| Named-pitcher pitches | Statcast via `statcast_pitcher` for Clase (MLBAM 661403) and Luis L. Ortiz (682847) | 8,977 (incl. spring training) | 2023–2025 | as above | `data/slim/pitchers_clase_ortiz.parquet` |
| Court-named pitches | Sept 18 2026 EDNY filing (25-CR-346), as reported by Sports Betting Dime and TSN | 18 pitches + 2 game-level rows | May 2023 – June 2025 | Public record; **allegations** | `data/labels/` |

**Collection.** Day-by-day Savant queries, one month at a time, at most 3 concurrent requests, with retries; about
50 minutes for three seasons. Spring training and exhibitions are dropped (`game_type` in R, F, D, L, W).

**Label matching.** Each label (date, inning, batter, pitch number in the plate appearance) was matched to exactly
one Statcast row: 18 of 18 matched, 0 ambiguous (`scripts/match_labels.py`, `data/labels/matched.csv`). The Vavra
label is reported as pitch 2; pitch 1 of that at-bat is also recorded for comparison. Ortiz's two games are known
only at game level.

**Checks.** Clase's pitch counts in the league files equal the per-pitcher pull (1,133 / 1,115 / 754).
`tests/` asserts 18/18 matches, no look-ahead in scoring, and that the CLI reproduces the frozen monitor.

**Known gaps.** No 2022 data. Statcast `plate_z` below the ground (e.g. -0.68 ft) is the extrapolated crossing
height of a ball that bounced. A handful of pitches lack tracking and are dropped.

**Privacy.** Pitch data concerns professional athletes' public on-field performance. Alerts for anyone other than
the two charged pitchers are anonymised in `results/league_cells_anon.csv`.
