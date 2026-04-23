# T2.3 · Grid Outage Forecaster + Appliance Prioritizer
**AIMS KTT Fellowship Hackathon 2026**

Predict 24-hour grid outage probability and generate actionable load-shedding plans for SMEs — designed for low-bandwidth, offline-first, non-smartphone users in Rwanda.

---

## ⚡ Quickstart (≤ 2 commands, free Colab CPU)

```bash
pip install pandas numpy scikit-learn lightgbm
python generate_data.py && python prioritizer.py salon
```

That's it. Generates all data, fits the model, prints the 24h plan and SMS digest for the salon archetype.

---

## 📊 Evaluation Metrics (30-day held-out)

| Metric | Value | Baseline |
|--------|-------|----------|
| Brier Score (P outage) | **0.1756** | 0.212 (naïve rate) |
| Duration MAE | **61.2 min** | — |
| Avg Lead Time | **2.79 h** | — |
| Inference Latency | **< 300 ms CPU** | — |
| Retrain Time | **< 5 min** | — |

---

## 📁 Repository Structure

```
├── generate_data.py      # Synthetic data generator (reproducible, seed=42)
├── forecaster.py         # LightGBM probabilistic outage forecaster
├── prioritizer.py        # Constrained appliance load-shedding planner
├── lite_ui.html          # Static 50KB dashboard (open in any browser)
├── digest_spec.md        # Product & Business adaptation artifact
├── process_log.md        # Hour-by-hour timeline + LLM tool use
├── SIGNED.md             # Honor code (signed)
├── eval.ipynb            # Rolling evaluation notebook
├── grid_history.csv      # Generated: 180 days × hourly grid data
├── appliances.json       # 10 appliances with categories + revenue
└── businesses.json       # 3 business archetypes (salon, cold room, tailor)
```

---

## 🔧 Usage

### Generate data
```bash
python generate_data.py
# → grid_history.csv, appliances.json, businesses.json
```

### Run forecast (CLI)
```bash
python forecaster.py                    # 24h forecast preview
python forecaster.py --eval             # Rolling 30-day Brier + MAE
python forecaster.py --serve            # JSON output + latency
```

### Run appliance plan
```bash
python prioritizer.py salon             # Salon archetype
python prioritizer.py cold_room         # Cold room archetype
python prioritizer.py tailor            # Tailor archetype
```

### Open UI
```bash
# Just open lite_ui.html in any browser — no server needed
```

---

## 🏗️ Architecture

```
grid_history.csv
      │
      ▼
forecaster.py::build_features()   ← lag features, rolling stats, weather, temporal
      │
      ▼
LightGBM Classifier → P(outage) per hour
LightGBM Regressor  → E[duration | outage] per hour
      │
      ▼
prioritizer.py::plan()
  Shed order: luxury → comfort → critical
  Tie-break: lowest revenue-per-hour shed first
  Exception: critical protected during peak hours
      │
      ▼
lite_ui.html   (forecast chart + appliance grid + SMS digest)
```

---

## 🌍 Product & Business Design

Designed for **low-bandwidth, offline-first, non-smartphone users**:

- **Feature phone SMS digest** (3 × 160 chars) at 06:30 CAT — no internet required for the end user
- **Offline fallback**: cached plan valid 6h, staleness banner after that, plan expired after 8h
- **Illiteracy adaptation**: Colored LED relay board (ESP32 + 3-channel relay, ~USD 8/unit) — red/green/yellow per appliance slot, no reading required
- **Cost**: ~RWF 30/business/day all-in (SMS + server amortized across 200+ subscribers)
- **Revenue protected**: ~RWF 62,000/week per salon vs naïve full-on operation

See `digest_spec.md` for full specification with numbers, users, and workflows.

---

## 📹 4-Minute Video

[YouTube link — to be inserted before submission]

**Video structure:**
- 0:00–0:30 On-camera intro: name, challenge ID, Brier score 0.1756
- 0:30–1:30 Live code: `prioritizer.py::plan()` — critical-before-luxury logic
- 1:30–2:30 Live demo: `lite_ui.html` salon forecast + plan
- 2:30–3:30 Read `digest_spec.md` morning SMS aloud
- 3:30–4:00 Three spoken answers

---

## 🤖 Model Hosting

Model weights (LightGBM pkl files) hosted on Hugging Face Hub:  
`[HF link — to be inserted before submission]`

Alternatively, retrain from scratch in < 5 min:
```bash
python forecaster.py --fit
```

---

## 📜 License

MIT License — see LICENSE file.

---

## ✅ Submission Checklist

- [x] Public GitHub repo with README
- [x] `generate_data.py` — reproducible in 2 commands
- [x] `forecaster.py` + `prioritizer.py`
- [x] `lite_ui.html` — < 50KB static page
- [x] `eval.ipynb` — rolling 30-day metrics
- [x] `digest_spec.md` — Product & Business artifact with real numbers
- [x] `process_log.md` — timeline + LLM use declared
- [x] `SIGNED.md` — honor code signed
- [ ] 4-minute video URL (to be added)
- [ ] Hugging Face model card link (to be added)
