from pathlib import Path

from bladerecon.modules import parameters


def test_parameter_discovery_skips_when_no_urls(monkeypatch, tmp_path: Path) -> None:
    async def no_urls(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return []

    monkeypatch.setattr(parameters, "_fetch_wayback", no_urls)
    monkeypatch.setattr(parameters, "_fetch_commoncrawl", no_urls)

    result = parameters.run("empty.example", tmp_path)

    assert result.status == "skipped"
    assert result.reason == "No URL sources available"
    assert not (tmp_path / "empty.example" / "parameters" / "parameters.txt").exists()


def test_parameter_discovery_skips_empty_url_file(tmp_path: Path) -> None:
    url_file = tmp_path / "urls.txt"
    url_file.write_text("", encoding="utf-8")

    result = parameters.run(str(url_file), tmp_path)

    assert result.status == "skipped"
    assert result.reason == "No URL sources available"
    assert not (tmp_path / "_file.urls.invalid" / "parameters" / "parameters.txt").exists()


def test_parameter_discovery_uses_local_fallback_urls(monkeypatch, tmp_path: Path) -> None:
    async def no_urls(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return []

    monkeypatch.setattr(parameters, "_fetch_wayback", no_urls)
    monkeypatch.setattr(parameters, "_fetch_commoncrawl", no_urls)

    endpoint_dir = tmp_path / "example.com" / "endpoints"
    js_dir = tmp_path / "example.com" / "js"
    endpoint_dir.mkdir(parents=True)
    js_dir.mkdir()
    (endpoint_dir / "endpoints.json").write_text(
        '[{"endpoint":"https://api.example.com/v1/users?id=1","source":"https://www.example.com/app.js"}]',
        encoding="utf-8",
    )
    (js_dir / "js_files.json").write_text(
        '[{"url":"https://www.example.com/app.js?build=123","source_page":"https://www.example.com"}]',
        encoding="utf-8",
    )

    result = parameters.run("example.com", tmp_path)

    assert result.status == "completed"
    text = (tmp_path / "example.com" / "parameters" / "parameters_from_urls.txt").read_text(encoding="utf-8")
    assert "id" in text
    assert "build" in text


def test_parameter_discovery_writes_confirmed_historical_candidate_classes(monkeypatch, tmp_path: Path) -> None:
    async def no_urls(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return []

    monkeypatch.setattr(parameters, "_fetch_wayback", no_urls)
    monkeypatch.setattr(parameters, "_fetch_commoncrawl", no_urls)

    endpoint_dir = tmp_path / "example.com" / "endpoints"
    historical_dir = tmp_path / "example.com" / "historical"
    endpoint_dir.mkdir(parents=True)
    historical_dir.mkdir()
    (endpoint_dir / "endpoints.txt").write_text("https://api.example.com/v1/users?id=1\n", encoding="utf-8")
    (historical_dir / "urls.txt").write_text("https://old.example.com/search?legacy=1\n", encoding="utf-8")

    result = parameters.run("example.com", tmp_path)

    assert result.status == "completed"
    confirmed = (tmp_path / "example.com" / "parameters" / "parameters_confirmed.txt").read_text(encoding="utf-8")
    historical = (tmp_path / "example.com" / "parameters" / "parameters_historical.txt").read_text(encoding="utf-8")
    rows = parameters.json.loads((tmp_path / "example.com" / "parameters" / "parameters.json").read_text(encoding="utf-8"))
    classes = {row["parameter"]: row["class"] for row in rows}
    assert "id" in confirmed
    assert "legacy" in historical
    assert classes["id"] == "confirmed"
    assert classes["legacy"] == "historical"
    assert "candidate" in classes.values()


def test_parameter_discovery_skips_wordlist_only_without_local_surface(monkeypatch, tmp_path: Path) -> None:
    async def urls_without_params(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return ["https://empty.example/", "https://www.empty.example/about"]

    async def no_urls(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return []

    monkeypatch.setattr(parameters, "_fetch_wayback", urls_without_params)
    monkeypatch.setattr(parameters, "_fetch_commoncrawl", no_urls)

    result = parameters.run("empty.example", tmp_path)

    assert result.status == "skipped"
    assert result.reason == "No URL-derived parameters or local attack surface available"
    assert not (tmp_path / "empty.example" / "parameters" / "parameters.txt").exists()


def test_parameter_fallback_ignores_dead_probe_urls(monkeypatch, tmp_path: Path) -> None:
    async def no_urls(domain: str, timeout: float = parameters.SOURCE_TIMEOUT):
        return []

    monkeypatch.setattr(parameters, "_fetch_wayback", no_urls)
    monkeypatch.setattr(parameters, "_fetch_commoncrawl", no_urls)

    probe_dir = tmp_path / "empty.example" / "probe"
    probe_dir.mkdir(parents=True)
    (probe_dir / "probe.json").write_text(
        '[{"url":"https://empty.example/?token=x","alive":false,"final_url":""}]',
        encoding="utf-8",
    )

    result = parameters.run("empty.example", tmp_path)

    assert result.status == "skipped"
    assert result.reason == "No URL sources available"
    assert not (tmp_path / "empty.example" / "parameters" / "parameters.txt").exists()
