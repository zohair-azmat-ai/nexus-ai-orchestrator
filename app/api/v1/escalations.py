from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import require_reviewer_or_admin
from app.db import crud
from app.db.models.user import User
from app.db.postgres import get_db
from app.schemas.common import ErrorResponse
from app.schemas.escalations import (
    EscalationAssignRequest,
    EscalationCaseListResponse,
    EscalationCaseResponse,
    EscalationNoteCreateRequest,
    EscalationNoteListResponse,
    EscalationNoteResponse,
    EscalationStatusUpdateRequest,
)
from app.services.escalations.manager import EscalationWorkflowError, escalation_workflow

router = APIRouter()


def _case_to_response(case) -> EscalationCaseResponse:
    return EscalationCaseResponse(
        case_id=case.id,
        conversation_id=case.conversation_id,
        trace_id=case.trace_id,
        user_id=case.user_id,
        escalation_reason=case.escalation_reason,
        severity=case.severity,
        status=case.status,
        assigned_to=case.assigned_to,
        latest_agent=case.latest_agent,
        latest_summary=case.latest_summary,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
    )


def _note_to_response(note) -> EscalationNoteResponse:
    return EscalationNoteResponse(
        note_id=note.id,
        case_id=note.case_id,
        author=note.author,
        note_type=note.note_type,
        content=note.content,
        created_at=note.created_at.isoformat(),
    )


@router.get("/escalations", response_model=EscalationCaseListResponse, tags=["Escalations"])
async def list_escalations(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationCaseListResponse:
    cases = await crud.list_escalation_cases(
        db,
        limit=limit,
        status=status,
        severity=severity,
        assigned_to=assigned_to,
    )
    return EscalationCaseListResponse(cases=[_case_to_response(case) for case in cases], total=len(cases))


@router.get(
    "/escalations/{case_id}",
    response_model=EscalationCaseResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Escalations"],
)
async def get_escalation(
    case_id: str,
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationCaseResponse:
    case = await crud.get_escalation_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Escalation case {case_id!r} not found")
    return _case_to_response(case)


@router.post(
    "/escalations/{case_id}/assign",
    response_model=EscalationCaseResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Escalations"],
)
async def assign_escalation(
    case_id: str,
    request: EscalationAssignRequest,
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationCaseResponse:
    try:
        case = await escalation_workflow.assign_case(
            db,
            case_id=case_id,
            assigned_to=request.assigned_to,
            actor=request.actor,
            move_to_in_review=request.move_to_in_review,
        )
    except EscalationWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if case is None:
        raise HTTPException(status_code=404, detail=f"Escalation case {case_id!r} not found")
    await db.commit()
    return _case_to_response(case)


@router.post(
    "/escalations/{case_id}/status",
    response_model=EscalationCaseResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Escalations"],
)
async def update_escalation_status(
    case_id: str,
    request: EscalationStatusUpdateRequest,
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationCaseResponse:
    try:
        case = await escalation_workflow.update_status(
            db,
            case_id=case_id,
            new_status=request.status,
            actor=request.actor,
        )
    except EscalationWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if case is None:
        raise HTTPException(status_code=404, detail=f"Escalation case {case_id!r} not found")
    await db.commit()
    return _case_to_response(case)


@router.post(
    "/escalations/{case_id}/notes",
    response_model=EscalationNoteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Escalations"],
)
async def add_escalation_note(
    case_id: str,
    request: EscalationNoteCreateRequest,
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationNoteResponse:
    try:
        note = await escalation_workflow.add_note(
            db,
            case_id=case_id,
            author=request.author,
            note_type=request.note_type,
            content=request.content,
        )
    except EscalationWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if note is None:
        raise HTTPException(status_code=404, detail=f"Escalation case {case_id!r} not found")
    await db.commit()
    return _note_to_response(note)


@router.get(
    "/escalations/{case_id}/notes",
    response_model=EscalationNoteListResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Escalations"],
)
async def list_escalation_notes(
    case_id: str,
    current_user: User = Depends(require_reviewer_or_admin),
    db: AsyncSession = Depends(get_db),
) -> EscalationNoteListResponse:
    case = await crud.get_escalation_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Escalation case {case_id!r} not found")
    notes = await crud.list_escalation_notes(db, case_id)
    return EscalationNoteListResponse(notes=[_note_to_response(note) for note in notes], total=len(notes))
