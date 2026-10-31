# Pitch Integrity Monitor

**Can public pitch-tracking data catch a rigged pitch?** We tested it on the 18 pitches federal prosecutors say
Emmanuel Clase sold to bettors, and on every MLB pitcher-month from 2023 to 2025.

> **Allegations, not findings.** The labelled pitches come from a Sept 18 2026 court filing (EDNY 25-CR-346).
> Emmanuel Clase and Luis L. Ortiz have pleaded not guilty and the trial is set for November 2026. This project
> measures how *unusual* pitches are for a pitcher. Unusual is not proof of anything.

Live app: _link added after deploy_ · AQX Sports Analytics Data Bowl 4.0

## The answer in two results

<!-- RESULTS_TABLE -->

1. **One pitch is not enough.** Our pre-registered pitch-level model (frozen in git at `5fa3b3e` before we looked
   at label ranks) ranked the 18 named pitches *worse* than a one-line "spiked ball" rule. A third of the named
   pitches were not balls at all, so no location rule could see them.
2. **Patterns show up.** A monitor that watches each pitcher's *own* monthly rate of the pattern described in the
   indictment (first pitch of an at-bat, taken for a ball, in the dirt) is tested league-wide below.

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
app.py (Streamlit)       case view · result 1 · result 2 · upload any pitcher · method & limits
```

**Code computes, nothing guesses.** There is no LLM in the pipeline. Every number on screen comes from the scripts above.

## Setup

```bash
pip install -r requirements.txt          # app + evals
streamlit run app.py                      # the app (works with the committed slim data)
pip install -r requirements-pipeline.txt && python scripts/pull_statcast.py && python scripts/make_slim.py 2023 2024 2025
python eval/within_pitcher.py && python eval/league_monitor.py && pytest -q
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

## Repo map

`pim/` scoring and monitor · `eval/` evaluation scripts · `results/` outputs · `data/labels/` labels ·
`scripts/` data pull · `tests/` golden-path tests · `CHANGELOG.md` dated build log
