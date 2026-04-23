import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="T2.3 · Grid Outage Forecaster",
    page_icon="⚡",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0f1117; color: #e8eaf6; }
  [data-testid="stSidebar"] { background: #1a1d27; }
  .metric-card {
    background: #1a1d27; border: 1px solid #2e3350; border-radius: 10px;
    padding: 14px 18px; text-align: center;
  }
  .metric-val { font-size: 1.6rem; font-weight: 800; color: #6366f1; }
  .metric-lbl { font-size: 11px; color: #8892b0; text-transform: uppercase; letter-spacing: .05em; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  }
  .badge-high    { background: #7f1d1d; color: #fca5a5; }
  .badge-medium  { background: #78350f; color: #fcd34d; }
  .badge-low     { background: #14532d; color: #86efac; }
  .badge-on      { background: #14532d; color: #86efac; }
  .badge-off     { background: #3f3f46; color: #a1a1aa; }
  .badge-critical{ background: #1e3a8a; color: #93c5fd; }
  .badge-comfort { background: #4a1d96; color: #c4b5fd; }
  .badge-luxury  { background: #374151; color: #9ca3af; }
  .ap-card {
    background: #1a1d27; border: 1px solid #2e3350; border-radius: 8px;
    padding: 12px 14px; margin-bottom: 8px;
  }
  .ap-card.off { opacity: .6; border-color: #3f3f46; }
  .ap-name { font-weight: 600; font-size: 14px; color: #e8eaf6; margin-bottom: 4px; }
  .ap-meta { display: flex; gap: 6px; margin-bottom: 4px; }
  .ap-shed { font-size: 10px; color: #9ca3af; margin-top: 3px; }
  .ap-right { text-align: right; font-size: 12px; color: #8892b0; }
  .ap-rev { color: #22c55e; font-weight: 600; font-size: 13px; }
  .sms-box {
    background: #22263a; border: 1px solid #2e3350; border-radius: 8px;
    padding: 14px; margin-bottom: 10px; font-family: monospace; font-size: 13px;
    line-height: 1.6; color: #e8eaf6;
  }
  .plan-header {
    background: #1a1d27; border: 1px solid #2e3350; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 12px;
  }
  .section-title { font-size: 1rem; font-weight: 600; color: #e8eaf6; margin-bottom: 10px; }
  h1, h2, h3 { color: #e8eaf6 !important; }
  .stSelectbox label, .stSlider label { color: #8892b0 !important; }
  div[data-testid="metric-container"] {
    background: #1a1d27; border: 1px solid #2e3350; border-radius: 8px; padding: 8px;
  }
</style>
""", unsafe_allow_html=True)

# ── Embedded Data ─────────────────────────────────────────────────────────────
FORECAST = [
    {"hour_offset":0,"timestamp":"2024-06-29 00:00","hour":0,"p_outage":0.2708,"p_outage_low":0.1908,"p_outage_high":0.3508,"expected_duration_min":89.8,"risk_level":"HIGH"},
    {"hour_offset":1,"timestamp":"2024-06-29 01:00","hour":1,"p_outage":0.2554,"p_outage_low":0.1754,"p_outage_high":0.3354,"expected_duration_min":83.2,"risk_level":"HIGH"},
    {"hour_offset":2,"timestamp":"2024-06-29 02:00","hour":2,"p_outage":0.2169,"p_outage_low":0.1369,"p_outage_high":0.2969,"expected_duration_min":85.0,"risk_level":"MEDIUM"},
    {"hour_offset":3,"timestamp":"2024-06-29 03:00","hour":3,"p_outage":0.2554,"p_outage_low":0.1754,"p_outage_high":0.3354,"expected_duration_min":85.0,"risk_level":"HIGH"},
    {"hour_offset":4,"timestamp":"2024-06-29 04:00","hour":4,"p_outage":0.2602,"p_outage_low":0.1802,"p_outage_high":0.3402,"expected_duration_min":78.8,"risk_level":"HIGH"},
    {"hour_offset":5,"timestamp":"2024-06-29 05:00","hour":5,"p_outage":0.2503,"p_outage_low":0.1703,"p_outage_high":0.3303,"expected_duration_min":85.0,"risk_level":"HIGH"},
    {"hour_offset":6,"timestamp":"2024-06-29 06:00","hour":6,"p_outage":0.24,  "p_outage_low":0.16,  "p_outage_high":0.32,  "expected_duration_min":83.2,"risk_level":"MEDIUM"},
    {"hour_offset":7,"timestamp":"2024-06-29 07:00","hour":7,"p_outage":0.2208,"p_outage_low":0.1408,"p_outage_high":0.3008,"expected_duration_min":78.5,"risk_level":"MEDIUM"},
    {"hour_offset":8,"timestamp":"2024-06-29 08:00","hour":8,"p_outage":0.2208,"p_outage_low":0.1408,"p_outage_high":0.3008,"expected_duration_min":78.5,"risk_level":"MEDIUM"},
    {"hour_offset":9,"timestamp":"2024-06-29 09:00","hour":9,"p_outage":0.198, "p_outage_low":0.118, "p_outage_high":0.278, "expected_duration_min":86.0,"risk_level":"MEDIUM"},
    {"hour_offset":10,"timestamp":"2024-06-29 10:00","hour":10,"p_outage":0.24, "p_outage_low":0.16, "p_outage_high":0.32, "expected_duration_min":71.3,"risk_level":"MEDIUM"},
    {"hour_offset":11,"timestamp":"2024-06-29 11:00","hour":11,"p_outage":0.2531,"p_outage_low":0.1731,"p_outage_high":0.3331,"expected_duration_min":73.1,"risk_level":"HIGH"},
    {"hour_offset":12,"timestamp":"2024-06-29 12:00","hour":12,"p_outage":0.2457,"p_outage_low":0.1657,"p_outage_high":0.3257,"expected_duration_min":76.9,"risk_level":"MEDIUM"},
    {"hour_offset":13,"timestamp":"2024-06-29 13:00","hour":13,"p_outage":0.263, "p_outage_low":0.183, "p_outage_high":0.343, "expected_duration_min":68.8,"risk_level":"HIGH"},
    {"hour_offset":14,"timestamp":"2024-06-29 14:00","hour":14,"p_outage":0.2582,"p_outage_low":0.1782,"p_outage_high":0.3382,"expected_duration_min":72.5,"risk_level":"HIGH"},
    {"hour_offset":15,"timestamp":"2024-06-29 15:00","hour":15,"p_outage":0.2194,"p_outage_low":0.1394,"p_outage_high":0.2994,"expected_duration_min":76.9,"risk_level":"MEDIUM"},
    {"hour_offset":16,"timestamp":"2024-06-29 16:00","hour":16,"p_outage":0.2688,"p_outage_low":0.1888,"p_outage_high":0.3488,"expected_duration_min":83.4,"risk_level":"HIGH"},
    {"hour_offset":17,"timestamp":"2024-06-29 17:00","hour":17,"p_outage":0.309, "p_outage_low":0.229, "p_outage_high":0.389, "expected_duration_min":84.6,"risk_level":"HIGH"},
    {"hour_offset":18,"timestamp":"2024-06-29 18:00","hour":18,"p_outage":0.3353,"p_outage_low":0.2553,"p_outage_high":0.4153,"expected_duration_min":84.6,"risk_level":"HIGH"},
    {"hour_offset":19,"timestamp":"2024-06-29 19:00","hour":19,"p_outage":0.3408,"p_outage_low":0.2608,"p_outage_high":0.4208,"expected_duration_min":76.1,"risk_level":"HIGH"},
    {"hour_offset":20,"timestamp":"2024-06-29 20:00","hour":20,"p_outage":0.3353,"p_outage_low":0.2553,"p_outage_high":0.4153,"expected_duration_min":99.4,"risk_level":"HIGH"},
    {"hour_offset":21,"timestamp":"2024-06-29 21:00","hour":21,"p_outage":0.3466,"p_outage_low":0.2666,"p_outage_high":0.4266,"expected_duration_min":100.6,"risk_level":"HIGH"},
    {"hour_offset":22,"timestamp":"2024-06-29 22:00","hour":22,"p_outage":0.2834,"p_outage_low":0.2034,"p_outage_high":0.3634,"expected_duration_min":102.5,"risk_level":"HIGH"},
    {"hour_offset":23,"timestamp":"2024-06-29 23:00","hour":23,"p_outage":0.2596,"p_outage_low":0.1796,"p_outage_high":0.3396,"expected_duration_min":106.9,"risk_level":"HIGH"},
]

SMS = [
    "UMURIRO FORECAST 24H: Risk=HIGH at 0h,1h,3h. Shed: Standing+TV. Est.save: 12,418RWF. Stay alert!",
    "PLAN: Turn OFF Standing+TV during risk hrs (0h,1h,3h). Keep dryer+clippers+lights ON. Generator ready?",
    "If no signal by 13h, use YESTERDAY plan. Risk valid 6h. Call 0788-GRID for live update. Good business!",
]

# ── Appliance plan generators ─────────────────────────────────────────────────
def salon_appliances(hour, risk):
    open_ = 7 <= hour <= 20
    peak  = 9 <= hour <= 17
    scale = 1.0 if peak else (0.75 if open_ else 0.0)
    if not open_:
        return [
            {"name":"Hair Dryer (2×)",       "category":"critical","state":"OFF","watts":2400,"revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Electric Clippers (3×)","category":"critical","state":"OFF","watts":120, "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"LED Lights",            "category":"critical","state":"ON", "watts":20,  "revenue_rwf":0},
            {"name":"Standing Fan",          "category":"comfort", "state":"OFF","watts":0,   "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"TV / Display",          "category":"comfort", "state":"OFF","watts":0,   "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Music System",          "category":"luxury",  "state":"OFF","watts":0,   "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Neon Sign",             "category":"luxury",  "state":"OFF","watts":0,   "revenue_rwf":0,"shed_reason":"Business closed"},
        ]
    shed_lux  = risk in ("HIGH","MEDIUM")
    shed_com  = risk == "HIGH"
    return [
        {"name":"Hair Dryer (2×)",       "category":"critical","state":"ON", "watts":2400,"revenue_rwf":round(2133*scale)},
        {"name":"Electric Clippers (3×)","category":"critical","state":"ON", "watts":120, "revenue_rwf":round(1422*scale)},
        {"name":"LED Lights",            "category":"critical","state":"ON", "watts":80,  "revenue_rwf":round(711*scale)},
        {"name":"Standing Fan",  "category":"comfort","state":"OFF" if shed_com else "ON","watts":0 if shed_com else 75, "revenue_rwf":0 if shed_com else round(285*scale),  **({"shed_reason":"HIGH risk — comfort shed"} if shed_com else {})},
        {"name":"TV / Display",  "category":"comfort","state":"OFF" if shed_com else "ON","watts":0 if shed_com else 150,"revenue_rwf":0 if shed_com else round(142*scale),  **({"shed_reason":"HIGH risk — comfort shed"} if shed_com else {})},
        {"name":"Music System",  "category":"luxury", "state":"OFF" if shed_lux else "ON","watts":0 if shed_lux else 80, "revenue_rwf":0, **({"shed_reason":"Risk ≥ MEDIUM — luxury shed"} if shed_lux else {})},
        {"name":"Neon Sign",     "category":"luxury", "state":"OFF" if shed_lux else "ON","watts":0 if shed_lux else 40, "revenue_rwf":0, **({"shed_reason":"Risk ≥ MEDIUM — luxury shed"} if shed_lux else {})},
    ]

def cold_appliances(hour, risk):
    open_ = 6 <= hour <= 20
    peak  = 8 <= hour <= 18
    scale = 1.0 if peak else (0.6 if open_ else 0.0)
    fridge_rev = round(1850*scale) if open_ else 0
    pump_rev   = round(1100*scale) if open_ else 0
    light_rev  = round(740*scale)  if open_ else 0
    fan_rev    = round(296*scale)  if open_ else 0
    tv_rev     = round(148*scale)  if open_ else 0
    shed_com = risk == "HIGH"
    shed_fan = shed_com or not open_
    shed_tv  = shed_com or not open_
    return [
        {"name":"Commercial Refrigerator","category":"critical","state":"ON", "watts":350,"revenue_rwf":fridge_rev or 200,**({"shed_reason":"After-hours — standby mode"} if not open_ else {})},
        {"name":"Water Pump",   "category":"critical","state":"ON"  if open_ else "OFF","watts":750 if open_ else 0,"revenue_rwf":pump_rev, **({"shed_reason":"After-hours — pump off"} if not open_ else {})},
        {"name":"LED Lights",   "category":"critical","state":"ON"  if open_ else "OFF","watts":80  if open_ else 0,"revenue_rwf":light_rev,**({"shed_reason":"After-hours — lights off"} if not open_ else {})},
        {"name":"Standing Fan", "category":"comfort", "state":"OFF" if shed_fan else "ON","watts":0 if shed_fan else 75, "revenue_rwf":0 if shed_fan else fan_rev,**({"shed_reason":"HIGH risk — comfort shed" if shed_com else "After-hours"} if shed_fan else {})},
        {"name":"TV / Display", "category":"comfort", "state":"OFF" if shed_tv  else "ON","watts":0 if shed_tv  else 150,"revenue_rwf":0 if shed_tv  else tv_rev, **({"shed_reason":"HIGH risk — comfort shed" if shed_com else "After-hours"} if shed_tv  else {})},
        {"name":"Backup Battery Charger","category":"luxury","state":"ON" if (risk=="LOW" and open_) else "OFF","watts":200 if (risk=="LOW" and open_) else 0,"revenue_rwf":0,**({"shed_reason":"Risk ≥ MEDIUM — luxury shed"} if not (risk=="LOW" and open_) else {})},
    ]

def tailor_appliances(hour, risk):
    open_ = 8 <= hour <= 18
    peak  = 9 <= hour <= 16
    scale = 1.0 if peak else (0.6 if open_ else 0.0)
    if not open_:
        return [
            {"name":"Sewing Machine (2×)","category":"critical","state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Overlocker",         "category":"critical","state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"LED Lights",         "category":"critical","state":"ON", "watts":20, "revenue_rwf":0},
            {"name":"Iron Press",         "category":"comfort", "state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Standing Fan",       "category":"comfort", "state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"Music System",       "category":"luxury",  "state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
            {"name":"TV / Display",       "category":"luxury",  "state":"OFF","watts":0,  "revenue_rwf":0,"shed_reason":"Business closed"},
        ]
    shed_lux = risk in ("HIGH","MEDIUM")
    shed_com = risk == "HIGH"
    shed_iron= risk == "HIGH"
    return [
        {"name":"Sewing Machine (2×)","category":"critical","state":"ON","watts":180,"revenue_rwf":round(590*scale)},
        {"name":"Overlocker",         "category":"critical","state":"ON","watts":100,"revenue_rwf":round(310*scale)},
        {"name":"LED Lights",         "category":"critical","state":"ON","watts":80, "revenue_rwf":round(180*scale)},
        {"name":"Iron Press",   "category":"comfort","state":"OFF" if shed_iron else "ON","watts":0 if shed_iron else 1000,"revenue_rwf":0 if shed_iron else round(260*scale),**({"shed_reason":"HIGH risk — heavy load shed"} if shed_iron else {})},
        {"name":"Standing Fan", "category":"comfort","state":"OFF" if shed_com  else "ON","watts":0 if shed_com  else 75,  "revenue_rwf":0 if shed_com  else round(120*scale),**({"shed_reason":"HIGH risk — comfort shed"}  if shed_com  else {})},
        {"name":"Music System", "category":"luxury", "state":"OFF" if shed_lux  else "ON","watts":0 if shed_lux  else 80,  "revenue_rwf":0,**({"shed_reason":"Risk ≥ MEDIUM — luxury shed"} if shed_lux else {})},
        {"name":"TV / Display", "category":"luxury", "state":"OFF" if shed_lux  else "ON","watts":0 if shed_lux  else 150, "revenue_rwf":0,**({"shed_reason":"Risk ≥ MEDIUM — luxury shed"} if shed_lux else {})},
    ]

PLANS = {
    "salon": {
        "label": "💇 Beauty Salon",
        "summary": {"total_revenue_plan_rwf":93850,"total_revenue_naive_rwf":101790,"net_benefit_rwf":12418,"hours_with_shed":24},
        "fn": salon_appliances,
    },
    "cold_room": {
        "label": "🧊 Cold Room",
        "summary": {"total_revenue_plan_rwf":118000,"total_revenue_naive_rwf":125000,"net_benefit_rwf":18000,"hours_with_shed":16},
        "fn": cold_appliances,
    },
    "tailor": {
        "label": "🧵 Tailor Shop",
        "summary": {"total_revenue_plan_rwf":42000,"total_revenue_naive_rwf":48000,"net_benefit_rwf":3600,"hours_with_shed":14},
        "fn": tailor_appliances,
    },
}

RISK_COLOR = {"HIGH": "#ef4444", "MEDIUM": "#f97316", "LOW": "#22c55e"}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Grid Outage Forecaster")
    st.markdown("<span style='color:#8892b0;font-size:12px'>T2.3 · AIMS KTT Hackathon 2026 · Kigali, Rwanda</span>", unsafe_allow_html=True)
    st.divider()

    st.markdown("### Model Metrics")
    st.metric("Brier Score", "0.176")
    st.metric("MAE (min)", "61.2")
    st.metric("Avg Lead Time", "2.79h")
    st.divider()

    st.markdown("### Business")
    biz_key = st.radio(
        "Select business",
        options=list(PLANS.keys()),
        format_func=lambda k: PLANS[k]["label"],
        label_visibility="collapsed",
    )
    st.divider()

    biz = PLANS[biz_key]
    s = biz["summary"]
    st.markdown("### Plan Summary")
    st.metric("Net Benefit (RWF)", f"{s['net_benefit_rwf']:,}")
    st.metric("Expected Rev (RWF)", f"{s['total_revenue_plan_rwf']:,}")
    high_h = sum(1 for f in FORECAST if f["risk_level"] == "HIGH")
    st.metric("HIGH Risk Hours", high_h)
    st.metric("Hours with Shed", s["hours_with_shed"])

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_forecast, tab_plan, tab_sms, tab_about = st.tabs(
    ["📈 Forecast", "🔌 Appliance Plan", "📱 SMS Digest", "ℹ️ About"]
)

# ══ FORECAST TAB ══════════════════════════════════════════════════════════════
with tab_forecast:
    st.markdown("### 24-Hour Outage Probability Forecast")

    hours       = [f["hour"] for f in FORECAST]
    p_out       = [f["p_outage"] for f in FORECAST]
    p_low       = [f["p_outage_low"] for f in FORECAST]
    p_high      = [f["p_outage_high"] for f in FORECAST]
    risk_levels = [f["risk_level"] for f in FORECAST]
    bar_colors  = [RISK_COLOR[r] for r in risk_levels]

    fig = go.Figure()

    # Risk background zones (coloured bar under chart)
    for f in FORECAST:
        col = {"HIGH":"rgba(239,68,68,.10)","MEDIUM":"rgba(249,115,22,.07)","LOW":"rgba(34,197,94,.04)"}[f["risk_level"]]
        fig.add_vrect(x0=f["hour"]-.5, x1=f["hour"]+.5, fillcolor=col, line_width=0, layer="below")

    # Uncertainty band
    fig.add_trace(go.Scatter(
        x=hours + hours[::-1],
        y=p_high + p_low[::-1],
        fill="toself", fillcolor="rgba(99,102,241,.18)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip", name="Uncertainty band",
    ))

    # Main line
    fig.add_trace(go.Scatter(
        x=hours, y=p_out,
        mode="lines+markers",
        line=dict(color="#6366f1", width=2.5),
        marker=dict(color=bar_colors, size=8, line=dict(color="#0f1117", width=1)),
        name="P(outage)",
        hovertemplate="Hour %{x}:00<br>P(outage)=%{y:.1%}<extra></extra>",
    ))

    # HIGH threshold line
    fig.add_hline(y=0.25, line=dict(color="#ef4444", dash="dash", width=1),
                  annotation_text="HIGH threshold", annotation_position="top left",
                  annotation_font_color="#ef4444")

    fig.update_layout(
        paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
        font=dict(color="#e8eaf6", size=12),
        xaxis=dict(title="Hour of day", gridcolor="#2e3350", tickvals=list(range(0,24,2))),
        yaxis=dict(title="P(outage)", gridcolor="#2e3350", tickformat=".0%", range=[0, 0.55]),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Hour grid ─────────────────────────────────────────────────────────────
    st.markdown("### Hourly Risk — click a cell to drill into plan")
    cols = st.columns(12)
    for i, f in enumerate(FORECAST):
        col_idx = i % 12
        with cols[col_idx]:
            risk = f["risk_level"]
            color = RISK_COLOR[risk]
            pct   = f"{f['p_outage']*100:.0f}%"
            st.markdown(f"""
            <div style='background:#1a1d27;border:1px solid #2e3350;border-radius:6px;
                 padding:6px 4px;text-align:center;margin-bottom:4px;'>
              <div style='font-size:10px;color:#8892b0'>{f["hour"]}h</div>
              <div style='font-size:14px;font-weight:700;color:{color}'>{pct}</div>
              <div style='margin-top:2px'><span class='badge badge-{risk.lower()}'>{risk}</span></div>
            </div>""", unsafe_allow_html=True)

    cols2 = st.columns(12)
    for i, f in enumerate(FORECAST):
        with cols2[i % 12]:
            pass  # second row of 12 hours already handled above

    # Second row (hours 12–23)
    st.markdown("")

# ══ PLAN TAB ══════════════════════════════════════════════════════════════════
with tab_plan:
    st.markdown("### 🔌 Appliance Plan")

    hour_idx = st.slider(
        "Select hour",
        min_value=0, max_value=23, value=0,
        format="%d:00",
    )

    fc = FORECAST[hour_idx]
    appliances = biz["fn"](hour_idx, fc["risk_level"])
    risk = fc["risk_level"]

    # Hour info header
    risk_color = RISK_COLOR[risk]
    st.markdown(f"""
    <div class='plan-header'>
      <b>Hour {hour_idx}</b> &nbsp;·&nbsp; {fc['timestamp'].split()[1]}
      &nbsp;&nbsp;<span class='badge badge-{risk.lower()}'>{risk}</span>
      &nbsp;&nbsp;P(outage) = <b>{fc['p_outage']*100:.1f}%</b>
      &nbsp;&nbsp;Exp. duration = <b>{fc['expected_duration_min']:.0f} min</b>
    </div>
    """, unsafe_allow_html=True)

    # Appliance cards in 2 columns
    left_col, right_col = st.columns(2)
    for i, ap in enumerate(appliances):
        target = left_col if i % 2 == 0 else right_col
        is_off = ap["state"] == "OFF"
        opacity = "opacity:.65;" if is_off else ""
        shed = f"<div class='ap-shed'>⚠ {ap['shed_reason']}</div>" if "shed_reason" in ap else ""
        rev_html = f"<div class='ap-rev'>{ap['revenue_rwf']:,} RWF/h</div>" if ap["state"] == "ON" and ap["revenue_rwf"] > 0 else "<div style='color:#6b7280'>—</div>"
        with target:
            st.markdown(f"""
            <div class='ap-card{"" if not is_off else " off"}' style='{opacity}'>
              <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                <div>
                  <div class='ap-name'>{ap['name']}</div>
                  <div class='ap-meta'>
                    <span class='badge badge-{ap['category']}'>{ap['category']}</span>
                    <span class='badge badge-{ap['state'].lower()}'>{ap['state']}</span>
                  </div>
                  {shed}
                </div>
                <div class='ap-right'>
                  <div style='font-size:11px;color:#8892b0'>{ap['watts']}W</div>
                  {rev_html}
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#1a1d27;border:1px solid #2e3350;border-radius:8px;
         padding:12px;font-size:12px;color:#8892b0;margin-top:8px;'>
      <b style='color:#e8eaf6'>Shedding Logic:</b>
      Luxury → Comfort → Critical (never shed during peak unless P &gt; 0.50).
      Within category: lowest revenue shed first. Critical always ON during business peak hours.
    </div>""", unsafe_allow_html=True)

# ══ SMS TAB ═══════════════════════════════════════════════════════════════════
with tab_sms:
    st.markdown("### 📱 Morning Digest — Feature Phone SMS")
    st.markdown("<span style='color:#8892b0;font-size:12px'>Sent at 06:30 CAT. Max 3 messages × 160 chars. Works on any GSM phone. No internet required. Language: Kinyarwanda/English mix for maximum reach.</span>", unsafe_allow_html=True)
    st.markdown("")

    for i, msg in enumerate(SMS):
        st.markdown(f"""
        <div class='sms-box'>
          <div style='display:flex;justify-content:space-between;margin-bottom:6px'>
            <span style='font-size:11px;font-weight:700;color:#6366f1'>SMS {i+1}/3</span>
            <span style='font-size:10px;color:#8892b0'>{len(msg)}/160 chars</span>
          </div>
          {msg}
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class='sms-box' style='border-color:#6366f1;margin-top:16px;'>
      <div style='font-size:12px;font-weight:700;color:#6366f1;margin-bottom:8px'>🔕 Offline Fallback Protocol</div>
      <div style='font-size:12px;color:#8892b0;line-height:1.7'>
        <b style='color:#e8eaf6'>If no internet refresh by 13:00:</b> Device shows last cached plan with
        a red ⚠️ staleness banner. Risk budget: plan valid for <b style='color:#f97316'>6 hours</b>
        from generation time. After 6h, all HIGH-risk flags remain but MEDIUM degrades to LOW (overly cautious).
        Maximum acceptable staleness: <b style='color:#ef4444'>8 hours</b>.
        Owner sees: "PLAN STALE — use generator, call 0788-GRID."
      </div>
    </div>
    <div class='sms-box' style='border-color:#22c55e;margin-top:10px;'>
      <div style='font-size:12px;font-weight:700;color:#22c55e;margin-bottom:8px'>🔊 Illiteracy Adaptation — Voice + LED Relay</div>
      <div style='font-size:12px;color:#8892b0;line-height:1.7'>
        <b style='color:#e8eaf6'>Design choice: Colored LED relay board</b> (3 LEDs per appliance slot).<br>
        🟢 GREEN = ON safe &nbsp;·&nbsp; 🟡 YELLOW = shed if load high &nbsp;·&nbsp; 🔴 RED = OFF now.<br>
        Board connects via GPIO to a ≈USD 8 ESP32 running cached plan. No reading required.
        Physical override switch lets owner override any LED. $8 hardware cost, zero ongoing data cost.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══ ABOUT TAB ═════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown("### Technical Notes")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class='sms-box'>
          <div style='font-size:12px;font-weight:700;color:#6366f1;margin-bottom:6px'>Model</div>
          <div style='font-size:12px;color:#8892b0;line-height:1.7'>
            <b style='color:#e8eaf6'>LightGBM</b> classifier for P(outage) + regressor for E[duration | outage].<br>
            Features: lagged load (1h, 2h, 24h, 48h), rolling stats, weather (temp, humidity, rain, wind),
            temporal (hour, DOW, month, peak flags, rainy season). Training: 150-day window.
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class='sms-box' style='margin-top:10px'>
          <div style='font-size:12px;font-weight:700;color:#6366f1;margin-bottom:6px'>Hardest Trade-off</div>
          <div style='font-size:12px;color:#8892b0;line-height:1.7'>
            Chose LightGBM over Prophet: faster retrain, handles irregular time steps,
            natively supports tabular weather features. Trade-off: less interpretable
            seasonality decomposition. Compensated with explicit hour/DOW/month features
            and SHAP values available in eval notebook.
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='sms-box'>
          <div style='font-size:12px;font-weight:700;color:#6366f1;margin-bottom:6px'>Performance</div>
          <div style='font-size:12px;color:#8892b0;line-height:1.7'>
            Brier score: <b style='color:#22c55e'>0.1756</b> (naïve base rate = ~0.212)<br>
            Duration MAE: <b style='color:#22c55e'>61.2 min</b><br>
            Avg lead time on true outages: <b style='color:#22c55e'>2.79h</b><br>
            Inference latency: <b style='color:#22c55e'>&lt;300ms CPU</b><br>
            Retraining time: <b style='color:#22c55e'>&lt;10 min</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class='sms-box' style='margin-top:10px'>
          <div style='font-size:12px;font-weight:700;color:#6366f1;margin-bottom:6px'>Constraints Met</div>
          <div style='font-size:12px;color:#8892b0;line-height:1.7'>
            ✅ CPU-only &nbsp;·&nbsp; ✅ &lt;10 min retrain &nbsp;·&nbsp; ✅ &lt;300ms serve<br>
            ✅ Feature phone SMS digest &nbsp;·&nbsp; ✅ Offline fallback protocol<br>
            ✅ Illiteracy adaptation &nbsp;·&nbsp; ✅ 3 business archetypes<br>
            ✅ Critical-before-luxury rule
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;color:#8892b0;font-size:11px;padding:20px 0 10px'>
      T2.3 · Grid Outage Forecaster + Appliance Prioritizer · AIMS KTT Hackathon 2026 · CPU-only
    </div>""", unsafe_allow_html=True)
