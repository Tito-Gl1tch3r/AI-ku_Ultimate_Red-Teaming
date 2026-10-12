import asyncio
import json
from pathlib import Path

from bladerecon.modules import advanced


def test_historical_url_normalization_keeps_in_scope_urls() -> None:
    assert advanced._normalize_historical_url("HTTPS://API.Example.com//api/v1/users?id=1", "example.com") == "https://api.example.com/api/v1/users?id=1"
    assert advanced._normalize_historical_url("https://evil.test/api", "example.com") == ""


def test_historical_url_normalization_skips_malformed_ipv6_url() -> None:
    assert advanced._normalize_historical_url("https://[2001:db8::1/api", "example.com") == ""


def test_historical_correlation_detects_removed_legacy_endpoint(tmp_path: Path) -> None:
    target = tmp_path / "example.com"
    (target / "endpoints").mkdir(parents=True)
    (target / "historical").mkdir()
    (target / "endpoints" / "endpoints.json").write_text(
        json.dumps([{"endpoint": "https://example.com/api/v2/users"}]),
        encoding="utf-8",
    )
    (target / "historical" / "endpoints.json").write_text(
        json.dumps([{"endpoint": "https://example.com/api/v1/users"}]),
        encoding="utf-8",
    )

    diff = advanced.correlate_historical("example.com", tmp_path)

    assert diff["legacy_paths"] == ["https://example.com/api/v1/users"]
    assert "https://example.com/api/v1/users" in diff["potentially_forgotten_assets"]
    assert (target / "historical_diff.json").exists()


def test_security_header_assets_classify_csp_hosts() -> None:
    rows = advanced._extract_header_assets(
        {"content-security-policy": "default-src 'self'; connect-src https://api.example.com https://login.okta.com; img-src https://cdn.example.net"},
        "example.com",
        "https://example.com",
    )

    by_host = {row["asset"]: row["type"] for row in rows}
    assert by_host["api.example.com"] == "In Scope"
    assert by_host["login.okta.com"] == "Authentication"
    assert by_host["cdn.example.net"] == "CDN"


def test_security_header_assets_do_not_fetch_dead_probe_rows(tmp_path: Path) -> None:
    target = tmp_path / "example.com"
    (target / "probe").mkdir(parents=True)
    (target / "probe" / "probe.json").write_text(
        json.dumps(
            [
                {"url": "https://dead.example.com", "alive": False, "status_code": 0},
                {"url": "https://blocked.example.com", "alive": False, "status_code": 0, "headers": {}},
            ]
        ),
        encoding="utf-8",
    )

    payload, requests = asyncio.run(advanced.collect_security_header_assets("example.com", tmp_path, {}, "safe"))

    assert requests == 0
    assert payload["requests_sent"] == 0
    assert payload["assets"] == []


def test_asset_priority_scores_high_interest_assets(tmp_path: Path) -> None:
    target = tmp_path / "example.com"
    (target / "probe").mkdir(parents=True)
    (target / "endpoints").mkdir()
    (target / "content_discovery").mkdir()
    (target / "nuclei").mkdir()
    (target / "probe" / "alive.txt").write_text("https://admin.example.com\n", encoding="utf-8")
    (target / "probe" / "probe.json").write_text(
        json.dumps([{"url": "https://admin.example.com", "title": "Admin Login"}]),
        encoding="utf-8",
    )
    (target / "endpoints" / "endpoints.json").write_text(
        json.dumps([{"endpoint": "https://admin.example.com/api/auth/login"}]),
        encoding="utf-8",
    )
    (target / "content_discovery" / "interesting_paths.json").write_text(
        json.dumps([{"url": "https://admin.example.com/admin", "signal": "High"}]),
        encoding="utf-8",
    )
    (target / "nuclei" / "results.json").write_text(
        json.dumps([{"host": "https://admin.example.com", "info": {"severity": "high"}}]),
        encoding="utf-8",
    )

    priority = advanced.build_asset_priority("example.com", tmp_path)

    top = priority["top_assets"][0]
    assert top["asset"] == "admin.example.com"
    assert top["score"] >= 90
    assert "High-interest endpoint" in top["reasons"]
    assert top["confidence"] == "High"
    assert top["strongest_factors"]
    assert any(item["signal"] == "nuclei_finding" for item in top["signal_details"])


def test_content_signal_scores_noise_lower_than_admin_paths() -> None:
    admin = advanced._content_signal("/admin", 200)
    test_path = advanced._content_signal("/test", 200)
    forbidden = advanced._content_signal("/debug", 403)
    graphql = advanced._content_signal("/graphql", 200)

    assert admin["level"] == "High"
    assert test_path["level"] == "Low"
    assert forbidden["score"] >= 45
    assert graphql["level"] == "High"


def test_historical_source_roi_reports_signal_per_source() -> None:
    roi = advanced._historical_source_roi(
        [
            {"url": "https://api.example.com/api/v1/users?id=1", "sources": ["commoncrawl", "wayback"]},
            {"url": "https://www.example.com/about", "sources": ["wayback"]},
        ],
        [
            {"source": "commoncrawl", "duration_seconds": 2.0, "requests_sent": 1},
            {"source": "wayback", "duration_seconds": 10.0, "requests_sent": 1},
        ],
    )

    by_source = {row["source"]: row for row in roi}
    assert by_source["commoncrawl"]["opportunity_candidates"] == 1
    assert by_source["commoncrawl"]["opportunities_per_second"] == 0.5
    assert by_source["wayback"]["selected_urls"] == 2
    assert by_source["wayback"]["signal_to_noise_ratio"] == 0.5


def test_historical_js_secrets_are_redacted_in_artifacts(tmp_path: Path) -> None:
    raw_secret = "Bearer abcdefghijklmnopqrstuvwxyz123456"
    target = tmp_path / "example.com"
    (target / "historical").mkdir(parents=True)
    (target / "js" / "files").mkdir(parents=True)
    (target / "historical" / "urls.txt").write_text("", encoding="utf-8")
    (target / "js" / "files" / "app.js").write_text(f'const token = "{raw_secret}";', encoding="utf-8")
    (target / "js" / "js_files.json").write_text(
        json.dumps([{"url": "https://static.example.com/app.js", "local_path": "js/files/app.js"}]),
        encoding="utf-8",
    )

    metadata, requests = asyncio.run(
        advanced.collect_historical_js("example.com", tmp_path, {"advanced": {"historical_js": {"max_files": 10}}}, "safe")
    )
    secret_json = (target / "historical_js" / "secrets.json").read_text(encoding="utf-8")
    secret_text = (target / "historical_js" / "secrets.txt").read_text(encoding="utf-8")
    rows = json.loads(secret_json)

    assert requests == 0
    assert metadata["secrets"] == 1
    assert raw_secret not in secret_json
    assert raw_secret not in secret_text
    assert "value" not in rows[0]
    assert rows[0]["value_preview"]
    assert rows[0]["value_fingerprint"]


def test_advanced_async_records_phase_timings_and_roi(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "example.com"
    (target / "probe").mkdir(parents=True)
    (target / "probe" / "alive.txt").write_text("https://www.example.com\n", encoding="utf-8")

    async def fake_historical(*args, **kwargs):
        return {"endpoints": 2}, 3

    async def fake_content(*args, **kwargs):
        return {"findings": 1}, 4

    async def fake_headers(*args, **kwargs):
        return {"assets": [{"asset": "api.example.com"}]}, 1

    async def fake_historical_js(*args, **kwargs):
        return {"endpoints": 1, "secrets": 1}, 2

    monkeypatch.setattr(advanced, "load_config", lambda: {})
    monkeypatch.setattr(advanced, "collect_historical", fake_historical)
    monkeypatch.setattr(advanced, "correlate_historical", lambda *args, **kwargs: {})
    monkeypatch.setattr(advanced, "run_content_discovery", fake_content)
    monkeypatch.setattr(advanced, "collect_security_header_assets", fake_headers)
    monkeypatch.setattr(advanced, "collect_historical_js", fake_historical_js)
    monkeypatch.setattr(advanced, "build_asset_priority", lambda *args, **kwargs: {"asset_count": 1, "top_assets": [{}]})

    summary = asyncio.run(advanced._run_async("example.com", tmp_path, "safe", False))

    assert summary["requests_sent"] == 10
    assert summary["roi"]["signals"] == 6
    assert summary["roi"]["signals_per_request"] == 0.6
    assert summary["roi"]["empty_scope"] is False
    assert {"historical", "content_discovery", "security_headers", "historical_js", "asset_priority"} <= set(summary["phase_timings"])
