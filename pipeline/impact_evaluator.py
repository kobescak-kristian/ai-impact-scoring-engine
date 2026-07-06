from typing import List
from config.settings import settings
from models.schemas import ImpactMetrics
from pipeline.outcome_handler import compute_lead_impact
from utils.logger import get_logger

logger = get_logger(__name__)


def evaluate_impact(leads: List[dict]) -> tuple[ImpactMetrics, List[dict]]:
    """
    Core deterministic metrics engine.
    No LLM. No interpretation. Numbers only.

    Returns:
        - ImpactMetrics object
        - List of enriched lead dicts (each with impact_type, financial_impact, notes)
    """
    if not leads:
        logger.warning("evaluate_impact called with empty lead list")
        return _empty_metrics(), []

    enriched = [compute_lead_impact(lead) for lead in leads]

    # ── Revenue generated ──────────────────────────────────────────────────────
    revenue_leads = [l for l in enriched if l["impact_type"] == "revenue_generated"]
    total_revenue_generated = sum(l["lead_value"] for l in revenue_leads)

    # Delayed conversion: revenue realised but penalised — track separately
    delayed_leads = [l for l in enriched if l["impact_type"] == "delayed_conversion"]
    delayed_opportunity_value = sum(
        l["lead_value"] * settings.delayed_conversion_penalty for l in delayed_leads
    )
    # Delayed revenue enters generated at gross lead_value — the penalty is
    # itemized once in delayed_opportunity_value (total_revenue_lost), not
    # baked into both figures. Net impact then reconciles with the per-lead
    # financial_impact (lead_value * (1 - penalty)) computed in outcome_handler.
    total_revenue_generated += sum(l["lead_value"] for l in delayed_leads)

    # ── Revenue lost ───────────────────────────────────────────────────────────
    missed_leads = [l for l in enriched if l["impact_type"] == "missed_opportunity"]
    missed_opportunity_value = sum(
        l["lead_value"] * settings.missed_opportunity_multiplier for l in missed_leads
    )

    fp_leads = [l for l in enriched if l["impact_type"] == "false_positive"]
    manual_no_value_leads = [l for l in enriched if l["impact_type"] == "manual_no_value"]
    false_positive_cost = abs(sum(l["financial_impact"] for l in fp_leads + manual_no_value_leads))

    total_revenue_lost = missed_opportunity_value + false_positive_cost + delayed_opportunity_value

    # ── Net impact ─────────────────────────────────────────────────────────────
    net_impact = total_revenue_generated - total_revenue_lost

    # ── Supporting ratios ──────────────────────────────────────────────────────
    total = len(enriched)
    pending = [l for l in enriched if l["impact_type"] == "pending"]
    evaluated = [l for l in enriched if l["impact_type"] != "pending"]

    converted_types = {"revenue_generated", "delayed_conversion"}
    converted = [l for l in evaluated if l["impact_type"] in converted_types]
    not_converted = [l for l in evaluated if l["impact_type"] == "false_positive"]

    conversion_rate = len(converted) / len(evaluated) if evaluated else 0.0

    sent_to_sales = [l for l in evaluated if l["decision"] == "send_to_sales"]
    false_positive_rate = (
        len(fp_leads) / len(sent_to_sales) if sent_to_sales else 0.0
    )

    archived = [l for l in evaluated if l["decision"] == "archived"]
    missed_rate = (
        len(missed_leads) / len(archived) if archived else 0.0
    )

    # Avg confidence by conversion result
    conv_scores = [l["confidence_score"] for l in converted if l.get("confidence_score") is not None]
    not_conv_scores = [l["confidence_score"] for l in not_converted if l.get("confidence_score") is not None]

    avg_conf_converted = round(sum(conv_scores) / len(conv_scores), 3) if conv_scores else 0.0
    avg_conf_not_converted = round(sum(not_conv_scores) / len(not_conv_scores), 3) if not_conv_scores else 0.0

    metrics = ImpactMetrics(
        total_leads=total,
        total_revenue_generated=round(total_revenue_generated, 2),
        total_revenue_lost=round(total_revenue_lost, 2),
        missed_opportunity_value=round(missed_opportunity_value, 2),
        false_positive_cost=round(false_positive_cost, 2),
        delayed_opportunity_value=round(delayed_opportunity_value, 2),
        net_impact=round(net_impact, 2),
        conversion_rate=round(conversion_rate, 3),
        false_positive_rate=round(false_positive_rate, 3),
        missed_opportunity_rate=round(missed_rate, 3),
        avg_confidence_converted=avg_conf_converted,
        avg_confidence_not_converted=avg_conf_not_converted,
        converted_count=len(converted),
        not_converted_count=len(not_converted),
        archived_later_converted_count=len(missed_leads),
        manual_review_converted_count=len(
            [l for l in enriched if l["decision"] == "manual_review"
             and l["impact_type"] in converted_types]
        ),
    )

    logger.info(
        f"Impact evaluated: {total} leads | net_impact={metrics.net_impact} | "
        f"conversion_rate={metrics.conversion_rate}"
    )

    return metrics, enriched


def _empty_metrics() -> ImpactMetrics:
    return ImpactMetrics(
        total_leads=0,
        total_revenue_generated=0.0,
        total_revenue_lost=0.0,
        missed_opportunity_value=0.0,
        false_positive_cost=0.0,
        delayed_opportunity_value=0.0,
        net_impact=0.0,
        conversion_rate=0.0,
        false_positive_rate=0.0,
        missed_opportunity_rate=0.0,
        avg_confidence_converted=0.0,
        avg_confidence_not_converted=0.0,
        converted_count=0,
        not_converted_count=0,
        archived_later_converted_count=0,
        manual_review_converted_count=0,
    )
