# Pitch Integrity Monitor

[![tests](https://github.com/debi910/pitch-integrity-monitor/actions/workflows/tests.yml/badge.svg)](https://github.com/debi910/pitch-integrity-monitor/actions/workflows/tests.yml)

**[Live app](https://pitch-integrity-monitor-uzwappgttfxqom7nyrx2nyk.streamlit.app/) · [9-slide deck (PDF)](docs/pitch-deck.pdf) · [Model card](docs/MODEL_CARD.md) · [Data card](docs/DATA_CARD.md) · [Changelog](CHANGELOG.md)**

**Can public pitch-tracking data catch a rigged pitch?** We tested it on the 18 pitches federal prosecutors say
Emmanuel Clase sold to bettors, and on every MLB pitcher-month from 2023 to 2025.

> **Allegations, not findings.** The labelled pitches come from a Sept 18 2026 court filing (EDNY 25-CR-346).
> Emmanuel Clase and Luis L. Ortiz have pleaded not guilty and the trial is set for November 2026. This project
> measures how *unusual* pitches are for a pitcher. Unusual is not proof of anything.

Live app: https://pitch-integrity-monitor-uzwappgttfxqom7nyrx2nyk.streamlit.app/ · AQX Sports Analytics Data Bowl 4.0

## The answer in two results

**Result 1 — single pitches** (all 2,972 Clase pitches 2023–25, 18 named; `results/within_clase.json`)

| Method | Avg precision (95% CI) | Named in top 18 | Named in top 100 | Median rank |
|---|---|---|---|---|
| PIM (ours) | 0.097 (0.02–0.29) | 2 | 4 | 350 |
| B1 spiked-ball rule | 0.200 (0.06–0.41) | 5 | 10 | 93 |
| B2 distance outside zone | 0.184 (0.04–0.40) | 4 | 7 | 173 |
| B3 random | 0.005 (0.00–0.01) | 0 | 0 | 1,490 |

**Result 2 — monthly pattern, league-wide** (2,175,365 pitches, 1,068 pitchers, 8,339 pitcher-months; `results/league_monitor.json`)

| Method | Avg precision | Rank of Clase May 2025 | Named months in top 1% |
|---|---|---|---|
| **Ours: jump above his own baseline** | 0.0076 | **#22** | 1 / 7 |
| Ours, live (earlier months only) | 0.0072 | #24 | 1 / 7 |
| Simple: raw monthly rate | 0.0057 | #31 | 1 / 7 |
| Simple: raw monthly count | 0.0012 | #783 | 0 / 7 |

At p ≤ 0.001 the monitor raises **27 alerts in 3 seasons (1.08 a month across MLB)**; a pure binomial
null would give 4.4, so real pitchers are burstier than the model assumes. It catches **1 of 7** named months
(Clase, May 2025: 9 of 41 first pitches in the dirt vs his 6.1% baseline). The live version would have flagged it on
June 1 2025, about a month before he was placed on leave. It is silent on 2023 and on Ortiz.

**Stress test** (post-hoc, after the frozen result; `eval/robustness.py` → `results/robustness.json`). Clase May 2025
across 27 settings (dirt threshold × volume floor × shrinkage):

| Dirt threshold | Rank range | Beats raw rate? |
|---|---|---|
| 30% below zone (frozen) | **#22 – #26** | 7 of 9 settings |
| 20% below zone | #76 – #97 | 9 of 9 |
| 40% below zone | #117 – #168 | 0 of 9 |

Volume floor and shrinkage barely matter; the dirt threshold does, and we say so. Alerts stay at 24–35 in every
setting. Replacing the binomial with a **beta-binomial null** (fitted to the league's normal month-to-month wobble,
ρ = 0.0059) cuts alerts from 27 to **3** (5.2 expected by chance) and moves Clase May 2025 up to **#12**, but its score
(2.55) then falls just short of p ≤ 0.001. Read the monitor as a ranked review list, not an alarm.

**Detection limit** (post-hoc, label-free; `eval/power.py` → `results/power.json`). We swapped *r* rigged first pitches
(taken ball in the dirt) into every real pitcher-month and asked whether the frozen monitor would alert:

| Rigged first pitches in a month | Reliever caught (n 20–59) | Starter caught (n 60+) |
|---|---|---|
| 1 | 0.7% | 0.9% |
| 2 | 2.4% | 2.0% |
| 4 | 14% | 7% |
| **6** | **52%** | 19% |
| 9 | 95% | **53%** |

A fixer who sells one or two pitches a month is invisible in public pitch data; the named months held 1 to 6 named
pitches each, which is why the monitor caught only one. Past about six a month the pattern gives itself away. Under the
stricter beta-binomial alarm a reliever needs 7 (50%) to 10 (90%). Performance data alone cannot stop small fixes, but it
caps how greedy a fixer can be and tells an integrity desk when to pull betting records.

**Coach mode, tested and not shipped** (pre-registered at `4eb6f84` before any injured-list data was joined;
`pim/drift.py`, `eval/injury.py` → `results/injury.json`). Can the same pitcher-vs-himself engine warn a coach before an
injury? We scored 7,070 pitcher-months (live mode) on command drift plus fastball-velocity drop, labelled by an IL placement
within 30 days (5,337 StatsAPI IL transactions; 1,088 positive months, 15%).

| Method | ROC AUC (95% CI, pitcher-clustered) | Lift in top 5% |
|---|---|---|
| Drift (command + velocity), ours | 0.553 (0.532–0.572) | 1.49× |
| **Velocity drop alone** (simple) | **0.558** (0.537–0.580) | 1.52× |
| Command drift alone | 0.519 (0.499–0.540) | 1.01× |
| Random | 0.502 | 0.99× |

Ours minus velocity: −0.005 AUC (−0.020 to +0.009). It ties the simple rule, so we do not ship it as a feature: for coaches,
fastball velocity already carries what public pitch data can say about injury risk. Post-hoc, restricting to arm injuries
(elbow, shoulder, forearm, etc.) gives 0.573 vs 0.575, the same picture.

1. **One pitch is not enough.** Our pre-registered pitch-level model (frozen in git at `5fa3b3e` before we looked
   at label ranks) ranked the 18 named pitches *worse* than a one-line "spiked ball" rule. A third of the named
   pitches were not balls at all, so no location rule could see them.
2. **Patterns show up, sometimes.** A monitor that watches each pitcher's *own* monthly rate of the pattern described in
   the indictment (first pitch of an at-bat, taken for a ball, in the dirt) ranks Clase's May 2025 #22 of 8,339
   pitcher-months, ahead of the raw-rate and raw-count rules, at about one alert a month league-wide. It misses the
   other six named months, where the rigged pitches were too sparse to move a monthly rate.

## Why it matters

Pitch-level prop bets let a single pitch be sold. So far every detection came from the betting side: an integrity
firm noticed unusual money on one pitch. Nobody had measured whether the performance data itself gives a fixer away,
or how many innocent pitchers a performance-based alarm would also flag. That false-alarm number decides whether a
tool like this is useful or dangerous.

## How it works

```
Baseball Savant (Statcast, every pitch 2023-25)
        │  pybaseball, monthly chunks, polite rate
        ▼
data/slim/*.parquet ──► pim/score.py    v1: per-pitch surprise vs the pitcher's own EARLIER games
                    │                        (location, pitch choice, velocity → Fisher-combined p)
                    └─► pim/monitor.py  v2: monthly rate of the indictment's template vs his own baseline
                                             (binomial tail test, shrunk to the league rate)
court filing ──► data/labels/ (18 Clase pitches matched 1:1 to Statcast rows; 2 Ortiz games)
        │
        ▼
eval/within_pitcher.py   Eval 1: rank of named pitches among all Clase pitches vs baselines
eval/league_monitor.py   Eval 2: rank of named months among all pitcher-months; alert volume
        │
        ▼
scripts/build_web.py ──► docs/index.html (story page, d3, photos inlined) ──► app.py (Streamlit host)
```

**Code computes, nothing guesses.** There is no LLM in the pipeline. Every number on screen comes from the scripts above.

## Use it

- **Integrity desk view:** the page's section 03 shows the case file the live monitor would have issued on June 1 2025 (pitch list, Savant game links, next steps, CSV export).
- **Score any pitcher:** `python -m pim my_savant_export.csv --mode live --top 20 --out alerts.csv` (names hidden unless `--names`).
- **Reproduce everything:** `make test`, `make evals`, `make app`, or `docker build -t pim . && docker run -p 8501:8501 pim`.

## Setup

```bash
pip install -r requirements.txt          # app + evals
streamlit run app.py                      # the app (works with the committed slim data)
pip install -r requirements-pipeline.txt && python scripts/pull_statcast.py && python scripts/make_slim.py 2023 2024 2025
python eval/within_pitcher.py && python eval/league_monitor.py && python eval/robustness.py && python eval/power.py && pytest -q
```

## Data

| Source | What | Licence / terms | Range | Real or proxy |
|---|---|---|---|---|
| [Baseball Savant](https://baseballsavant.mlb.com/statcast_search) via [pybaseball](https://github.com/jldbc/pybaseball) | Every pitch: location, speed, type, count, result | MLB Advanced Media terms; non-commercial research use. Raw pulls are not committed, only slim columns | 2023-03 to 2025-11 | **Real**, exact use case |
| [DOJ press release](https://www.justice.gov/usao-edny/pr/two-current-major-league-baseball-players-charged-sports-betting-and-money-laundering) | Charges, scheme description, Ortiz game dates | Public record | Nov 9 2025 | **Real** |
| Sept 18 2026 filing as reported by [Sports Betting Dime](https://www.sportsbettingdime.com/news/industry/new-court-documents-show-18-alleged-emmanuel-clase-rigged-pitches/) and [TSN](https://www.tsn.ca/mlb/article/prosecutors-identify-18-alleged-rigged-pitches-for-clase-trial-n1-49980924/) | 18 named pitches (date, inning, batter, pitch number) | Public record (allegations) | May 2023 – May 2025 | **Real** labels, allegations |

Nothing is simulated or mocked.

## Where it stops

- It never outputs "rigged". It ranks what is unusual **for this pitcher** and hands it to a human investigator.
- Labels are allegations, and the earlier list covered at least 48 games, so some "false alarms" may not be false.
- Bets on velocity or pitch type leave no trace in location. The monitor cannot see them.
- Other pitchers who trigger alerts are never named in the app or results. Most will be slumps, injuries or new pitches.
- With 18 positives, every confidence interval is wide. We report them.

## Honest limitations

- v2's template was written from the indictment's public description, and we had seen the 18 labels when we
  matched them. The league-wide test is the honest check, since it is dominated by pitchers the template never saw.
- No 2022 data, so early-2023 baselines lean on the league prior.
- Ortiz's two pitches are known only at game level.
- The Vavra label is reported as pitch 2 of the at-bat; pitch 1 (a 0-0 slider just below the zone) fits the pattern better. We kept the label as reported.
- Photos: CC-licensed from Wikimedia Commons, credited in `web/img/CREDITS.md` and on the page.

## Repo map

`pim/` scoring and monitor · `eval/` evaluation scripts · `results/` outputs · `data/labels/` labels ·
`scripts/` data pull · `tests/` golden-path tests · `CHANGELOG.md` dated build log
