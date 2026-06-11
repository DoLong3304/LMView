"""AI action catalog endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_current_user
from ai_service.actions.registry import get_action_catalog

router = APIRouter()


@router.get("/actions/catalog")
async def actions_catalog(current_user: dict = Depends(get_current_user)):
    """Return reusable function schemas for AI/debug action calls."""
    return get_action_catalog()

