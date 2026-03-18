from fastapi import APIRouter

from backend.api.routes.accounts import router as accounts_router
from backend.api.routes.analyze import router as analyze_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.schemas.responses import HealthResponse

router = APIRouter()

router.include_router(analyze_router)
router.include_router(jobs_router)
router.include_router(accounts_router)


@router.get("/health", response_model=HealthResponse, summary="Health check", tags=["System"])
async def health() -> HealthResponse:
    """Returns API health status."""
    return HealthResponse(status="ok", version="1.0.0")
