## Inspiration

On **October 5, 2024**, in the ninth inning of a 7–0 playoff game in Cleveland, Emmanuel Clase's first pitch to Matt Vierling bounced in the dirt: a 93.1 mph slider that crossed at $z = -0.68$ ft, well under the bottom of the zone ($1.67$ ft). Nobody blinked.

Two years later federal prosecutors listed it among **18 pitches** they say were sold to bettors, who allegedly won at least \$400,000. *Both pitchers have pleaded not guilty; the trial is set for November 2026. These are allegations, not findings.*

Pitch-level prop bets mean a single pitch can now be bought. So far every detection came from the **betting** side: someone noticed strange money. We asked the other question:

> **Can the pitch-tracking data itself reveal a fix, and how many innocent pitchers would that alarm catch?**

## What it does

Pitch Integrity Monitor judges every pitcher **only against himself**, and turns $2{,}175{,}365$ Statcast pitches into a short, ranked review list for a human integrity analyst. It never outputs "rigged".

**v1: per-pitch surprise.** For pitch $i$ we compute three tail probabilities against the same pitcher's *earlier* games only: location $p_{\text{loc}}$, pitch choice in this count $p_{\text{choice}}$, and velocity $p_{\text{velo}}$. We combine them with Fisher's method:

$$X^2_i = -2\left(\ln p_{\text{loc}} + \ln p_{\text{choice}} + \ln p_{\text{velo}}\right) \sim \chi^2_6, \qquad \text{score}_i = -\log_{10} P\!\left(\chi^2_6 \ge X^2_i\right).$$

**v2: pattern monitor.** The indictment describes rigged balls thrown "in the dirt", often on the first pitch of an at-bat. With the zone-relative height

$$z^{\text{rel}} = \frac{z - z_{\text{bot}}}{z_{\text{top}} - z_{\text{bot}}},$$

a *template event* is a first pitch, taken for a ball, with $z^{\text{rel}} < -0.3$. For pitcher $j$ in month $m$ we observe $k$ events out of $n$ first pitches and compare them with his own baseline, shrunk toward the league rate $\pi_{\text{lg}} = 0.0587$ with $\lambda = 150$ pseudo-pitches:

$$\hat{\pi}_{j,m} = \frac{K_{j,\neg m} + \lambda\,\pi_{\text{lg}}}{N_{j,\neg m} + \lambda}, \qquad s_{j,m} = -\log_{10} P\!\left(X \ge k\right),\; X \sim \operatorname{Bin}\!\left(n, \hat{\pi}_{j,m}\right).$$

$K_{j,\neg m}$ and $N_{j,\neg m}$ count his *other* months (audit mode) or only his *earlier* months (live mode). An alert fires when $s_{j,m} \ge 3$, i.e. $p \le 0.001$.

For Clase in May 2025: $k = 9$, $n = 41$, and $\hat{\pi} = 0.061$, so $k/n = 0.22 \approx 3.6\,\hat{\pi}$ and $s = 3.15$.

## How we built it

- **Data.** Every regular-season and postseason pitch from 2023 to 2025 from Baseball Savant via `pybaseball`, pulled politely in monthly chunks ($2{,}184{,}102$ pitches). We matched the 18 court-named pitches one-to-one to Statcast rows by date, inning, batter and pitch number: **18 of 18 matched, 0 ambiguous**.
- **Pre-registration.** Both models were frozen in git *before* evaluation (`5fa3b3e`, `674637e`) and compared with simple baselines.
- **Evaluation.**
  - Within-pitcher ranking of the 18 named pitches among all $2{,}972$ Clase pitches, by average precision $\text{AP} = \sum_k (R_k - R_{k-1})\,P_k$.
  - League-wide false alarms on all $8{,}339$ pitcher-months.
  - A 27-setting stress test, plus a beta-binomial null with over-dispersion $\rho = 0.0059$.
  - A label-free **detection limit**: plant $r$ rigged first pitches into every real pitcher-month and estimate $P(\text{alert} \mid r)$.
  - A **threshold-free check**: average each pitcher-month's score over 11 dirt cut-offs, from 10% to 60% of a zone height below the zone, so that no hand-picked line drives the result.
  - **Coach mode** (pre-registered at `4eb6f84` before any injury data was joined). Can the same engine warn a coach before an injury? We scored 7,070 pitcher-months on command drift plus fastball-velocity drop. A month counts as positive if an injured-list placement follows within 30 days; we pulled 5,337 IL transactions from the MLB StatsAPI, giving 1,088 positive months.
- **Stack.** Python (pandas, NumPy, SciPy), a d3 story page inside Streamlit, a CLI (`python -m pim`), 12 tests on GitHub Actions CI, Docker, and model and data cards. **No LLM in the pipeline:** code computes, nothing guesses.
- **Video.** Generated from code. The 3D pitch is rebuilt from its Statcast flight data, $\mathbf{x}(t) = \mathbf{x}_0 + \mathbf{v}_0 t + \tfrac{1}{2}\mathbf{a}t^2$; the music is synthesized and the photos are CC-licensed.

## Results

| | Result |
|---|---|
| **Single pitches** | Our frozen model **lost** to a one-line spiked-ball rule: $\text{AP} = 0.10$ (95% CI $0.02$–$0.29$) vs $0.20$. Random is $0.005$. Six of the 18 were not even balls. |
| **Monthly pattern** | Clase, May 2025 ranks **#22 of 8,339**, ahead of the raw rate (#31) and raw count (#783). |
| **False alarms** | 27 alerts in three seasons, $\approx 1.08$ a month across all of MLB. |
| **Live** | Would have flagged May 2025 on **June 1, 2025**, about a month before he was placed on leave. |
| **Detection limit** | $P(\text{alert}) \ge 0.5$ needs $r \approx 6$ rigged first pitches a month for a reliever and $r \approx 9$ for a starter. |
| **No hand-picked cut-off** | Averaged over 11 cut-offs, May 2025 ranks **#38 of 8,339** (top 0.5%), and it stays in the top 2.3% at every single cut-off. |
| **Honest miss** | Caught **1 of 7** named months; sparse fixes do not move a monthly rate. |
| **Coach mode** | Our drift score ties a simple velocity-drop rule: ROC AUC $0.553$ ($0.532$–$0.572$) vs $0.558$. Reported, **not shipped**. |

## Challenges we ran into

- **Our first model lost.** We kept the negative result on the front page and moved from single pitches to monthly patterns.
- **Real pitchers are bursty.** We saw 27 alerts where a binomial null expects $4.4$. A beta-binomial null cuts the alerts to 3 and moves May 2025 up to #12, but its score ($2.55$) falls just short of the alert threshold. So we present a *ranked review list*, not an alarm.
- **A second honest null.** Our coach-mode injury warning tied a one-line velocity rule ($\Delta\text{AUC} = -0.005$, 95% CI $-0.020$ to $+0.009$), so we kept it out of the product.
- **Labels are allegations,** with $n = 18$ positives, so every interval is wide; we report them. One pitch number (Vavra) is ambiguous.
- **Ethics.** Alerts are anonymised everywhere except for the two charged pitchers, and the CLI hides names by default.

## Accomplishments that we're proud of

- An honest, reproducible answer to a live question, with frozen commits, tests and CI.
- A monitor that would have fired on June 1, 2025 at about one alert a month league-wide.
- A detection limit that tells regulators what public data can and cannot see.

## What we learned

A single rigged pitch is statistically invisible. A pattern is visible only above roughly 6–9 pitches a month. The false-alarm rate matters more than any headline accuracy. And a simple baseline can win: velocity alone already carries what public pitch data says about injury risk.

## What's next

- Velocity and pitch-type monitors for the other prop markets.
- A two-sided alert that joins pitch data with betting volume.
- Minor leagues and other tracked sports.
- A pilot with one integrity desk.
