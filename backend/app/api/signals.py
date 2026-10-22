"""Signal processing API routes (Phase 2)."""

from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("/status")
async def get_signals_status():
    """Get status of the Signal Processing Engine."""
    return {"status": "ready", "phase": 2}
