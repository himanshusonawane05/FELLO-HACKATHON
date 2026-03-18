import logging

from fastapi import APIRouter, HTTPException, Query

from backend.api.schemas.responses import (
    AccountIntelligenceResponse,
    AccountListResponse,
    AccountSummaryResponse,
    BusinessSignalsResponse,
    CompanyProfileResponse,
    IntentScoreResponse,
    LeaderResponse,
    LeadershipProfileResponse,
    PersonaInferenceResponse,
    RecommendedActionResponse,
    SalesPlaybookResponse,
    SignalResponse,
    TechStackResponse,
    TechnologyResponse,
)
from backend.controllers.analysis import analysis_controller

router = APIRouter(prefix="/accounts", tags=["Accounts"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=AccountListResponse,
    summary="List all analyzed accounts",
)
async def list_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AccountListResponse:
    """Return a paginated list of completed account intelligence results."""
    try:
        accounts, total = await analysis_controller.list_accounts(page=page, page_size=page_size)
    except Exception as exc:
        logger.warning("list_accounts failed, returning empty list: %s", exc, exc_info=True)
        return AccountListResponse(accounts=[], total=0, page=page, page_size=page_size)

    summaries = []
    for a in accounts:
        try:
            company = getattr(a, "company", None)
            summaries.append(
                AccountSummaryResponse(
                    account_id=a.id,
                    company_name=company.company_name if company else "Unknown",
                    domain=company.domain if company else None,
                    industry=company.industry if company else None,
                    intent_score=a.intent.intent_score if a.intent else None,
                    confidence_score=a.confidence_score,
                    analyzed_at=a.analyzed_at,
                )
            )
        except Exception as exc:
            logger.warning("Skipping malformed account %s: %s", getattr(a, "id", "?"), exc)
    return AccountListResponse(accounts=summaries, total=total, page=page, page_size=page_size)


@router.get(
    "/{account_id}",
    response_model=AccountIntelligenceResponse,
    summary="Get full account intelligence",
)
async def get_account(account_id: str) -> AccountIntelligenceResponse:
    """Retrieve the complete AI-generated account intelligence."""
    intel = await analysis_controller.get_account(account_id)
    if not intel:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Account not found", "details": None}},
        )

    c = intel.company
    return AccountIntelligenceResponse(
        account_id=intel.id,
        company=CompanyProfileResponse(
            company_name=c.company_name,
            domain=c.domain,
            industry=c.industry,
            company_size_estimate=c.company_size_estimate,
            headquarters=c.headquarters,
            founding_year=c.founding_year,
            description=c.description,
            annual_revenue_range=c.annual_revenue_range,
            confidence_score=c.confidence_score,
            data_sources=c.data_sources,
        ),
        persona=(
            PersonaInferenceResponse(
                likely_role=intel.persona.likely_role,
                department=intel.persona.department,
                seniority_level=intel.persona.seniority_level.value,
                behavioral_signals=intel.persona.behavioral_signals,
                confidence_score=intel.persona.confidence_score,
                reasoning=intel.persona.reasoning,
            )
            if intel.persona else None
        ),
        intent=(
            IntentScoreResponse(
                intent_score=intel.intent.intent_score,
                intent_stage=intel.intent.intent_stage.value,
                signals_detected=intel.intent.signals_detected,
                page_score_breakdown=intel.intent.page_score_breakdown,
                confidence_score=intel.intent.confidence_score,
            )
            if intel.intent else None
        ),
        tech_stack=(
            TechStackResponse(
                technologies=[
                    TechnologyResponse(
                        name=t.name,
                        category=t.category.value,
                        confidence_score=t.confidence_score,
                    )
                    for t in intel.tech_stack.technologies
                ],
                detection_method=intel.tech_stack.detection_method,
                confidence_score=intel.tech_stack.confidence_score,
            )
            if intel.tech_stack else None
        ),
        business_signals=(
            BusinessSignalsResponse(
                signals=[
                    SignalResponse(
                        signal_type=s.signal_type.value,
                        title=s.title,
                        description=s.description,
                        source_url=s.source_url,
                    )
                    for s in intel.business_signals.signals
                ],
                confidence_score=intel.business_signals.confidence_score,
            )
            if intel.business_signals else None
        ),
        leadership=(
            LeadershipProfileResponse(
                leaders=[
                    LeaderResponse(
                        name=l.name,
                        title=l.title,
                        department=l.department,
                        linkedin_url=l.linkedin_url,
                        source_url=l.source_url,
                    )
                    for l in intel.leadership.leaders
                ],
                confidence_score=intel.leadership.confidence_score,
            )
            if intel.leadership else None
        ),
        playbook=(
            SalesPlaybookResponse(
                priority=intel.playbook.priority.value,
                recommended_actions=[
                    RecommendedActionResponse(
                        action=a.action,
                        rationale=a.rationale,
                        priority=a.priority.value,
                    )
                    for a in intel.playbook.recommended_actions
                ],
                talking_points=intel.playbook.talking_points,
                outreach_template=intel.playbook.outreach_template,
            )
            if intel.playbook else None
        ),
        ai_summary=intel.ai_summary,
        analyzed_at=intel.analyzed_at,
        confidence_score=intel.confidence_score,
        reasoning_trace=intel.reasoning_trace,
    )
