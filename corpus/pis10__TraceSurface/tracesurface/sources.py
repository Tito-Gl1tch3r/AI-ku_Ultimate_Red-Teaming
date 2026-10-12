from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from tracesurface.models import SourceRef


def _home() -> Path:
    base = os.environ.get("TRACESURFACE_HOME")
    home = Path(base).expanduser() if base else Path.home() / ".tracesurface"
    home.mkdir(parents=True, exist_ok=True)
    return home


def source_root() -> Path:
    root = _home() / "sources"
    root.mkdir(parents=True, exist_ok=True)
    return root


def source_scan_dir(scan_id: int | str) -> Path:
    return source_root() / str(scan_id)


def store_source(
    scope: int | str,
    kind: str,
    url: str,
    text: str,
) -> SourceRef:
    root = source_scan_dir(scope) / kind
    root.mkdir(parents=True, exist_ok=True)

    data = (text or "").encode("utf-8", errors="replace")

    digest = hashlib.sha256(data).hexdigest()
    path = root / f"{digest}.txt"

    if not path.exists():
        tmp = path.with_suffix(f".{uuid4().hex}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return SourceRef(
        url=url,
        path=str(path),
        size=len(data),
        sha256=digest,
    )


def load_source(ref: SourceRef) -> str:
    return Path(ref.path).read_text(encoding="utf-8", errors="replace")


def iter_sources(refs: Mapping[str, SourceRef]):
    for url, ref in refs.items():
        yield url, load_source(ref)


def remove_scan_sources(scan_id: int | str) -> int:
    path = source_scan_dir(scan_id)
    if not path.exists():
        return 0

    count = sum(1 for p in path.rglob("*") if p.is_file())
    shutil.rmtree(path, ignore_errors=True)
    return count


def remove_all_sources() -> int:
    root = source_root()

    count = sum(1 for p in root.rglob("*") if p.is_file()) if root.exists() else 0
    shutil.rmtree(root, ignore_errors=True)
    return count
