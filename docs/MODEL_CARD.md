# Model card: Pitch Integrity Monitor

**What it is.** Two pitcher-relative anomaly scores computed from public Statcast data. There is no machine-learned
black box and no LLM; every number comes from `pim/` and `eval/`.

| | v1 pitch score (`pim/score.py`) | v2 pattern monitor (`pim/monitor.py`) |
|---|---|---|
| Unit | one pitch | one pitcher-month |
| Question | Is this pitch's location, pitch choice or speed unusual **for this pitcher**, given only his earlier games? | Has his rate of the indictment's template (first pitch, taken for a ball, well below the zone) jumped above **his own** baseline? |
| Output | `pim_score = -log10(Fisher-combined p)` | `score = -log10 P(X >= k \| n, baseline)`; alert at score >= 3 |
| Frozen | git `5fa3b3e`, before any label was scored | git `674637e`, before the league-wide evaluation |

## Intended use
A **ranked review list for a trained integrity analyst**, alongside betting-market signals. The analyst decides
what, if anything, to look at. Typical users: league integrity offices, sportsbook integrity desks, regulators.

## Out of scope / misuse
- **Not a verdict.** A high score means "unusual for this pitcher", never "rigged". Slumps, injuries, new pitches,
  catcher changes and weather all move these rates.
- **Do not publish names from alerts.** The app and `results/` never name pitchers other than the two already
  charged. The CLI hides names unless `--names` is passed.
- Not for betting, player evaluation, contract or disciplinary decisions.

## Performance (all numbers from `results/`)
- **Single pitches (v1):** average precision 0.097 (95% CI 0.02–0.29) on 2,972 Clase pitches with 18 named;
  a one-line spiked-ball rule scores 0.200. **v1 loses**, and we report it.
- **Monthly pattern (v2), league-wide:** 2,175,365 pitches, 8,339 pitcher-months. Clase May 2025 ranks **#22**
  (raw rate #31, raw count #783). 27 alerts in three seasons (**1.08 a month across MLB**). Catches **1 of 7**
  named months; silent on 2023 and on Ortiz.
- **Live mode:** would have flagged May 2025 on June 1 2025.
- **Detection limit** (`results/power.json`): a reliever needs about **6** rigged first pitches in a month for a 50%
  chance of an alert (9 for 90%); a starter about 9 (13 for 90%). Under a beta-binomial null the limits rise.
- **Robustness** (`results/robustness.json`): across 27 settings the May 2025 rank stays #22–#26 at the frozen dirt
  threshold; it moves with the threshold, and we say so.

## Known limitations
- The v2 template came from the indictment's public text, and we had seen the 18 labels when we matched them.
  The league-wide test is dominated by pitchers the template never saw.
- Labels are allegations; some "false alarms" may not be false, and some named pitches may not have been rigged.
- Bets on velocity or pitch type leave no trace in location; v2 cannot see them.
- 18 positives make every interval wide. No 2022 data, so early-2023 baselines lean on the league prior.

## Ethics
Both pitchers have pleaded not guilty and the trial is set for November 2026. We show the named pitches because
they are in a public court filing, and we label them as allegations everywhere they appear.
