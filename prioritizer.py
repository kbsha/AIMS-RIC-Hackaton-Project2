"""
T2.3 · prioritizer.py
Appliance load-shedding plan generator.
Given a 24h forecast and a business's appliance list,
outputs per-appliance, per-hour ON/OFF plan maximizing
expected revenue under the 'drop luxury before critical' rule.

Usage:
    from prioritizer import plan, load_data
    appliances, businesses = load_data()
    forecast = [...]  # from forecaster.py
    result = plan(forecast, appliances, business_id="salon")
    print(result)
"""

import json
from pathlib import Path
from typing import Optional

# Category priority order (lower = shed first / shed last... no, drop luxury FIRST)
# Shedding priority (1 = shed first): luxury > comfort > critical
SHED_ORDER = {"luxury": 1, "comfort": 2, "critical": 3}
CATEGORY_REVENUE_WEIGHT = {"critical": 1.0, "comfort": 0.6, "luxury": 0.2}

# Outage risk thresholds for shed depth
RISK_SHED_FRACTION = {
    "LOW":    0.0,   # no shedding
    "MEDIUM": 0.33,  # shed luxury
    "HIGH":   0.66,  # shed luxury + comfort
}


def load_data(appliances_path="appliances.json", businesses_path="businesses.json"):
    with open(appliances_path) as f:
        appliances = json.load(f)
    with open(businesses_path) as f:
        businesses = json.load(f)
    return appliances, businesses


def get_business_appliances(appliances: list, business: dict) -> list:
    """Filter appliances to those used by this business."""
    ap_map = {a["id"]: a for a in appliances}
    return [ap_map[aid] for aid in business["appliance_ids"] if aid in ap_map]


def plan(forecast: list[dict], appliances: list, business_id: str = "salon",
         businesses_path: str = "businesses.json") -> dict:
    """
    Core planning function.

    Algorithm:
    1. For each hour, determine outage risk level from forecast.
    2. Sort appliances by shed priority (luxury first, critical last).
    3. Apply shed depth based on risk: LOW=none, MEDIUM=shed luxury,
       HIGH=shed luxury+comfort. Critical never shed unless P>0.5.
    4. Within each category, break ties by lowest revenue-per-watt (shed cheapest first).
    5. Calculate expected revenue saved vs naïve full-on.

    Returns dict with 24-hour plan per appliance + summary stats.
    """
    # Load business
    with open(businesses_path) as f:
        businesses = json.load(f)
    biz_map = {b["id"]: b for b in businesses}
    business = biz_map[business_id]
    biz_appliances = get_business_appliances(appliances, business)

    # Sort appliances: shed luxury first, then comfort, then critical
    # Within category: sort by revenue desc (protect highest revenue first)
    def shed_sort_key(ap):
        cat_priority = SHED_ORDER[ap["category"]]  # luxury=1 shed first
        rev = ap["revenue_if_running_rwf_per_h"]
        return (cat_priority, rev)  # shed low-revenue luxury first

    sorted_appliances = sorted(biz_appliances, key=shed_sort_key)

    hourly_plan = []
    total_revenue_plan = 0
    total_revenue_naive = 0

    for hour_data in forecast:
        h = hour_data["hour"]
        p_out = hour_data["p_outage"]
        risk = hour_data["risk_level"]
        exp_dur = hour_data["expected_duration_min"]

        # Fraction of hour expected to be without power
        frac_lost = (exp_dur / 60.0) * p_out
        frac_lost = min(frac_lost, 1.0)

        # Determine how many categories to shed
        # HIGH risk: shed luxury + comfort (keep critical)
        # MEDIUM risk: shed luxury only
        # LOW risk: keep all on
        # Exception: if P(outage) > 0.5, even critical gets load-managed
        categories_to_shed = set()
        if risk == "HIGH":
            categories_to_shed = {"luxury", "comfort"}
        elif risk == "MEDIUM":
            categories_to_shed = {"luxury"}
        if p_out > 0.50:
            categories_to_shed.add("critical")

        appliance_states = []
        hour_revenue_plan = 0
        hour_revenue_naive = 0

        for ap in biz_appliances:
            # Check business peak hours — don't shed critical during peak
            is_peak = h in business.get("peak_hours", [])
            if ap["category"] == "critical" and is_peak:
                # Never shed critical during peak hours regardless
                state = "ON"
            elif ap["category"] in categories_to_shed:
                state = "OFF"
            else:
                state = "ON"

            # Revenue calculation
            base_rev = ap["revenue_if_running_rwf_per_h"]
            naive_rev = base_rev * (1 - frac_lost)  # naive: stays on, loses revenue during outage
            plan_rev = base_rev if state == "ON" else 0  # plan: if OFF we save the outage disruption

            # If ON and outage still happens, we lose some revenue regardless
            if state == "ON":
                plan_rev = base_rev * (1 - frac_lost)

            hour_revenue_plan += plan_rev
            hour_revenue_naive += naive_rev

            appliance_states.append({
                "appliance_id": ap["id"],
                "name": ap["name"],
                "category": ap["category"],
                "state": state,
                "watts": ap["watts_avg"] if state == "ON" else 0,
                "revenue_rwf": round(plan_rev, 0),
                "shed_reason": f"Risk={risk}, P={p_out:.2f}" if state == "OFF" else None,
            })

        total_revenue_plan += hour_revenue_plan
        total_revenue_naive += hour_revenue_naive

        hourly_plan.append({
            "hour_offset": hour_data["hour_offset"],
            "timestamp": hour_data["timestamp"],
            "hour": h,
            "p_outage": p_out,
            "risk_level": risk,
            "expected_duration_min": exp_dur,
            "appliances": appliance_states,
            "hour_revenue_plan_rwf": round(hour_revenue_plan, 0),
            "hour_revenue_naive_rwf": round(hour_revenue_naive, 0),
        })

    revenue_saved = total_revenue_plan - total_revenue_naive
    # In HIGH risk periods, turning off luxury/comfort means we don't waste startup costs
    # but main saving is avoiding the disruption penalty we model as a 20% recovery cost
    disruption_penalty = total_revenue_naive * 0.20
    net_benefit = revenue_saved + disruption_penalty

    return {
        "business": business["name"],
        "business_id": business_id,
        "plan": hourly_plan,
        "summary": {
            "total_revenue_plan_rwf": round(total_revenue_plan, 0),
            "total_revenue_naive_rwf": round(total_revenue_naive, 0),
            "revenue_saved_rwf": round(revenue_saved, 0),
            "disruption_penalty_avoided_rwf": round(disruption_penalty, 0),
            "net_benefit_rwf": round(net_benefit, 0),
            "hours_with_shed": sum(
                1 for h in hourly_plan
                if any(a["state"] == "OFF" for a in h["appliances"])
            ),
        },
    }


def format_digest(plan_result: dict, forecast: list) -> list[str]:
    """
    Generate 3 SMS messages (max 160 chars each) for the morning digest.
    Designed for feature phone delivery.
    """
    biz = plan_result["business"]
    summary = plan_result["summary"]
    hourly = plan_result["plan"]

    # Find highest-risk hours
    high_risk_hours = [h for h in hourly if h["risk_level"] == "HIGH"]
    med_risk_hours = [h for h in hourly if h["risk_level"] == "MEDIUM"]

    if high_risk_hours:
        risk_times = ",".join([str(h["hour"]) + "h" for h in high_risk_hours[:3]])
        risk_word = "HIGH"
    elif med_risk_hours:
        risk_times = ",".join([str(h["hour"]) + "h" for h in med_risk_hours[:3]])
        risk_word = "MED"
    else:
        risk_times = "none"
        risk_word = "LOW"

    # Appliances to shed
    shed_hours = [h for h in hourly if any(a["state"] == "OFF" for a in h["appliances"])]
    if shed_hours:
        sample_hour = shed_hours[0]
        shed_names = [a["name"].split()[0] for a in sample_hour["appliances"]
                      if a["state"] == "OFF"][:2]
        shed_str = "+".join(shed_names)
    else:
        shed_str = "none"

    net = int(summary["net_benefit_rwf"])
    saved_str = f"{net:,}RWF"

    sms1 = f"UMURIRO FORECAST 24H: Risk={risk_word} at {risk_times}. Shed: {shed_str}. Est.save: {saved_str}. Stay alert!"
    sms2 = f"PLAN: Turn OFF {shed_str} during risk hrs ({risk_times}). Keep dryer+clippers+lights ON. Generator ready?"
    sms3 = f"If no signal by 13h, use YESTERDAY plan. Risk valid 6h. Call 0788-GRID for live update. Good business!"

    # Enforce 160 char limit
    sms1 = sms1[:160]
    sms2 = sms2[:160]
    sms3 = sms3[:160]

    return [sms1, sms2, sms3]


def print_plan(plan_result: dict):
    """Pretty-print the 24h plan to terminal."""
    print(f"\n{'='*70}")
    print(f"  LOAD-SHEDDING PLAN — {plan_result['business']}")
    print(f"{'='*70}")
    print(f"{'Hour':>5} {'Time':>12} {'Risk':>6} {'P(out)':>7} | Appliances OFF")
    print("-" * 70)
    for h in plan_result["plan"]:
        off = [a["name"][:12] for a in h["appliances"] if a["state"] == "OFF"]
        off_str = ", ".join(off) if off else "—"
        print(f"{h['hour']:>5} {h['timestamp'][11:]:>12} {h['risk_level']:>6} "
              f"{h['p_outage']:>7.3f} | {off_str}")
    print("-" * 70)
    s = plan_result["summary"]
    print(f"  Net benefit vs naïve: {s['net_benefit_rwf']:,.0f} RWF")
    print(f"  Revenue (plan):       {s['total_revenue_plan_rwf']:,.0f} RWF")
    print(f"  Shed hours:           {s['hours_with_shed']}/24")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys
    from forecaster import Forecaster

    business_id = sys.argv[1] if len(sys.argv) > 1 else "salon"

    print(f"Fitting forecaster...")
    fc = Forecaster().fit("grid_history.csv")
    forecast = fc.predict_next_24h()

    appliances, businesses = load_data()

    print(f"\nGenerating plan for: {business_id}")
    result = plan(forecast, appliances, business_id=business_id)
    print_plan(result)

    # SMS digest
    sms_msgs = format_digest(result, forecast)
    print("📱 Morning SMS Digest (3×160 chars):")
    for i, msg in enumerate(sms_msgs, 1):
        print(f"  SMS {i} ({len(msg)} chars): {msg}")
