import json
from typing import List, Tuple
from models.schemas import ImpactMetrics, ImpactAnalysis, Recommendation
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def _build_prompt(metrics: ImpactMetrics) -> str:
    return f"""You are a business intelligence analyst reviewing the financial performance of an AI impact scoring system that evaluates the financial consequences of AI lead routing decisions.

You have been given the following deterministic metrics. Do NOT invent numbers. Only interpret what is provided.

METRICS:
- Total leads evaluated: {metrics.total_leads}
- Revenue generated: €{metrics.total_revenue_generated:,.2f}
- Revenue lost (total): €{metrics.total_revenue_lost:,.2f}
- Missed opportunity value (archived leads that later converted): €{metrics.missed_opportunity_value:,.2f}
- False positive cost (sales effort on non-converting leads): €{metrics.false_positive_cost:,.2f}
- Delayed opportunity cost (manual review delays): €{metrics.delayed_opportunity_value:,.2f}
- Net impact: €{metrics.net_impact:,.2f}
- Conversion rate: {metrics.conversion_rate:.1%}
- False positive rate: {metrics.false_positive_rate:.1%}
- Missed opportunity rate (of archived leads): {metrics.missed_opportunity_rate:.1%}
- Avg confidence score — converted leads: {metrics.avg_confidence_converted}
- Avg confidence score — non-converted leads: {metrics.avg_confidence_not_converted}
- Leads converted: {metrics.converted_count}
- Leads not converted (false positives): {metrics.not_converted_count}
- Archived leads that later converted: {metrics.archived_later_converted_count}
- Manual review leads that converted: {metrics.manual_review_converted_count}

Respond ONLY with a valid JSON object. No explanation outside the JSON. No markdown. No backticks.

The JSON must follow this exact structure:
{{
  "summary": "2-3 sentence plain-English summary of overall system performance and financial outcome",
  "key_issues": ["issue 1", "issue 2", "issue 3"],
  "root_causes": ["cause 1", "cause 2"],
  "recommendations": [
    {{
      "action": "action_slug",
      "from_value": null_or_number,
      "to_value": null_or_number,
      "reason": "why this action is needed",
      "expected_effect": "what will improve",
      "tradeoff": "what may get worse"
    }}
  ]
}}

Rules:
- Identify 2–4 key issues based strictly on the metrics
- Provide 1–3 root causes
- Provide 2–4 concrete recommendations
- Each recommendation must include a specific action, reason, expected effect, and tradeoff
- Where applicable, include from_value and to_value for threshold changes (e.g. confidence score adjustments)
- Be specific and business-focused. Avoid vague statements.
"""


# ── OpenAI Call ────────────────────────────────────────────────────────────────

def _call_openai(metrics: ImpactMetrics) -> Tuple[ImpactAnalysis, List[Recommendation], bool]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_prompt(metrics)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1200,
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        analysis = ImpactAnalysis(
            summary=data["summary"],
            key_issues=data["key_issues"],
            root_causes=data["root_causes"],
            simulated=False,
        )

        recommendations = [
            Recommendation(
                action=r["action"],
                from_value=r.get("from_value"),
                to_value=r.get("to_value"),
                reason=r["reason"],
                expected_effect=r["expected_effect"],
                tradeoff=r["tradeoff"],
            )
            for r in data.get("recommendations", [])
        ]

        logger.info(f"OpenAI analysis complete — {len(recommendations)} recommendations returned")
        return analysis, recommendations, False

    except Exception as e:
        logger.error(f"OpenAI call failed: {e}. Falling back to simulation.")
        return _simulate_analysis(metrics)


# ── Simulation Fallback ────────────────────────────────────────────────────────

def _simulate_analysis(metrics: ImpactMetrics) -> Tuple[ImpactAnalysis, List[Recommendation], bool]:
    """
    Rule-based simulation fallback.
    Produces deterministic analysis from metric thresholds.
    Used when OpenAI is unavailable or USE_SIMULATION_FALLBACK=true.
    """
    logger.info("Using simulation fallback for impact analysis")

    issues = []
    causes = []
    recommendations = []

    # Issue: high false positive rate
    if metrics.false_positive_rate > 0.25:
        issues.append(
            f"High false positive rate ({metrics.false_positive_rate:.1%}) — "
            f"sales team is being sent unqualified leads, costing €{metrics.false_positive_cost:,.0f}"
        )
        causes.append("Confidence threshold may be set too low, passing borderline leads to sales")
        recommendations.append(Recommendation(
            action="increase_confidence_threshold",
            from_value=0.60,
            to_value=0.68,
            reason=f"False positive rate of {metrics.false_positive_rate:.1%} exceeds acceptable limit",
            expected_effect="Fewer unqualified leads sent to sales, reduced wasted effort",
            tradeoff="May increase volume of leads routed to manual review or archived",
        ))

    # Issue: high missed opportunity rate
    if metrics.missed_opportunity_rate > 0.20:
        issues.append(
            f"High missed opportunity rate ({metrics.missed_opportunity_rate:.1%}) — "
            f"€{metrics.missed_opportunity_value:,.0f} in value was archived and lost"
        )
        causes.append("Archive threshold may be too aggressive, filtering out viable leads")
        recommendations.append(Recommendation(
            action="lower_archive_threshold",
            from_value=0.35,
            to_value=0.28,
            reason=f"Missed opportunity rate of {metrics.missed_opportunity_rate:.1%} indicates over-filtering",
            expected_effect="More borderline leads routed to manual review rather than archived",
            tradeoff="Increases manual review volume and associated review costs",
        ))

    # Issue: negative net impact
    if metrics.net_impact < 0:
        issues.append(
            f"Net impact is negative (€{metrics.net_impact:,.0f}) — "
            "the system is generating more costs than revenue"
        )
        causes.append("Combined false positive and missed opportunity costs exceed generated revenue")

    # Issue: low conversion rate
    if metrics.conversion_rate < 0.40:
        issues.append(
            f"Below-target conversion rate ({metrics.conversion_rate:.1%}) — "
            "less than 40% of evaluated leads are converting"
        )

    # Issue: confidence gap between converted and not-converted is small
    conf_gap = metrics.avg_confidence_converted - metrics.avg_confidence_not_converted
    if conf_gap < 0.15:
        issues.append(
            f"Small confidence gap between converted ({metrics.avg_confidence_converted}) "
            f"and non-converted ({metrics.avg_confidence_not_converted}) leads — "
            "threshold is not effectively separating signal from noise"
        )
        recommendations.append(Recommendation(
            action="review_scoring_model",
            from_value=None,
            to_value=None,
            reason="Confidence scores are not sufficiently discriminating between good and bad leads",
            expected_effect="Better separation between qualifying and disqualifying leads",
            tradeoff="Requires retraining or re-calibrating the underlying scoring model",
        ))

    # Issue: delayed conversions present
    if metrics.manual_review_converted_count > 0 and metrics.delayed_opportunity_value > 0:
        recommendations.append(Recommendation(
            action="reduce_manual_review_volume",
            from_value=None,
            to_value=None,
            reason=f"Manual review is causing delays, costing €{metrics.delayed_opportunity_value:,.0f} in delay penalties",
            expected_effect="Faster lead processing, reduced delay cost",
            tradeoff="Requires tighter routing rules to avoid sending low-confidence leads to manual review",
        ))

    if not issues:
        issues.append("System is performing within acceptable parameters")
    if not causes:
        causes.append("No critical root causes identified at current thresholds")

    net_word = "positive" if metrics.net_impact >= 0 else "negative"
    summary = (
        f"The AI lead qualification system processed {metrics.total_leads} leads, "
        f"generating €{metrics.total_revenue_generated:,.0f} in revenue against "
        f"€{metrics.total_revenue_lost:,.0f} in losses, for a {net_word} net impact of "
        f"€{metrics.net_impact:,.0f}. "
        f"Conversion rate stands at {metrics.conversion_rate:.1%} with a false positive rate "
        f"of {metrics.false_positive_rate:.1%}."
    )

    analysis = ImpactAnalysis(
        summary=summary,
        key_issues=issues[:4],
        root_causes=causes[:3],
        simulated=True,
    )

    return analysis, recommendations, True


# ── Public Interface ───────────────────────────────────────────────────────────

def analyze_impact(metrics: ImpactMetrics) -> Tuple[ImpactAnalysis, List[Recommendation]]:
    """
    Entry point for AI analysis layer.
    Uses OpenAI if configured; falls back to simulation otherwise.
    """
    use_simulation = (
        settings.use_simulation_fallback
        or not settings.openai_api_key
    )

    if use_simulation:
        logger.info("Simulation mode active — skipping OpenAI call")
        analysis, recommendations, _ = _simulate_analysis(metrics)
    else:
        analysis, recommendations, _ = _call_openai(metrics)

    return analysis, recommendations
