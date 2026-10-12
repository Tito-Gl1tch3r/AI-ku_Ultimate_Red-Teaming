import asyncio
from types import SimpleNamespace

from models import ScanConfig, ScanStatus
from server.routers import scans_service


class _RepoStub:
    def __init__(self):
        self.session_state = {"status": ScanStatus.RUNNING.value}
        self.updated = []
        self.events = []
        self.deleted_sessions = []
        self.merged_sessions = []
        self.latest_session_id = None
        self.current_slugs = []
        self.previous_slugs = []

    def update_session_status(
        self,
        session_id,
        status,
        total_found=None,
        high_risk_count=None,
        error_message=None,
    ):
        self.updated.append(
            {
                "session_id": session_id,
                "status": status.value if hasattr(status, "value") else status,
                "total_found": total_found,
                "high_risk_count": high_risk_count,
                "error_message": error_message,
            }
        )
        self.session_state = {"status": status.value if hasattr(status, "value") else status}

    def get_session(self, session_id):
        del session_id
        return self.session_state

    def get_latest_session_by_config(self, config_dict, exclude_id):
        del config_dict, exclude_id
        return self.latest_session_id

    def get_result_slugs(self, session_id):
        if session_id == 100:
            return list(self.current_slugs)
        if session_id == 99:
            return list(self.previous_slugs)
        return []

    def delete_session(self, session_id):
        self.deleted_sessions.append(session_id)
        return True

    def mark_session_merged(self, session_id):
        self.merged_sessions.append(session_id)


def _build_config(themes=False):
    return ScanConfig(
        pages=1,
        limit=1,
        min_installs=0,
        max_installs=0,
        sort="popular",
        smart=False,
        abandoned=False,
        user_facing=False,
        themes=themes,
        min_days=0,
        max_days=3650,
        aggressive=False,
    )


async def _capture_event(session_id, payload, sink):
    sink.append((session_id, payload))


def test_finalize_scan_completion_marks_cancelled(monkeypatch):
    repo = _RepoStub()
    repo.session_state = {"status": ScanStatus.CANCELLED.value}
    events = []

    monkeypatch.setattr(
        scans_service,
        "_send_session_event",
        lambda session_id, payload: _capture_event(session_id, payload, events),
    )

    completed = asyncio.run(
        scans_service._finalize_scan_completion(
            session_id=100,
            config=_build_config(),
            repo=repo,
            found_count=3,
            high_risk_count=1,
        )
    )

    assert completed is False
    assert repo.updated == [
        {
            "session_id": 100,
            "status": ScanStatus.CANCELLED.value,
            "total_found": 3,
            "high_risk_count": 1,
            "error_message": None,
        }
    ]
    assert events == [
        (
            100,
            {
                "type": "cancelled",
                "session_id": 100,
                "total_found": 3,
                "high_risk_count": 1,
            },
        )
    ]


def test_finalize_scan_completion_deduplicates_identical_results(monkeypatch):
    repo = _RepoStub()
    repo.latest_session_id = 99
    repo.current_slugs = ["akismet", "seo-pack"]
    repo.previous_slugs = ["seo-pack", "akismet"]
    events = []

    monkeypatch.setattr(
        scans_service,
        "_send_session_event",
        lambda session_id, payload: _capture_event(session_id, payload, events),
    )

    completed = asyncio.run(
        scans_service._finalize_scan_completion(
            session_id=100,
            config=_build_config(),
            repo=repo,
            found_count=2,
            high_risk_count=1,
        )
    )

    assert completed is False
    assert repo.updated == [
        {
            "session_id": 100,
            "status": ScanStatus.COMPLETED.value,
            "total_found": 2,
            "high_risk_count": 1,
            "error_message": None,
        }
    ]
    assert repo.deleted_sessions == [100]
    assert repo.merged_sessions == [99]
    assert events[-1] == (
        100,
        {
            "type": "deduplicated",
            "original_session_id": 99,
            "message": "Results identical to previous scan. Merged.",
        },
    )


def test_finalize_scan_completion_emits_complete_when_not_cancelled_or_dedup(monkeypatch):
    repo = _RepoStub()
    events = []

    monkeypatch.setattr(
        scans_service,
        "_send_session_event",
        lambda session_id, payload: _capture_event(session_id, payload, events),
    )

    completed = asyncio.run(
        scans_service._finalize_scan_completion(
            session_id=100,
            config=_build_config(),
            repo=repo,
            found_count=5,
            high_risk_count=2,
        )
    )

    assert completed is True
    assert repo.updated == [
        {
            "session_id": 100,
            "status": ScanStatus.COMPLETED.value,
            "total_found": 5,
            "high_risk_count": 2,
            "error_message": None,
        }
    ]
    assert events == [
        (
            100,
            {
                "type": "complete",
                "session_id": 100,
                "total_found": 5,
                "high_risk_count": 2,
            },
        )
    ]


def test_run_scan_task_marks_failed_on_exception(monkeypatch):
    repo = _RepoStub()
    events = []

    async def _boom(**kwargs):
        del kwargs
        raise RuntimeError("scanner exploded")

    monkeypatch.setattr(scans_service, "_run_scan_mode", _boom)
    monkeypatch.setattr(
        scans_service,
        "_send_session_event",
        lambda session_id, payload: _capture_event(session_id, payload, events),
    )

    asyncio.run(scans_service.run_scan_task(123, _build_config(), repo))

    assert repo.updated[0]["status"] == ScanStatus.RUNNING.value
    assert repo.updated[1] == {
        "session_id": 123,
        "status": ScanStatus.FAILED.value,
        "total_found": None,
        "high_risk_count": None,
        "error_message": "scanner exploded",
    }
    assert events[0] == (123, {"type": "start", "session_id": 123})
    assert events[1] == (123, {"type": "error", "message": "scanner exploded"})
    assert 123 not in scans_service.active_scans


def test_create_scan_session_enqueues_background_task():
    class _BackgroundStub:
        def __init__(self):
            self.calls = []

        def add_task(self, func, *args):
            self.calls.append((func, args))

    class _CreateRepo:
        def create_session(self, config):
            assert isinstance(config, ScanConfig)
            return 321

    background = _BackgroundStub()
    request = SimpleNamespace(
        pages=5,
        limit=25,
        min_installs=100,
        max_installs=1000000,
        sort="updated",
        smart=True,
        abandoned=False,
        user_facing=True,
        themes=False,
        min_days=0,
        max_days=3650,
        aggressive=False,
    )

    repo = _CreateRepo()
    response = scans_service.create_scan_session(
        repo=repo,
        scan_request=request,
        background_tasks=background,
    )

    assert response == {
        "session_id": 321,
        "status": "started",
        "websocket_url": "/ws/scans/321",
    }

    assert len(background.calls) == 1
    func, args = background.calls[0]
    assert func is scans_service.run_scan_task
    assert args[0] == 321
    assert args[1] == scans_service.build_scan_config(request)
    assert args[2] is repo
