# process_log.md · T2.3 · Grid Outage Forecaster + Appliance Prioritizer

**Candidate:** Nathnael Dereje Mengistu  
**Challenge:** T2.3 · Grid Outage Forecaster + Appliance Prioritizer  
**Date:** 2026-04-23  
**Total build time:** ~3.5 hours

---

## Hour-by-Hour Timeline

| Time | Activity |
|------|----------|
| 0:00–0:20 | Read both PDFs end-to-end. Identified the 4 tasks, 6 deliverables, scoring weights. Noted Product & Business = 20% weight — equal to technical. Decided to frontload data + model. |
| 0:20–0:45 | Wrote `generate_data.py`. Synthetic data: logistic outage model, LogNormal duration, dual-peak load, rainy season noise. Ran and verified: 4,320 rows, 12.2% outage rate. |
| 0:45–1:20 | Wrote `forecaster.py`. Chose LightGBM over Prophet (see hardest decision). Built feature engineering: 4 load lags, rolling stats, weather, temporal flags. Fit + confirmed forecast runs in <300ms. |
| 1:20–1:50 | Wrote `prioritizer.py`. Implemented `plan()` function. Tested critical-before-luxury rule, peak-hour protection. Confirmed correct appliance shedding across all 3 business archetypes. |
| 1:50–2:10 | Ran rolling 30-day evaluation (`--eval`). Results: Brier=0.1756, MAE=61.2min, lead_time=2.79h. Documented in eval notebook. |
| 2:10–2:45 | Built `lite_ui.html`. Pure canvas chart (no JS library = smaller file). Hour grid, appliance plan, SMS tab, About tab. Business switcher. Offline banner. Verified <50KB (actual: 33KB). |
| 2:45–3:10 | Wrote `digest_spec.md`. Filled in all 4 sections: SMS design, offline protocol, LED relay adaptation, revenue calculation with real RWF numbers. |
| 3:10–3:30 | Wrote eval notebook (`eval.ipynb`), README, SIGNED.md. Verified all files present. |
| 3:30–3:45 | Final review: tested `python prioritizer.py salon` terminal output, verified SMS <160 chars, checked README runs in 2 commands. |

---

## LLM / Tool Use Declaration

**Tool used:** Claude Sonnet 4.6 (claude.ai)  
**Role:** Code scaffolding, design review, artifact drafting

**How I used it:**
- Described the challenge and asked Claude to help scaffold all files simultaneously
- Reviewed and edited all generated code before running — fixed the lag indexing in `build_features()`, adjusted shed threshold logic in `prioritizer.py`, redesigned the chart rendering
- The Product & Business thinking (LED board choice, RWF numbers, 6-hour staleness rule, Rwanda-specific context) is mine — I drew on my experience with SME operations across East Africa

**Three sample prompts I actually sent:**

1. *"Build generate_data.py for the AIMS KTT T2.3 challenge. The spec says: logistic outage model with sigmoid(a0 + a1*load_lag1 + a2*rain + a3*hour_of_day), LogNormal duration mean=90min sigma=0.6, dual-peak load morning+evening, weekly seasonality, rainy season noise. Output grid_history.csv with columns: timestamp, load_mw, temp_c, humidity, wind_ms, rain_mm, outage, duration_min. Also generate appliances.json and businesses.json matching the 10 appliances and 3 archetypes in the brief."*

2. *"Now write forecaster.py using LightGBM. Features: load lags at 1h, 2h, 24h, 48h; rolling mean and std; weather cols; hour, DOW, month, is_weekend, is_peak_morning, is_peak_evening, is_rainy_season; outage_lag1, outage_roll6_sum. Fit a classifier for P(outage) and a regressor for E[duration|outage]. predict_next_24h() returns list of 24 dicts including p_outage, p_outage_low, p_outage_high, expected_duration_min, risk_level. Include --eval flag for rolling 30-day Brier + MAE."*

3. *"Write prioritizer.py with a plan() function. Core rule: shed luxury first, then comfort, never critical unless P>0.5. Within each category, shed lowest-revenue appliances first. Protect critical appliances during peak hours regardless of risk. Calculate expected revenue saved vs naive full-on operation. Include format_digest() generating 3 SMS messages max 160 chars each, mixing Kinyarwanda and English."*

**One prompt I discarded and why:**

I drafted a prompt asking Claude to add a neighbour-signal stretch goal (crowd-reported outages re-ranking forecasts). I discarded it because: (a) it would have pushed total time past 4h, (b) a clean working baseline with solid Product & Business artifacts scores better than a half-working stretch feature. The brief itself warns: "A clean, simple, correct baseline always beats a half-working 'production' solution."

---

## Hardest Decision

**LightGBM vs Prophet for the forecasting backbone.**

Prophet was the first option listed in the brief and is more interpretable (explicit seasonality decomposition, trend + Fourier terms). LightGBM is faster to retrain, handles tabular weather features natively without special regressors, and easily produces calibrated probabilities via `predict_proba`. The trade-off: Prophet would have given me a cleaner uncertainty band from its built-in posterior sampling, and the decomposition would be easier to explain in the live defense ("here is the weekly component, here is the rainy-season component").

I chose LightGBM because: (1) the 180-day synthetic dataset has structured patterns that tabular methods handle well, (2) I wanted the weather features (rain, humidity) as first-class inputs without Prophet's awkward `add_regressor()` API, (3) inference speed — <300ms is a hard constraint. The risk I accepted: I need to explain the feature importances clearly in the live defense, and the uncertainty band is a heuristic (±0.08) rather than a proper posterior interval. If I had more time, I would fit isotonic regression on validation probabilities to get a calibrated confidence interval instead.
