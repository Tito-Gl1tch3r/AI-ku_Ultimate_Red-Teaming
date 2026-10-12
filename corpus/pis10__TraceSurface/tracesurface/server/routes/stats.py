from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import tracesurface.storage.sqlite.queries as queries
from tracesurface.storage.commands import PurgeAll, PurgeTarget
from tracesurface.storage.sqlite.writer import apply_command

router = APIRouter()


@router.get("/api/health")
def health():
    return {"ok": True}


@router.get("/api/stats")
def stats():
    return queries.query_stats()


@router.get("/api/domains")
def domains(limit: int = Query(1000, ge=1, le=10000)):
    return {"items": queries.query_domains(limit=limit)}


@router.get("/api/targets")
def targets():
    return {"items": queries.query_targets()}


@router.delete("/api/data")
def purge(target_url: str | None = None, all: bool = False):
    if target_url and all:
        raise HTTPException(400, "target_url 与 all=1 只能指定一个")

    if target_url:
        counts = apply_command(PurgeTarget(target_url))
        return {
            "ok": True,
            "scope": "target",
            "target_url": target_url,
            "counts": counts,
        }

    if all:
        return {"ok": True, "scope": "all", "counts": apply_command(PurgeAll())}

    raise HTTPException(400, "需指定 target_url 或 all=1")
