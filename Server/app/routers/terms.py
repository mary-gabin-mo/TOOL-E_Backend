"""
PURPOSE:
Exposes term configuration endpoints used by dashboard/report filtering.

API ENDPOINTS OWNED:
- GET /terms
- PUT /terms
"""

from fastapi import APIRouter, HTTPException

from app.models import TermListPayload, TermListResponse
from app.services import terms_service

router = APIRouter()


@router.get("/terms", response_model=TermListResponse)
async def get_terms_route():
    try:
        terms = terms_service.get_terms()
        return {"terms": terms}
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/terms", response_model=TermListResponse)
async def set_terms_route(payload: TermListPayload):
    try:
        terms = terms_service.set_terms([term.dict() for term in payload.terms])
        return {"terms": terms}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
