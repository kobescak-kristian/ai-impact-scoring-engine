from typing import Tuple
from utils.logger import get_logger

logger = get_logger(__name__)

# Decision + Outcome → Impact classification
IMPACT_ROUTING_TABLE = {
    ("send_to_sales",  "converted"):           "revenue_generated",
    ("send_to_sales",  "not_converted"):        "false_positive",
    ("send_to_sales",  "later_converted"):      "revenue_generated",   # rare but valid
    ("send_to_sales",  "converted_delayed"):    "delayed_conversion",
    ("archived",       "not_converted"):        "correct_archive",
    ("archived",       "later_converted"):      "missed_opportunity",
    ("archived",       "converted"):            "missed_opportunity",
    ("archived",       "converted_delayed"):    "missed_opportunity",
    ("manual_review",  "converted"):            "revenue_generated",
    ("manual_review",  "not_converted"):        "manual_no_value",
    ("manual_review",  "converted_delayed"):    "delayed_conversion",
    ("manual_review",  "later_converted"):      "delayed_conversion",
    ("send_to_sales",  "pending"):              "pending",
    ("archived",       "pending"):              "pending",
    ("manual_review",  "pending"):              "pending",
}


def route_lead(decision: str, outcome: str) -> str:
    """
    Return the impact classification for a given decision + outcome pair.
    Falls back to 'unknown' if the combination is not mapped.
    """
    key = (decision, outcome)
    impact_type = IMPACT_ROUTING_TABLE.get(key, "unknown")

    if impact_type == "unknown":
        logger.warning(f"Unmapped decision/outcome combination: {key}")

    return impact_type
