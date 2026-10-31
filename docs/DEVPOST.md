# Devpost submission: Pitch Integrity Monitor

Copy each block into the matching Devpost field. Every number comes from `results/*.json`.

---

## Project name
Pitch Integrity Monitor

## Tagline (≤ 200 characters)
Can public pitch-tracking data catch a rigged pitch? We tested it on the 18 pitches prosecutors say were sold to bettors, and on every MLB pitcher-month from 2023 to 2025.

## Links
- **Live app:** https://pitch-integrity-monitor-uzwappgttfxqom7nyrx2nyk.streamlit.app/
- **Code:** https://github.com/debi910/pitch-integrity-monitor
- **Demo video (2:00):** *(upload `video/out/pitch-integrity-monitor.mp4` to YouTube or Vimeo, unlisted, and paste the link here)*
- **Deck:** https://github.com/debi910/pitch-integrity-monitor/blob/main/docs/pitch-deck.pdf

---

## Inspiration
On October 5, 2024, in the ninth inning of a 7–0 playoff game, Emmanuel Clase's first pitch to Matt Vierling bounced
in the dirt. Nobody blinked. Two years later federal prosecutors listed it among 18 pitches they say were sold to
bettors, who allegedly won at least $400,000. Both pitchers have pleaded not guilty; the trial is set for November 2026.

Pitch-level prop bets mean a single pitch can now be bought. Every detection so far came from the **betting** side:
someone noticed strange money. We asked the other question. **Can the pitch data itself reveal a fix, and how many
innocent pitchers would that alarm catch?** The false-alarm number decides whether a tool like this is useful or dangerous.

## What it does
Pitch Integrity Monitor judges every pitcher **only against himself** and turns 2.18 million Statcast pitches into a
short, ranked review list for a human integrity analyst.

- **Per-pitch score (v1):** is this pitch's location, pitch choice or speed unusual for this pitcher, given only his
  earlier games?
- **Pattern monitor (v2):** has his monthly rate of the scheme described in the indictment (first pitch of an at-bat,
  taken for a ball, in the dirt) jumped above his own baseline?
- **Integrity-desk case file:** the alert the live monitor would have issued on June 1 2025, with the pitch list, game
  links, next steps and a CSV export.
- **Score any pitcher:** `python -m pim my_savant_export.csv --mode live` prints a ranked list. Names stay hidden
  unless you ask, because an alert is not an accusation.

**Results:**

| | Result |
|---|---|
| Single pitches | Our model, frozen in git before testing, **lost** to a one-line "spiked ball" rule: average precision 0.10 vs 0.20. A rigged ball in the dirt looks like an ordinary miss, and 6 of the 18 were not even balls. |
| Monthly pattern | Clase's May 2025 (9 of 41 first pitches in the dirt, vs his 6.1% baseline) ranks **#22 of 8,339** pitcher-months league-wide, ahead of raw-rate (#31) and raw-count (#783) rules. |
| False alarms | 27 alerts in three seasons: **about 1 a month across all of MLB**. |
| Live | Would have flagged May 2025 on **June 1 2025**, about a month before he was placed on leave. |
| Detection limit | A reliever needs about **6** rigged first pitches in a month for a 50% chance of an alert; a starter about **9**. |
| Honest miss | Caught **1 of 7** named months. The 2023 pitches and Ortiz's two were too sparse to move a monthly rate. |

## How we built it
- **Data:** every regular-season and postseason pitch from 2023 to 2025 from Baseball Savant via `pybaseball`, pulled
  politely in monthly chunks (2,184,102 pitches). The 18 court-named pitches were matched one-to-one to Statcast rows
  by date, inning, batter and pitch number: 18 of 18 matched, none ambiguous.
- **Models:** pure statistics in Python (pandas, NumPy, SciPy). v1 combines three pitcher-relative tail probabilities
  with Fisher's method, using only earlier games (no look-ahead, enforced by a test). v2 is a binomial tail test of
  each pitcher-month against his own baseline, shrunk toward the league rate. **No LLM in the pipeline.**
- **Pre-registration:** both models were frozen in git before evaluation (`5fa3b3e`, `674637e`) and compared with
  simple baselines.
- **Evaluation:** within-pitcher ranking of the 18 named pitches; league-wide false alarms on all 8,339
  pitcher-months; a 27-setting stress test with a beta-binomial null; and a label-free detection-limit study that
  plants synthetic rigged pitches into real months.
- **App:** an animated d3 story page embedded in Streamlit, with a CSV upload.
- **Engineering:** CLI, Makefile, Dockerfile, 11 golden-path tests on GitHub Actions CI, model card, data card and a
  dated changelog.
- **Video:** generated from code. The 3D pitch is rebuilt from its actual Statcast flight data. Narration is neural
  text-to-speech, the music was synthesized from scratch, and the photos are CC-licensed.

## Challenges we ran into
- **Our first model lost.** The pre-registered per-pitch model ranked the named pitches worse than a one-line rule.
  We kept the result, reported it, and moved to monthly patterns instead of hiding it.
- **False alarms are the real cost.** Real pitchers are burstier than a binomial model assumes (27 alerts against 4.4
  expected), so we fitted a beta-binomial null and say plainly that the output is a ranked review list, not an alarm.
- **Labels are allegations,** only 18 of them, with one ambiguous pitch number (Vavra). Every interval is wide, and
  we report the intervals.
- **Ethics:** showing other pitchers' alerts could smear innocent players. Alerts are anonymised everywhere except
  for the two charged pitchers.
- **Data volume:** about 2.2 million rows pulled without hammering Savant; slim zstd parquet files keep the repo usable.

## Accomplishments that we're proud of
- An honest answer to a live question, with the negative result on the front page.
- A monitor that ranks the key month #22 of 8,339 at about one alert a month, and would have fired on June 1 2025.
- A detection limit that tells regulators what public data can and cannot see: roughly 6–9 rigged pitches a month.
- Fully reproducible: the frozen commits, tests and CI, and one command for every number.

## What we learned
- A single rigged pitch is statistically invisible; patterns are not, but only above a threshold.
- Baselines and false-alarm rates matter more than a model's headline score.
- Pitcher-relative ("is this strange for him?") beats league-relative for integrity work.

## What's next for Pitch Integrity Monitor
- Velocity and pitch-type monitors for the other prop markets, which leave no trace in location.
- Joining with betting-volume data for a two-sided alert.
- Minor leagues and other sports with pitch- or shot-level tracking.
- A pilot with one integrity desk, measuring analyst time per true lead.

## Built with
python · pandas · numpy · scipy · scikit-learn · pyarrow · pybaseball · statcast · baseball-savant · streamlit · d3.js · plotly · pillow · ffmpeg · edge-tts · github-actions · docker

## Notes for judges
Allegations, not findings. The labelled pitches come from a Sept 18 2026 court filing (EDNY 25-CR-346), as reported by
Sports Betting Dime and TSN. This project measures how unusual pitches are for a pitcher; unusual is not proof of anything.
