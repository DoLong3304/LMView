"""
Tour Plan API endpoints.

Persistence and replay for Interact mode guided analysis tours.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth_dependencies import get_current_user
from backend.core.postgres import get_pg_pool

router = APIRouter(tags=["ai-tours"])


@router.post("/save")
async def save_tour_plan(
    plan_data: dict,
    user: dict = Depends(get_current_user),
    pool=Depends(get_pg_pool),
):
    """Persist a completed tour plan for later replay."""
    session_id = plan_data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tour_plans (id, session_id, tour_id, title, summary, chart_snapshot, steps, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, 'completed', $8, $8)
            """,
            plan_id,
            session_id,
            plan_data.get("tour_id", "custom"),
            plan_data.get("title", "Guided Analysis"),
            plan_data.get("summary"),
            plan_data.get("chart_snapshot"),
            plan_data.get("steps", "[]"),
            now,
        )
    return {"plan_id": plan_id, "status": "saved"}


@router.get("/history/{session_id}")
async def get_tour_history(
    session_id: str,
    user: dict = Depends(get_current_user),
    pool=Depends(get_pg_pool),
):
    """List tours for a session."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, tour_id, title, summary, status, created_at, completed_at
            FROM tour_plans
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            session_id,
        )
    return [
        {
            "id": r["id"],
            "tour_id": r["tour_id"],
            "title": r["title"],
            "summary": r["summary"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
        }
        for r in rows
    ]


@router.get("/{plan_id}")
async def get_tour_plan(
    plan_id: str,
    user: dict = Depends(get_current_user),
    pool=Depends(get_pg_pool),
):
    """Get full tour plan with steps for replay."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tour_plans WHERE id = $1",
            plan_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Tour plan not found")
    return {
        "id": row["id"],
        "tour_id": row["tour_id"],
        "title": row["title"],
        "summary": row["summary"],
        "steps": row["steps"],
        "chart_snapshot": row["chart_snapshot"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }
