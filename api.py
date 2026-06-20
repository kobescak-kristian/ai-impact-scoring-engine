from fastapi import FastAPI, HTTPException
from typing import List
from models.schemas import ImpactResponse, LeadImpactResponse, LeadRecord
from pipeline.ai_processor import run_impact_pipeline
from pipeline.outcome_handler import compute_lead_impact
from pipeline.impact_evaluator import evaluate_impact
from database.db import get_all_leads, get_lead_by_id, insert_lead, get_lead_count
from pipeline.validator import validate_batch
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AI Impact Scoring Engine",
    description="Turns AI lead qualification decisions into measurable financial impact and actionable recommendations.",
    version="1.0.0",
)


# ── GET /impact ────────────────────────────────────────────────────────────────

@app.get("/impact", response_model=ImpactResponse, summary="Full batch impact analysis")
def get_impact():
    """
    Runs full impact analysis over all stored leads.
    Returns deterministic metrics + AI interpretation + structured recommendations.
    """
    leads = get_all_leads()

    if not leads:
        raise HTTPException(status_code=404, detail="No leads found in database. Load data first via /load.")

    logger.info(f"/impact called — analysing {len(leads)} leads")
    return run_impact_pipeline(leads)


# ── GET /impact/summary ────────────────────────────────────────────────────────

@app.get("/impact/summary", summary="Quick metrics summary — no AI layer")
def get_impact_summary():
    """
    Returns deterministic metrics only. No OpenAI call. Fast and cheap.
    Useful for dashboards or health checks.
    """
    leads = get_all_leads()

    if not leads:
        raise HTTPException(status_code=404, detail="No leads found in database.")

    metrics, _ = evaluate_impact(leads)
    return {"metrics": metrics}


# ── GET /impact/{lead_id} ──────────────────────────────────────────────────────

@app.get("/impact/{lead_id}", response_model=LeadImpactResponse, summary="Per-lead impact detail")
def get_lead_impact(lead_id: str):
    """
    Returns the financial impact classification for a single lead.
    No AI layer — deterministic only.
    """
    lead = get_lead_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")

    enriched = compute_lead_impact(lead)

    return LeadImpactResponse(
        lead_id=enriched["lead_id"],
        decision=enriched["decision"],
        outcome=enriched["outcome"],
        lead_value=enriched["lead_value"],
        confidence_score=enriched["confidence_score"],
        financial_impact=enriched["financial_impact"],
        impact_type=enriched["impact_type"],
        notes=enriched["notes"],
    )


# ── POST /load ─────────────────────────────────────────────────────────────────

@app.post("/load", summary="Load lead records into the database")
def load_leads(records: List[LeadRecord]):
    """
    Accepts a list of lead records, validates, and stores them.
    Use this to seed the database with sample or real data.
    """
    raw = [r.model_dump() for r in records]

    # Normalise datetime to string for SQLite
    for r in raw:
        if r.get("timestamp"):
            r["timestamp"] = r["timestamp"].isoformat()
        if r.get("decision"):
            r["decision"] = r["decision"].value if hasattr(r["decision"], "value") else r["decision"]
        if r.get("outcome"):
            r["outcome"] = r["outcome"].value if hasattr(r["outcome"], "value") else r["outcome"]
        if r.get("customer_type") and hasattr(r["customer_type"], "value"):
            r["customer_type"] = r["customer_type"].value
        if r.get("value_tier") and hasattr(r["value_tier"], "value"):
            r["value_tier"] = r["value_tier"].value

    valid, invalid = validate_batch(raw)

    for lead in valid:
        insert_lead(lead)

    return {
        "loaded": len(valid),
        "rejected": len(invalid),
        "total_in_db": get_lead_count(),
        "validation_errors": invalid if invalid else [],
    }


# ── GET /health ────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
def health():
    return {"status": "ok", "leads_in_db": get_lead_count()}
