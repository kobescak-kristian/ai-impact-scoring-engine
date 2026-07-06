from config.settings import settings
from pipeline.router import route_lead
from utils.logger import get_logger

logger = get_logger(__name__)


def compute_lead_impact(lead: dict) -> dict:
    """
    Given a single lead record, compute its financial impact.
    Returns the lead dict enriched with:
      - impact_type
      - financial_impact (positive = gain, negative = loss/cost)
      - notes
    """
    decision = lead["decision"]
    outcome = lead["outcome"]
    lead_value = float(lead["lead_value"])

    impact_type = route_lead(decision, outcome)

    if impact_type == "revenue_generated":
        financial_impact = lead_value
        notes = "Correct decision — revenue realised"

    elif impact_type == "false_positive":
        # Sales cost incurred without revenue
        financial_impact = -(lead_value * settings.false_positive_cost_multiplier)
        notes = "False positive — sales effort wasted on non-converting lead"

    elif impact_type == "missed_opportunity":
        # Full lead value lost — AI archived a lead that later converted
        financial_impact = -(lead_value * settings.missed_opportunity_multiplier)
        notes = "Missed opportunity — lead was archived but later converted elsewhere"

    elif impact_type == "delayed_conversion":
        # Partial penalty for delay; revenue still eventually realised
        financial_impact = lead_value - (lead_value * settings.delayed_conversion_penalty)
        notes = "Delayed conversion — revenue realised but at reduced value due to delay cost"

    elif impact_type == "correct_archive":
        # Correct decision to archive; no financial impact
        financial_impact = 0.0
        notes = "Correct archive — lead correctly filtered out"

    elif impact_type == "manual_no_value":
        # Manual review cost without conversion
        financial_impact = -(lead_value * settings.false_positive_cost_multiplier)
        notes = "Manual review with no conversion — review cost incurred"

    elif impact_type == "pending":
        financial_impact = 0.0
        notes = "Outcome pending — no impact calculated yet"

    else:
        # An "unknown" impact_type means (decision, outcome) is missing from
        # IMPACT_ROUTING_TABLE. Silently defaulting to 0.0 would let it sit in
        # evaluated denominators uncounted — fail loud instead so a routing-table
        # gap is caught immediately rather than quietly skewing rates.
        raise ValueError(
            f"Unmapped decision/outcome combination for lead {lead.get('lead_id')}: "
            f"decision={decision!r}, outcome={outcome!r}. Add it to IMPACT_ROUTING_TABLE."
        )

    return {
        **lead,
        "impact_type": impact_type,
        "financial_impact": round(financial_impact, 2),
        "notes": notes,
    }
