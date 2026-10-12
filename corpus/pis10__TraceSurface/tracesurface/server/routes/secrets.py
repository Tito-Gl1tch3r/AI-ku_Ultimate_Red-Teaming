from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import tracesurface.storage.sqlite.queries as queries

router = APIRouter()


@router.get("/api/secrets/facets")
def secrets_facets(target: str = ""):
    return queries.secret_facets(target=target)


@router.get("/api/secrets")
def secrets_list(
    target: str = "",
    groups: str = "",
    sensitive: bool | None = None,
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
):
    group_list = [g for g in groups.split(",") if g] or None
    total, items = queries.query_secrets(
        target=target,
        groups=group_list,
        sensitive=sensitive,
        q=q,
        offset=offset,
        limit=limit,
    )
    return {"total": total, "items": items}


@router.get("/api/secrets/{secret_id}")
def secret_detail(secret_id: int):
    secret = queries.get_secret(secret_id)
    if not secret:
        raise HTTPException(404, "secret not found")
    return secret
