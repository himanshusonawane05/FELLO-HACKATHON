from fastapi import APIRouter, HTTPException

from backend.api.schemas.responses import JobStatusResponse
from backend.controllers.analysis import analysis_controller

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll job status",
)
async def get_job(job_id: str) -> JobStatusResponse:
    """Poll a job for its current status and progress."""
    record = await analysis_controller.get_job_status(job_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Job not found", "details": None}},
        )
    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status.value,
        progress=record.progress,
        current_step=record.current_step,
        result_id=record.result_id,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
