from datetime import datetime, timezone

from fastapi import APIRouter

from backend.api.schemas.requests import (
    BatchAnalysisRequest,
    CompanyAnalysisRequest,
    VisitorAnalysisRequest,
)
from backend.api.schemas.responses import (
    AnalysisAcceptedResponse,
    BatchAcceptedResponse,
)
from backend.controllers.analysis import analysis_controller
from backend.domain.company import CompanyInput
from backend.domain.visitor import VisitorSignal

router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post(
    "/visitor",
    response_model=AnalysisAcceptedResponse,
    status_code=202,
    summary="Analyze a visitor signal",
)
async def analyze_visitor(body: VisitorAnalysisRequest) -> AnalysisAcceptedResponse:
    """Submit a visitor signal for AI analysis. Returns job_id for polling."""
    signal = VisitorSignal(
        visitor_id=body.visitor_id,
        ip_address=body.ip_address,
        pages_visited=body.pages_visited,
        time_on_site_seconds=body.time_on_site_seconds,
        visit_count=body.visit_count,
        referral_source=body.referral_source,
        device_type=body.device_type,
        location=body.location,
        timestamps=body.timestamps,
    )
    record = await analysis_controller.analyze_visitor(signal)
    return AnalysisAcceptedResponse(
        job_id=record.job_id,
        status="PENDING",
        analysis_type="visitor",
        message="Visitor analysis started",
        poll_url=f"/api/v1/jobs/{record.job_id}",
        created_at=record.created_at,
    )


@router.post(
    "/company",
    response_model=AnalysisAcceptedResponse,
    status_code=202,
    summary="Analyze a company by name/domain",
)
async def analyze_company(body: CompanyAnalysisRequest) -> AnalysisAcceptedResponse:
    """Submit a company name for AI enrichment. Returns job_id for polling."""
    company = CompanyInput(company_name=body.company_name, domain=body.domain)
    record = await analysis_controller.analyze_company(company)
    return AnalysisAcceptedResponse(
        job_id=record.job_id,
        status="PENDING",
        analysis_type="company",
        message="Company analysis started",
        poll_url=f"/api/v1/jobs/{record.job_id}",
        created_at=record.created_at,
    )


@router.post(
    "/batch",
    response_model=BatchAcceptedResponse,
    status_code=202,
    summary="Batch analyze multiple companies",
)
async def analyze_batch(body: BatchAnalysisRequest) -> BatchAcceptedResponse:
    """Submit multiple companies for concurrent AI enrichment."""
    companies = [CompanyInput(company_name=c.company_name, domain=c.domain) for c in body.companies]
    batch_record, job_ids = await analysis_controller.analyze_batch(companies)
    return BatchAcceptedResponse(
        batch_id=batch_record.job_id,
        job_ids=job_ids,
        status="PENDING",
        analysis_type="batch",
        message=f"Batch analysis started for {len(job_ids)} companies",
        poll_url=f"/api/v1/jobs/{batch_record.job_id}",
        created_at=batch_record.created_at,
        total=len(job_ids),
    )
