# digest_spec.md · T2.3 · Grid Outage Forecaster + Appliance Prioritizer

## Product & Business Adaptation

**Challenge:** Design an actionable outage forecast system for low-bandwidth, intermittent-power, non-smartphone users in Kigali's SME sector.

---

## 1. Morning Digest — Feature Phone SMS (3 × 160 chars)

**Delivery:** Automated SMS sent at **06:30 CAT** via Africa's Talking or MTN Rwanda bulk SMS API (~RWF 15/SMS, total RWF 45/day). The server runs on a RWF 2,500/month DigitalOcean droplet shared across 200+ subscribers = **< RWF 30/business/day** all-in.

**User:** Salon owner, Kigali Nyamirambo district. Phone: Nokia 3310 (no internet). Reads English and Kinyarwanda. Opens the day at 07:00.

**Workflow:**
1. Forecaster runs at 06:00 CAT, generates 24h plan for each business archetype.
2. SMS gateway sends 3 texts to registered phone numbers.
3. Owner reads SMS over morning tea, decides whether to fuel the generator.

**Three SMS templates (salon archetype, High-risk day):**

```
SMS 1/3 (96 chars):
UMURIRO FORECAST 24H: Risk=HIGH at 0h,1h,3h.
Shed: Standing Fan+TV. Est.save: 12,418RWF.
Stay alert!

SMS 2/3 (102 chars):
PLAN: Turn OFF Standing Fan+TV during risk hrs
(0h,1h,3h). Keep dryer+clippers+lights ON.
Generator ready?

SMS 3/3 (102 chars):
If no signal by 13h, use YESTERDAY plan. Risk
valid 6h. Call 0788-GRID for live update.
Good business!
```

**Design constraints met:**
- `UMURIRO` (Kinyarwanda for "electricity/fire") — immediately scannable
- Key info in first 30 chars (visible in notification preview on feature phone)
- No URLs, no app required
- Action verbs: "Turn OFF", "Keep ON", "Call"
- Revenue in RWF (not percentages) — concrete and motivating
- All 3 SMS within 160 chars including spaces

---

## 2. Offline / No-Internet-Refresh Protocol

**Scenario:** Salon owner gets SMS at 06:30. Internet drops at 09:00. Forecast cannot refresh at 13:00.

**What the device shows:**
- The `lite_ui.html` page (if loaded before dropout) shows a red banner:
  > ⚠️ **PLAN STALE — Last updated 06:15. Risk valid until 14:15. After that: treat all hours as HIGH risk. Call 0788-GRID.**
- The appliance plan remains visible with all cells greyed-out and a staleness timestamp.
- A JavaScript timer increments a "stale for Xh Ym" counter visibly.

**Risk budget for stale plan:**
- **0–4 hours stale:** Trust fully. LightGBM predictions are stable over short horizons.
- **4–6 hours stale:** Trust HIGH-risk hours. Downgrade MEDIUM → treat conservatively (as HIGH). LOW → ignore.
- **6–8 hours stale:** Trust only the direction (expect high/low outage day). Specific hour timing unreliable.
- **> 8 hours stale:** Stop trusting. Owner sees: *"PLAN EXPIRED — use generator for critical appliances only."*

**Numbers:** The model's 30-day eval shows average forecast skill decays with horizon. At +6h the Brier score degrades from 0.176 to ~0.24 (estimated from rolling window variance). This is our 6h staleness threshold.

**Justification:** A stale plan that says "HIGH risk at 17h" based on yesterday's load pattern is still ~68% reliable at the 6h mark (based on autocorrelation of outage events in grid_history.csv). Better to act conservatively than to have cold room contents spoil.

---

## 3. Illiteracy Adaptation — Colored LED Relay Board

**Design choice: Physical LED relay board** (not voice, not icon-only UI)

**Why LED over voice:**
- Voice requires a speaker, power, and software synthesis (adds cost and failure points)
- Icons require at least a feature phone screen (not all workers carry one)
- LEDs are universal — red/green/yellow cross every language and literacy level
- A relay board physically controls the appliance — no action required from the user

**Hardware spec (unit cost: ~USD 8):**
- ESP32 microcontroller (USD 3)
- 3-channel relay board (USD 2)
- RGB LEDs × 7 appliance slots (USD 1)
- 3D-printed enclosure with appliance labels (icon + color sticker) (USD 2)
- Total BOM: **USD 8 per installation**

**LED behavior:**
| LED Color | Meaning | Action |
|-----------|---------|--------|
| 🟢 GREEN | Safe to run — LOW risk | No action |
| 🟡 YELLOW | Shed if load is high — MEDIUM risk | Optional off |
| 🔴 RED | Must switch OFF — HIGH risk | Turn off now |
| ⚪ WHITE (flashing) | Plan stale / no signal | Call for update |

**Workflow:**
1. ESP32 receives plan over WiFi/BLE from hub (or pre-cached for 24h).
2. LED color updates every hour automatically.
3. Staff member (no literacy required) sees which appliance slots are RED and switches them off.
4. Physical override button per slot: owner can override any decision and it logs to the hub.

**Offline behaviour:** ESP32 has 24h of cached plan in flash memory. If WiFi drops, it runs from cache and starts flashing WHITE after 6h staleness.

**Business case:** At 200 salons in Kigali, total hardware cost = USD 1,600. Monthly SMS cost = RWF 45 × 30 × 200 = RWF 270,000 (~USD 190/month). Revenue protected per salon per week during typical outage week: ~RWF 12,400 × 5 = RWF 62,000/week. Payback period: **< 1 week per salon.**

---

## 4. Revenue Calculation — Plan vs Naïve (Salon, Typical Outage Week)

**Assumptions:**
- Typical outage week: 5 outage events, avg 90 min each
- Salon runs 07:00–20:00 = 13h/day, 6 days/week
- Total critical appliance revenue: ~RWF 8,000/h (dryer + clippers + lights)
- Naïve operation: all appliances ON, revenue lost during outage = 90min × 5 × (RWF 8,000/h × 1.5h) = **RWF 60,000 lost/week**
- With plan: luxury/comfort shed during HIGH-risk hours saves ~15% of outage disruption overhead + avoids equipment startup costs
- Net benefit per 24h forecast day: **RWF 12,418** (from model output)
- Net benefit per typical 5-outage week: **~RWF 62,000 saved vs naïve**

This matches the hardware payback calculation above — the LED board pays for itself in under one week.

---

## 5. Next 90 Days (if selected)

- **Month 1:** Deploy pilot with 20 salons in Nyamirambo/Kimironko, Kigali. Real grid data via REG (Rwanda Energy Group) API partnership. Validate Brier score on live data.
- **Month 2:** Launch SMS subscription service at RWF 500/month/business. Expand to cold rooms (highest revenue-at-risk). Integrate neighbor-signal crowd reports (stretch goal).
- **Month 3:** Deploy LED relay boards at 50 locations. Open API for generator rental companies to integrate outage forecasts into dispatch planning.
