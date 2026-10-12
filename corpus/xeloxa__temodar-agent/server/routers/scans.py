"""
Scans Router
"""

from fastapi import APIRouter, BackgroundTasks, Request

from database.repository import ScanRepository
from server.limiter import limiter
from server.routers.scans_service import (
    create_scan_session,
    delete_scan_session,
    get_scan_session,
    get_scan_session_results,
    list_scan_sessions,
)
from server.schemas import ScanRequest

router = APIRouter(prefix="/api/scans", tags=["scans"])
repo = ScanRepository()


@router.get("")
@limiter.limit("10000/minute")
async def list_scans(request: Request, limit: int = 50):
    """List all scan sessions."""
    return list_scan_sessions(repo=repo, limit=limit)


@router.post("")
@limiter.limit("5000/minute")
async def create_scan(
    request: Request, scan_request: ScanRequest, background_tasks: BackgroundTasks
):
    """Create and start a new scan."""
    return create_scan_session(
        repo=repo,
        scan_request=scan_request,
        background_tasks=background_tasks,
    )


@router.get("/{session_id}")
async def get_scan(session_id: int):
    """Get scan session details."""
    return get_scan_session(repo=repo, session_id=session_id)


@router.get("/{session_id}/results")
async def get_scan_results(
    session_id: int,
    sort_by: str = "score",
    sort_order: str = "desc",
    limit: int = 100,
):
    """Get results for a scan session."""
    return get_scan_session_results(
        repo=repo,
        session_id=session_id,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
    )


@router.delete("/{session_id}")
async def delete_scan(session_id: int):
    """Delete a scan session."""
    return delete_scan_session(repo=repo, session_id=session_id)
