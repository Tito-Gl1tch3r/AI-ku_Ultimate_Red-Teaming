from __future__ import annotations

from tracesurface.storage.sqlite.connection import init


def run_report_server(*, host: str, port: int, reload: bool) -> None:
    init()

    import uvicorn

    from tracesurface.server.app import create_app

    if reload:
        uvicorn.run(
            "tracesurface.server.app:create_app",
            host=host,
            port=port,
            reload=True,
            factory=True,
        )
        return

    uvicorn.run(create_app(), host=host, port=port)
