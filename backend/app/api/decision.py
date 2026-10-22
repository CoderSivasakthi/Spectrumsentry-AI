"""FastAPI Decision Engine API routes (Phase 6).

Provides endpoints for evidence evaluation, live latest assessment, rule inspection,
and historical decision retrieval.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.database.repository import DecisionRepository
from backend.app.decision.engine import decision_engine
from backend.app.schemas.decision import (
    DecisionInput,
    DecisionResult,
    DecisionRuleInfo,
)

router = APIRouter(prefix="/decision", tags=["Decision Engine"])


@router.post(
    "/evaluate",
    response_model=DecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate cross-domain evidence",
    description="Evaluates combined signal/AI and communication evidence, executes deterministic rules, and returns explainable decision.",
)
async def evaluate_evidence(
    input_evidence: DecisionInput,
    persist: bool = Query(True, description="Whether to persist decision record in database"),
    db: Session = Depends(get_db),
) -> DecisionResult:
    """Evaluate explicit evidence payload."""
    try:
        return decision_engine.evaluate(input_evidence, db=db, persist=persist)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decision evaluation failed: {str(exc)}",
        ) from exc


@router.get(
    "/latest",
    response_model=DecisionResult,
    summary="Get latest unified decision assessment",
    description="Gathers current active communication telemetry and latest signal experiment to produce real-time decision.",
)
async def get_latest_decision(
    session_id: Optional[str] = Query(None, description="Optional target communication session ID"),
    experiment_id: Optional[str] = Query(None, description="Optional target signal experiment ID"),
    persist: bool = Query(True, description="Whether to persist decision record"),
    db: Session = Depends(get_db),
) -> DecisionResult:
    """Evaluate current live system state."""
    try:
        return decision_engine.evaluate_from_latest(
            db=db,
            session_id=session_id,
            experiment_id=experiment_id,
            persist=persist,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to evaluate latest decision: {str(exc)}",
        ) from exc


@router.get(
    "/rules",
    response_model=List[DecisionRuleInfo],
    summary="Inspect active decision rules",
    description="Returns all registered decision rules and their priority rankings for full transparency.",
)
async def list_rules() -> List[DecisionRuleInfo]:
    """Return all active decision rules."""
    return decision_engine.get_active_rules()


@router.get(
    "/history",
    response_model=List[DecisionResult],
    summary="Get decision evaluation history",
    description="Returns historical decision records stored in SQLite.",
)
async def get_decision_history(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to fetch"),
    db: Session = Depends(get_db),
) -> List[DecisionResult]:
    """Retrieve historical decision records."""
    repo = DecisionRepository(db)
    records = repo.get_all(skip=skip, limit=limit)
    return [DecisionResult.model_validate(r) for r in records]
