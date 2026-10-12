import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bladerecon.modules import utils


def test_status_falls_back_when_console_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    fallback = io.StringIO()

    def broken_print(*args, **kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr(utils.console, "print", broken_print)
    monkeypatch.setattr(utils.sys, "__stdout__", fallback)

    utils.status("INFO", "hello")

    assert "[INFO] hello" in fallback.getvalue()


def test_wordlist_loading_ignores_comments_empty_and_duplicates(tmp_path: Path) -> None:
    wordlist = tmp_path / "words.txt"
    wordlist.write_text("\n# comment\napi\napi\n admin \n", encoding="utf-8")

    assert utils.read_wordlist(wordlist) == ["api", "admin"]


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("target.com", "target.com"),
        ("api.target.com", "api.target.com"),
        ("TARGET.COM.", "target.com"),
        ("https://target.com", "target.com"),
        ("https://target.com/", "target.com"),
        ("https://target.com:8443", "target.com_8443"),
        ("*.example.com", "wildcard.example.com"),
        ("192.168.1.1", "192.168.1.1"),
        ("2001:db8::1", "ipv6_2001_db8__1"),
        ("192.168.1.0/24", "cidr_192.168.1.0_24"),
        ("2001:db8::/32", "cidr_2001_db8___32"),
    ],
)
def test_normalize_target_accepts_supported_target_types(target: str, expected: str) -> None:
    assert utils.normalize_target(target) == expected


@pytest.mark.parametrize(
    "target",
    [
        "123",
        "hello",
        "google",
        "localhost",
        "https://target.com/path?q=1",
        "https://target.com/#fragment",
        "https://user:pass@target.com",
        "ftp://target.com",
        "http://",
        "http://target.com:99999",
        "999.1.1.1",
        "1.2.3.4/33",
        "192.168.1.1/24",
        "2001:db8::/129",
        "*.*.example.com",
        "bad_label.example.com",
        "-bad.example.com",
        "bad-.example.com",
    ],
)
def test_normalize_target_rejects_invalid_or_ambiguous_targets(target: str) -> None:
    with pytest.raises(ValueError):
        utils.normalize_target(target)


def test_artifact_target_names_do_not_validate_as_scan_targets(tmp_path: Path) -> None:
    artifact = utils.safe_artifact_target_name("urls.txt", "file")

    assert artifact == "_file.urls-txt.invalid"
    with pytest.raises(ValueError):
        utils.normalize_target(artifact)
    assert utils.target_output_dir(tmp_path, artifact) == (tmp_path / artifact).resolve()


def test_normalize_target_rejects_path_traversal_and_absolute_paths() -> None:
    for target in ("../target.com", "..\\target.com", "/tmp/target.com", "C:\\temp\\target.com"):
        try:
            utils.normalize_target(target)
        except ValueError:
            continue
        raise AssertionError(f"unsafe target accepted: {target}")


def test_prepare_module_output_clears_stale_files_unless_resuming(tmp_path: Path) -> None:
    stale = tmp_path / "example.com" / "probe" / "alive.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("https://old.example.com\n", encoding="utf-8")

    out_dir = utils.prepare_module_output(tmp_path, "example.com", "probe")

    assert out_dir == (tmp_path / "example.com" / "probe").resolve()
    assert not stale.exists()

    fresh = out_dir / "alive.txt"
    fresh.write_text("https://new.example.com\n", encoding="utf-8")
    utils.prepare_module_output(tmp_path, "example.com", "probe", resume=True)

    assert fresh.exists()


def test_scan_run_output_dirs_are_isolated_and_latest_resolves(tmp_path: Path) -> None:
    first = utils.create_scan_run_output_dir(tmp_path, "example.com", "safe")
    second = utils.create_scan_run_output_dir(tmp_path, "example.com", "safe")

    assert first != second
    assert first.parent == second.parent == (tmp_path / "example.com" / "runs").resolve()
    assert (first / utils.RUN_MARKER_FILENAME).exists()
    assert (second / utils.RUN_MARKER_FILENAME).exists()
    assert utils.target_output_dir(first, "example.com") == first
    assert utils.resolve_latest_run_output_dir(tmp_path, "example.com") == second
    assert utils.target_output_dir(tmp_path, "example.com") == (tmp_path / "example.com").resolve()


def test_latest_run_resolution_falls_back_to_newest_valid_run_when_pointer_is_malformed(tmp_path: Path) -> None:
    first = utils.create_scan_run_output_dir(tmp_path, "example.com", "safe")
    second = utils.create_scan_run_output_dir(tmp_path, "example.com", "balanced")
    third = utils.create_scan_run_output_dir(tmp_path, "example.com", "aggressive")
    malformed = tmp_path / "example.com" / "runs" / "99999999T999999Z-safe-bad"
    malformed.mkdir()
    (tmp_path / "example.com" / utils.LATEST_RUN_FILENAME).write_text('{"path":"missing"}', encoding="utf-8")

    assert utils.resolve_latest_run_output_dir(tmp_path, "example.com") == third
    assert first != second != third


def test_latest_run_resolution_rejects_cross_target_pointer(tmp_path: Path) -> None:
    safe_run = utils.create_scan_run_output_dir(tmp_path, "example.com", "safe")
    other_run = utils.create_scan_run_output_dir(tmp_path, "other.example", "aggressive")
    (tmp_path / "example.com" / utils.LATEST_RUN_FILENAME).write_text(
        '{"path":"' + str(other_run).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )

    assert utils.resolve_latest_run_output_dir(tmp_path, "example.com") == safe_run


def test_resolve_scan_run_profile_prefers_run_marker_then_legacy_scan_state(tmp_path: Path) -> None:
    run_dir = utils.create_scan_run_output_dir(tmp_path, "example.com", "aggressive")

    assert utils.resolve_scan_run_profile(tmp_path, "example.com") == "aggressive"

    (run_dir / "scan_state.json").write_text('{"scan_profile":"safe"}', encoding="utf-8")

    assert utils.resolve_scan_run_profile(tmp_path, "example.com") == "aggressive"

    (run_dir / utils.RUN_MARKER_FILENAME).unlink()
    (tmp_path / "example.com" / "scan_state.json").write_text('{"scan_profile":"safe"}', encoding="utf-8")

    assert utils.resolve_scan_run_profile(tmp_path, "example.com") == "safe"


def test_scan_state_save_reconciles_isolated_run_profile_to_marker(tmp_path: Path) -> None:
    run_dir = utils.create_scan_run_output_dir(tmp_path, "example.com", "aggressive")

    utils.save_scan_state("example.com", run_dir, {"scan_profile": "balanced", "completed_modules": []})

    state = utils.load_scan_state("example.com", run_dir)
    assert state["scan_profile"] == "aggressive"


def test_normalize_scan_profile_treats_typer_optioninfo_as_missing() -> None:
    class OptionInfo:
        pass

    assert utils.normalize_scan_profile(OptionInfo()) == "balanced"
    assert utils.normalize_scan_profile("standard") == "balanced"


def test_scan_state_tracks_completed_and_failed_modules(tmp_path: Path) -> None:
    utils.update_scan_state("example.com", tmp_path, "probe", "completed", 1.25)
    utils.update_scan_state("example.com", tmp_path, "nuclei", "failed", 0.5, "missing binary")

    state = utils.load_scan_state("example.com", tmp_path)
    assert state["scan_id"]
    assert state["scan_profile"] == "balanced"
    assert state["framework_version"]
    assert state["report_version"] == utils.REPORT_VERSION
    assert "probe" in state["completed_modules"]
    assert "nuclei" in state["failed_modules"]
    assert state["modules"]["nuclei"]["error"] == "missing binary"


def test_scan_state_moves_completed_module_to_failed(tmp_path: Path) -> None:
    utils.update_scan_state("example.com", tmp_path, "nuclei", "completed", 1.0)
    utils.update_scan_state("example.com", tmp_path, "nuclei", "failed", 0.5, "templates unavailable")

    state = utils.load_scan_state("example.com", tmp_path)
    assert "nuclei" not in state["completed_modules"]
    assert "nuclei" in state["failed_modules"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("completed", "completed"),
        ("skipped", "skipped"),
        ("timeout", "timeout"),
        ("failed", "failed"),
        ("partial", "partial"),
        ("not_run", "not_run"),
        ("timed_out", "timeout"),
        ("incomplete_timeout", "partial"),
    ],
)
def test_module_status_resolver_normalizes_canonical_and_legacy_values(value: str, expected: str) -> None:
    assert utils.resolve_module_status(value) == expected


def test_module_status_resolver_prefers_scan_state_then_metadata() -> None:
    assert utils.resolve_module_status({"status": "failed"}, {"status": "completed"}) == "failed"
    assert utils.resolve_module_status({}, {"coverage_status": "incomplete_timeout"}) == "partial"
    assert utils.resolve_module_status({}, {}, has_artifact=True) == "completed"
    with pytest.raises(ValueError):
        utils.ModuleResult(status="unexpected")


def test_load_scan_state_translates_legacy_module_status_for_resume(tmp_path: Path) -> None:
    path = tmp_path / "example.com" / "scan_state.json"
    path.parent.mkdir()
    path.write_text('{"modules":{"nuclei":{"status":"timed_out"}}}', encoding="utf-8")
    assert utils.load_scan_state("example.com", tmp_path)["modules"]["nuclei"]["status"] == "timeout"


def test_nuclei_template_status_accepts_updater_store(tmp_path: Path) -> None:
    template_dir = tmp_path / "nuclei-templates"
    template_dir.mkdir()
    (template_dir / ".checksum").write_text("ok", encoding="utf-8")
    (template_dir / "http").mkdir()
    (template_dir / "http" / "test.yaml").write_text("id: test\ninfo:\n  name: test\n", encoding="utf-8")

    status = utils.nuclei_template_status(template_dir)

    assert status["ok"] is True
    assert status["status"] == "OK"
    assert status["source"] == "Nuclei Updater"


def test_nuclei_template_status_accepts_git_store_without_checksum(tmp_path: Path) -> None:
    template_dir = tmp_path / "nuclei-templates"
    template_dir.mkdir()
    (template_dir / ".git").mkdir()
    (template_dir / "dns").mkdir()
    (template_dir / "dns" / "test.yaml").write_text("id: test\ninfo:\n  name: test\n", encoding="utf-8")

    status = utils.nuclei_template_status(template_dir)

    assert status["ok"] is True
    assert status["status"] == "OK"
    assert status["source"] == "Git Repository"
    assert status["template_count"] == 1


def test_nuclei_template_status_marks_empty_directory_missing(tmp_path: Path) -> None:
    template_dir = tmp_path / "nuclei-templates"
    template_dir.mkdir()

    status = utils.nuclei_template_status(template_dir)

    assert status["ok"] is False
    assert status["status"] == "MISSING"


def test_nuclei_template_status_warns_for_partial_directory(tmp_path: Path) -> None:
    template_dir = tmp_path / "nuclei-templates"
    template_dir.mkdir()
    (template_dir / "misc").mkdir()
    (template_dir / "misc" / "test.yaml").write_text("id: test\ninfo:\n  name: test\n", encoding="utf-8")

    status = utils.nuclei_template_status(template_dir)

    assert status["ok"] is False
    assert status["status"] == "WARN"
    assert "categories" in status["missing"]
    assert ".checksum" not in status["missing"]


def test_nuclei_template_status_accepts_custom_template_directory(tmp_path: Path) -> None:
    template_dir = tmp_path / "custom-templates"
    template_dir.mkdir()
    (template_dir / "local.yaml").write_text("id: local\n", encoding="utf-8")

    status = utils.nuclei_template_status(template_dir, require_checksum=False)

    assert status["ok"] is True
    assert status["template_count"] == 1
    assert "categories" not in status["missing"]


def test_clear_cache_handles_read_only_files(tmp_path: Path) -> None:
    cache_file = tmp_path / ".cache" / "urlscan" / "example.com.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("{}", encoding="utf-8")
    cache_file.chmod(0o444)

    removed, skipped = utils.clear_cache(tmp_path)

    assert removed >= 1
    assert skipped == 0
    assert not (tmp_path / ".cache").exists()


def test_chromium_check_warns_when_executable_missing() -> None:
    chromium = Mock()
    chromium.executable_path = str(Path("missing-chromium"))
    playwright = Mock()
    playwright.chromium = chromium
    manager = Mock()
    manager.__enter__ = Mock(return_value=playwright)
    manager.__exit__ = Mock(return_value=False)

    with patch("importlib.util.find_spec", return_value=True), patch("playwright.sync_api.sync_playwright", return_value=manager):
        ok, detail = utils.check_playwright_chromium()

    assert ok is False
    assert detail == "Chromium browser not installed"


def test_load_config_supports_nested_env_overrides_with_types(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLADERECON_TIMEOUTS_HTTP", "25")
    monkeypatch.setenv("BLADERECON_OPSEC_RANDOM_USER_AGENT", "true")
    monkeypatch.setenv("BLADERECON_NUCLEI__BASELINE_SCAN__ENABLED", "false")
    monkeypatch.setenv("BLADERECON_SAFETY_PROFILES_SAFE_CONCURRENCY_PROBE", "3")

    config = utils.load_config(Path("missing-config.yaml"))

    assert config["timeouts"]["http"] == 25
    assert config["opsec"]["random_user_agent"] is True
    assert config["nuclei"]["baseline_scan"]["enabled"] is False
    assert config["safety_profiles"]["safe"]["concurrency"]["probe"] == 3


def test_safety_profiles_are_monotonic_for_collection_ceilings_and_rates() -> None:
    config = utils.load_config(Path("missing-config.yaml"))
    ordered = ["safe", "balanced", "aggressive"]
    ceilings = ["probe", "js_html", "js_downloads", "screenshots", "nuclei_targets", "historical_urls", "content_discovery", "security_header_hosts", "historical_js"]
    concurrency = ["probe", "js", "screenshots", "nuclei", "dns"]
    rates = ["probe", "js", "screenshots", "nuclei"]

    for section, keys in (("request_ceilings", ceilings), ("concurrency", concurrency), ("rate_limits", rates)):
        for key in keys:
            values = [config["safety_profiles"][profile][section][key] for profile in ordered]
            assert values == sorted(values), f"{section}.{key} is not monotonic: {values}"


def test_atomic_write_text_preserves_existing_file_on_replace_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "artifact.json"
    path.write_text('{"ok": true}', encoding="utf-8")

    def fail_replace(_src: Path, _dst: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(utils.os, "replace", fail_replace)

    with pytest.raises(OSError):
        utils.atomic_write_text(path, '{"ok": false}', encoding="utf-8")

    assert path.read_text(encoding="utf-8") == '{"ok": true}'
    assert not list(tmp_path.glob(".artifact.json.*.tmp"))
