"""Tour registry — list and resolve available guided tours.

Provides helpers for frontend and backend to discover tours
by id, list all tours, and resolve tour steps.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ai_service.tours.tour_templates import (
    AVAILABLE_TOURS,
    TourTemplate,
)


def get_tour(tour_id: str) -> Optional[TourTemplate]:
    """Resolve a tour by its ID."""
    return AVAILABLE_TOURS.get(tour_id)


def list_tours() -> List[Dict[str, Any]]:
    """Return a list of all available tours (metadata only, no steps)."""
    return [
        {
            "tour_id": t.tour_id,
            "title": t.title,
            "description": t.description,
            "step_count": len(t.steps),
        }
        for t in AVAILABLE_TOURS.values()
    ]


def get_tour_steps(tour_id: str) -> Optional[List[Dict[str, Any]]]:
    """Resolve a tour's steps as dicts (for JSON serialization)."""
    tour = get_tour(tour_id)
    if tour is None:
        return None
    return [
        {
            "action": step.action,
            "explanation": step.explanation,
            "requires_approval": step.requires_approval,
            "target_selector": step.target_selector,
        }
        for step in tour.steps
    ]
