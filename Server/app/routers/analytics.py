"""
PURPOSE:
Provides dashboard analytics aggregates and period-based usage stats.

API ENDPOINTS OWNED:
- GET /analytics/dashboard

API ENDPOINTS USED:
- None (this module defines endpoints).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database import engine_tools
from app.services import terms_service

router = APIRouter()


def _resolve_period_dates(period: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    if period == "1_month":
        return now - timedelta(days=30), now

    term = terms_service.get_term_by_id(period)
    if not term:
        raise HTTPException(status_code=400, detail=f"Unknown period '{period}'")

    try:
        start_date = datetime.strptime(term["start"], "%Y-%m-%d")
        end_date = datetime.strptime(term["end"], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid term date format in terms.json") from exc

    return start_date, end_date


@router.get("/analytics/dashboard")
async def get_dashboard_analytics(period: str = "1_month"):
    with engine_tools.connect() as conn:
        start_date, end_date = _resolve_period_dates(period)

        params = {"start_date": start_date, "end_date": end_date}
        
        total_tools = conn.execute(text("SELECT COUNT(*) FROM tools")).scalar()
        current_borrowed = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE return_timestamp IS NULL")
        ).scalar()
        current_overdue = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE return_timestamp IS NULL AND desired_return_date < NOW()")
        ).scalar()

        period_checkouts = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE checkout_timestamp >= :start_date AND checkout_timestamp <= :end_date"),
            params
        ).scalar()

        top_tools_result = conn.execute(
            text("""
                SELECT t.tool_name, COUNT(tr.tool_id) as usage_count
                FROM transactions tr
                JOIN tools t ON tr.tool_id = t.tool_id
                WHERE tr.checkout_timestamp >= :start_date AND tr.checkout_timestamp <= :end_date
                GROUP BY tr.tool_id, t.tool_name
                ORDER BY usage_count DESC
                LIMIT 10
            """),
            params
        ).fetchall()
        
        top_tools = [{"name": row.tool_name, "uses": row.usage_count} for row in top_tools_result]

        return {
            "live_stats": {
                "total_tools": total_tools,
                "current_borrowed": current_borrowed,
                "current_overdue": current_overdue,
            },
            "period_stats": {
                "checkouts": period_checkouts,
                "top_tools": top_tools,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
