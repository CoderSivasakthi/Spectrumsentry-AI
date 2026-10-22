"""Main API routes aggregator."""

from fastapi import APIRouter

from .ai import router as ai_router
from .communication import router as communication_router
from .decision import router as decision_router
from .experiments import router as experiments_router
from .monitoring import router as monitoring_router
from .signals import router as signals_router

api_router = APIRouter(prefix="/api")

api_router.include_router(signals_router)
api_router.include_router(ai_router)
api_router.include_router(monitoring_router)
api_router.include_router(communication_router)
api_router.include_router(decision_router)
api_router.include_router(experiments_router)


