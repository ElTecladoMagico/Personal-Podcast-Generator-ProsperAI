"""Internal dashboard (ADR 0013). Admins are Clerk users with public_metadata.role = "admin"."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app import metrics
from app.auth import require_admin

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
RANGES = (7, 30, 90)  # days, as the dashboard offers them


@router.get("/metrics")
def get_metrics(days: int = 30, include_mock: bool = True) -> dict:
    """Every number of the dashboard, computed now for the last `days` whole UTC days."""
    if days not in RANGES:
        raise HTTPException(422, f"days must be one of {RANGES}")
    return metrics.dashboard(datetime.now(UTC).date(), days, include_mock)
