"""
seed_and_run.py

Loads sample_outcomes.json into the database and prints the full /impact response.
Uses simulation fallback — no OpenAI key required.

Usage:
    python seed_and_run.py
"""

import json
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force simulation mode for demo
os.environ["USE_SIMULATION_FALLBACK"] = "true"

from database.db import init_db, insert_lead, get_lead_count
from pipeline.validator import validate_batch
from pipeline.ai_processor import run_impact_pipeline
from database.db import get_all_leads


def load_data():
    data_path = os.path.join(os.path.dirname(__file__), "data", "sample_outcomes.json")
    with open(data_path) as f:
        records = json.load(f)

    valid, invalid = validate_batch(records)
    for lead in valid:
        insert_lead(lead)

    print(f"Loaded {len(valid)} leads | {len(invalid)} rejected")
    print(f"Total in DB: {get_lead_count()}")
    if invalid:
        print("Rejected:")
        for r in invalid:
            print(f"  {r}")


def run_analysis():
    leads = get_all_leads()
    result = run_impact_pipeline(leads)

    print("\n" + "=" * 60)
    print("IMPACT ENGINE — FULL OUTPUT")
    print("=" * 60)

    m = result.metrics
    print(f"\n[ METRICS ]")
    print(f"  Total leads:              {m.total_leads}")
    print(f"  Revenue generated:        €{m.total_revenue_generated:,.2f}")
    print(f"  Revenue lost:             €{m.total_revenue_lost:,.2f}")
    print(f"  Missed opportunity:       €{m.missed_opportunity_value:,.2f}")
    print(f"  False positive cost:      €{m.false_positive_cost:,.2f}")
    print(f"  Delayed opportunity cost: €{m.delayed_opportunity_value:,.2f}")
    print(f"  Net impact:               €{m.net_impact:,.2f}")
    print(f"  Conversion rate:          {m.conversion_rate:.1%}")
    print(f"  False positive rate:      {m.false_positive_rate:.1%}")
    print(f"  Missed opportunity rate:  {m.missed_opportunity_rate:.1%}")
    print(f"  Avg confidence (conv):    {m.avg_confidence_converted}")
    print(f"  Avg confidence (no conv): {m.avg_confidence_not_converted}")

    a = result.analysis
    print(f"\n[ ANALYSIS ] {'(simulated)' if a.simulated else '(OpenAI)'}")
    print(f"  Summary: {a.summary}")
    print(f"\n  Key issues:")
    for issue in a.key_issues:
        print(f"    - {issue}")
    print(f"\n  Root causes:")
    for cause in a.root_causes:
        print(f"    - {cause}")

    print(f"\n[ RECOMMENDATIONS ]")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"\n  {i}. Action: {rec.action}")
        if rec.from_value is not None:
            print(f"     From:   {rec.from_value}  ->  To: {rec.to_value}")
        print(f"     Reason: {rec.reason}")
        print(f"     Effect: {rec.expected_effect}")
        print(f"     Trade-off: {rec.tradeoff}")

    print("\n" + "=" * 60)
    print("Simulation complete. No OpenAI credits used.")
    print("Set USE_SIMULATION_FALLBACK=false and add OPENAI_API_KEY to use live AI analysis.")
    print("=" * 60)


if __name__ == "__main__":
    init_db()
    load_data()
    run_analysis()
