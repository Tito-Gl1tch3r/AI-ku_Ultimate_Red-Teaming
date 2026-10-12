import json
import subprocess
from types import SimpleNamespace

from bladerecon.main import _bootstrap_nuclei_templates, _collect_summary, _collect_traffic_counts, _command_output, _custom_templates_available, full, resume
from bladerecon.modules import nuclei
from bladerecon.modules.utils import create_scan_run_output_dir


def test_collect_summary_marks_template_unavailable_nuclei_as_skipped(tmp_path):
    target = tmp_path / "example.com"
    target.mkdir(parents=True)
    (target / "scan_state.json").write_text(
        json.dumps({"modules": {"nuclei": {"status": "failed", "error": "templates unavailable"}}}),
        encoding="utf-8",
    )

    summary = _collect_summary("example.com", tmp_path, "1.00s")

    assert summary["Nuclei Findings"] == "Skipped"


def test_collect_summary_marks_absent_nuclei_as_not_run(tmp_path):
    target = tmp_path / "example.com"
    target.mkdir(parents=True)

    summary = _collect_summary("example.com", tmp_path, "1.00s")

    assert summary["Nuclei Findings"] == "Not Run"


def test_collect_summary_uses_metadata_for_skipped_nuclei(tmp_path):
    target = tmp_path / "example.com"
    target.mkdir(parents=True)
    (target / "nuclei").mkdir(parents=True)
    (target / "nuclei" / "metadata.json").write_text(
        json.dumps({"status": "skipped", "skip_reason": "templates unavailable"}),
        encoding="utf-8",
    )

    summary = _collect_summary("example.com", tmp_path, "1.00s")

    assert summary["Nuclei Findings"] == "Skipped"


def test_resume_preserves_latest_run_profile(tmp_path, monkeypatch):
    run_dir = create_scan_run_output_dir(tmp_path, "example.com", "safe")
    (run_dir / "scan_state.json").write_text('{"scan_profile":"safe","completed_modules":[]}', encoding="utf-8")
    calls = []

    def fake_full(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("bladerecon.main.full", fake_full)

    resume(domain="example.com", domain_option=None, output=tmp_path)

    assert calls[0]["resume_mode"] is True
    assert calls[0]["profile"] == "safe"


def test_full_preflight_does_not_block_on_optional_dependencies(tmp_path, monkeypatch):
    readiness_calls = []
    optional_calls = []

    def fake_ensure(requirements, output, template_dir=None, auto_templates=True):
        readiness_calls.append(list(requirements))
        return True

    def fake_warn(requirements, output, template_dir=None):
        optional_calls.append(list(requirements))

    monkeypatch.setattr("bladerecon.main._ensure_readiness", fake_ensure)
    monkeypatch.setattr("bladerecon.main._warn_optional_readiness", fake_warn)
    monkeypatch.setattr("bladerecon.main.print_module_header", lambda *args, **kwargs: None)
    monkeypatch.setattr("bladerecon.main.print_scan_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr("bladerecon.main.success", lambda *args, **kwargs: None)
    monkeypatch.setattr("bladerecon.main.info", lambda *args, **kwargs: None)

    result = SimpleNamespace(status="completed")
    monkeypatch.setattr("bladerecon.modules.subdomains.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.probe.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.js.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.endpoints.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.secrets.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.parameters.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.intelligence.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.advanced.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.screenshots.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.nuclei.run", lambda *args, **kwargs: result)
    monkeypatch.setattr("bladerecon.modules.report.run", lambda *args, **kwargs: result)

    full(domain="example.com", output=tmp_path, report=False)

    assert readiness_calls == [["Output Directories", "Permissions"]]
    assert optional_calls == [["Playwright", "Chromium", "Nuclei Binary", "Nuclei Templates"]]


def test_collect_traffic_counts_includes_module_metadata(tmp_path):
    target = tmp_path / "example.com"
    (target / "probe").mkdir(parents=True)
    (target / "js").mkdir()
    (target / "probe" / "probe.json").write_text('[{"status_code":200},{"status_code":0}]', encoding="utf-8")
    (target / "js" / "metadata.json").write_text('{"html_requests":2,"download_requests":3}', encoding="utf-8")
    (target / "advanced_metadata.json").write_text('{"requests_sent":7}', encoding="utf-8")

    counts = _collect_traffic_counts("example.com", tmp_path)

    assert counts["total_requests_sent"] == 14
    assert counts["total_responses_received"] == 1


def test_custom_templates_available_accepts_single_yaml_directory(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "local.yaml").write_text("id: local\n", encoding="utf-8")

    assert _custom_templates_available(templates) is True


def test_command_output_strips_ansi_sequences():
    ok, output = _command_output(["python", "-c", "print('\\x1b[34mblue\\x1b[0m')"])

    assert ok is True
    assert output == "blue"


def test_nuclei_run_skips_when_templates_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(nuclei, "_nuclei_exists", lambda: True)
    monkeypatch.setattr(nuclei, "_resolve_target_file", lambda domain, list_file, output: (domain, None, domain))
    monkeypatch.setattr(nuclei, "nuclei_template_status", lambda *args, **kwargs: {"ok": False, "path": str(tmp_path), "missing": ["templates"]})

    result = nuclei.run(domain="example.com", output=tmp_path)

    assert result.status == "skipped"
    assert "templates unavailable" in result.reason


def test_template_bootstrap_falls_back_to_git_after_updater_timeout(tmp_path, monkeypatch):
    calls = []

    def fake_which(name):
        return name

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "nuclei":
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 1))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("bladerecon.main.shutil.which", fake_which)
    monkeypatch.setattr("bladerecon.main.subprocess.run", fake_run)
    monkeypatch.setattr("bladerecon.main.nuclei_template_status", lambda path: {"ok": True, "source": "Git Repository"})

    ok, message = _bootstrap_nuclei_templates(tmp_path / "nuclei-templates", timeout=1)

    assert ok is True
    assert "Git" in message
    assert calls[0][0] == "nuclei"
    assert calls[1][:3] == ["git", "clone", "--depth"]


def test_template_bootstrap_reports_missing_git_after_updater_failure(tmp_path, monkeypatch):
    def fake_which(name):
        return "nuclei" if name == "nuclei" else None

    monkeypatch.setattr("bladerecon.main.shutil.which", fake_which)
    monkeypatch.setattr(
        "bladerecon.main.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="failed to download templates"),
    )

    ok, message = _bootstrap_nuclei_templates(tmp_path / "nuclei-templates", timeout=1)

    assert ok is False
    assert "git is not available" in message
