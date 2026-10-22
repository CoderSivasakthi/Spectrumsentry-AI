"""Experiment history API routes."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.database.repository import ExperimentRepository
from backend.app.schemas.experiment import ExperimentSummary

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.get("/", response_model=List[ExperimentSummary])
async def list_experiments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retrieve list of saved experiments from SQLite."""
    repo = ExperimentRepository(db)
    return repo.get_all(skip=skip, limit=limit)
