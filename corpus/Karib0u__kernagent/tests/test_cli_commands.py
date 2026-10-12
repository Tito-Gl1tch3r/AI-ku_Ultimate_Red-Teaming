"""Comprehensive tests for CLI commands."""

import json
from pathlib import Path
from unittest import mock

import pytest

from kernagent.cli import (
    build_parser,
    ensure_snapshot,
    run_agent_and_print,
    run_oneshot_and_print,
    run_summary_and_print,
)
from kernagent.config import Settings
from kernagent.snapshot import SnapshotError


class DummyMessage:
    """Mock message for LLM responses."""

    def __init__(self, content, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []


class DummyChoice:
    """Mock choice for LLM responses."""

    def __init__(self, message):
        self.message = message


class DummyResponse:
    """Mock response for LLM chat completions."""

    def __init__(self, content):
        self.choices = [DummyChoice(DummyMessage(content))]


@pytest.fixture
def mock_settings():
    """Create test settings."""
    return Settings(
        api_key="test-key",
        base_url="http://test-url",
        model="test-model",
        debug=False,
    )


@pytest.fixture
def fixture_archive():
    """Path to test fixture archive."""
    return Path(__file__).parent / "fixtures" / "bifrose_archive"


class TestArgumentParsing:
    """Test CLI argument parsing."""

    def test_parser_requires_command(self):
        """Parser should require a subcommand."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_summary_command_parsing(self):
        """Test summary command argument parsing."""
        parser = build_parser()
        args = parser.parse_args(["summary", "/path/to/binary"])
        assert args.command == "summary"
        assert args.binary == Path("/path/to/binary")
        assert not args.json

    def test_summary_command_with_json_flag(self):
        """Test summary command with --json flag."""
        parser = build_parser()
        args = parser.parse_args(["summary", "/path/to/binary", "--json"])
        assert args.command == "summary"
        assert args.json

    def test_ask_command_parsing(self):
        """Test ask command argument parsing."""
        parser = build_parser()
        args = parser.parse_args(["ask", "/path/to/binary", "What does this do?"])
        assert args.command == "ask"
        assert args.binary == Path("/path/to/binary")
        assert args.question == "What does this do?"

    def test_oneshot_command_parsing(self):
        """Test oneshot command argument parsing."""
        parser = build_parser()
        args = parser.parse_args(["oneshot", "/path/to/binary"])
        assert args.command == "oneshot"
        assert args.binary == Path("/path/to/binary")
        assert not args.json

    def test_oneshot_command_with_json_flag(self):
        """Test oneshot command with --json flag."""
        parser = build_parser()
        args = parser.parse_args(["oneshot", "/path/to/binary", "--json"])
        assert args.command == "oneshot"
        assert args.json

    def test_global_model_override(self):
        """Test --model global argument."""
        parser = build_parser()
        args = parser.parse_args(["--model", "custom-model", "summary", "/path/to/binary"])
        assert args.model == "custom-model"

    def test_global_base_url_override(self):
        """Test --base-url global argument."""
        parser = build_parser()
        args = parser.parse_args(["--base-url", "http://custom-url", "summary", "/path/to/binary"])
        assert args.base_url == "http://custom-url"

    def test_global_api_key_override(self):
        """Test --api-key global argument."""
        parser = build_parser()
        args = parser.parse_args(["--api-key", "custom-key", "summary", "/path/to/binary"])
        assert args.api_key == "custom-key"

    def test_verbose_flag(self):
        """Test --verbose global flag."""
        parser = build_parser()
        args = parser.parse_args(["-v", "summary", "/path/to/binary"])
        assert args.verbose


class TestEnsureSnapshot:
    """Test snapshot discovery and creation logic."""

    def test_returns_existing_archive_directory(self, tmp_path):
        """Should return existing archive directory if present."""
        binary = tmp_path / "test.exe"
        binary.touch()
        archive_dir = tmp_path / "test_archive"
        archive_dir.mkdir()

        result = ensure_snapshot(binary, verbose=False)
        assert result == archive_dir

    def test_extracts_zip_if_archive_missing(self, tmp_path):
        """Should extract ZIP if archive directory missing."""
        import zipfile

        binary = tmp_path / "test.exe"
        binary.touch()
        zip_path = tmp_path / "test_archive.zip"
        archive_dir = tmp_path / "test_archive"

        # Create a test ZIP with a directory structure
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test_archive/meta.json", '{"test": true}')

        result = ensure_snapshot(binary, verbose=False)
        assert result == archive_dir
        assert archive_dir.exists()

    @mock.patch("kernagent.cli.build_snapshot")
    def test_builds_snapshot_if_nothing_exists(self, mock_build, tmp_path):
        """Should build snapshot via PyGhidra if nothing exists."""
        binary = tmp_path / "test.exe"
        binary.touch()
        archive_dir = tmp_path / "test_archive"

        mock_build.return_value = archive_dir

        result = ensure_snapshot(binary, verbose=True)
        assert result == archive_dir
        mock_build.assert_called_once_with(binary, None, verbose=True)

    def test_rejects_path_traversal_in_zip(self, tmp_path):
        """Should reject ZIP files with path traversal attempts."""
        import zipfile

        binary = tmp_path / "test.exe"
        binary.touch()
        zip_path = tmp_path / "test_archive.zip"

        # Create malicious ZIP with path traversal
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../evil.txt", "malicious")

        with pytest.raises(SnapshotError, match="Unsafe relative path"):
            ensure_snapshot(binary, verbose=False)


class TestSummaryCommand:
    """Test summary command execution."""

    def test_summary_json_output(self, fixture_archive, mock_settings, capsys):
        """Summary --json should output pruned JSON without LLM call."""
        run_summary_and_print(fixture_archive, mock_settings, verbose=False, json_output=True)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "file" in output
        assert "sections" in output
        assert output["file"]["format"]

    def test_summary_llm_analysis(self, fixture_archive, mock_settings, capsys):
        """Summary without --json should call LLM and print response."""
        with mock.patch("kernagent.cli.LLMClient") as mock_llm_class:
            mock_llm = mock.Mock()
            mock_llm.chat.return_value = DummyResponse("Executive summary: This is malware.")
            mock_llm_class.return_value = mock_llm

            run_summary_and_print(fixture_archive, mock_settings, verbose=False, json_output=False)

            captured = capsys.readouterr()
            assert "Executive summary: This is malware." in captured.out
            mock_llm.chat.assert_called_once()

            # Verify system prompt and payload structure
            call_args = mock_llm.chat.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            # User message should be JSON payload
            payload = json.loads(messages[1]["content"])
            assert "file" in payload

    def test_summary_llm_failure(self, fixture_archive, mock_settings):
        """Summary should raise on LLM failure."""
        with mock.patch("kernagent.cli.LLMClient") as mock_llm_class:
            mock_llm = mock.Mock()
            mock_llm.chat.side_effect = Exception("API Error")
            mock_llm_class.return_value = mock_llm

            with pytest.raises(Exception, match="API Error"):
                run_summary_and_print(fixture_archive, mock_settings, verbose=False, json_output=False)


class TestOneshotCommand:
    """Test oneshot command execution."""

    def test_oneshot_json_output(self, fixture_archive, mock_settings, capsys):
        """Oneshot --json should output pruned JSON without LLM call."""
        run_oneshot_and_print(fixture_archive, mock_settings, verbose=False, json_output=True)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "file" in output
        assert "sections" in output

    def test_oneshot_llm_analysis(self, fixture_archive, mock_settings, capsys):
        """Oneshot without --json should call LLM with ONESHOT_SYSTEM_PROMPT."""
        with mock.patch("kernagent.cli.LLMClient") as mock_llm_class:
            mock_llm = mock.Mock()
            mock_llm.chat.return_value = DummyResponse("Classification: Backdoor trojan")
            mock_llm_class.return_value = mock_llm

            run_oneshot_and_print(fixture_archive, mock_settings, verbose=False, json_output=False)

            captured = capsys.readouterr()
            assert "Classification: Backdoor trojan" in captured.out
            mock_llm.chat.assert_called_once()

            # Verify temperature=0 for deterministic output
            call_args = mock_llm.chat.call_args
            assert call_args[1]["temperature"] == 0


class TestAskCommand:
    """Test ask command execution."""

    def test_ask_invokes_agent(self, fixture_archive, mock_settings, capsys):
        """Ask should invoke agent with question."""
        with mock.patch("kernagent.cli.ReverseEngineeringAgent") as mock_agent_class:
            mock_agent = mock.Mock()
            mock_agent.run.return_value = "The binary is a network backdoor."
            mock_agent_class.return_value = mock_agent

            run_agent_and_print(fixture_archive, "What is this binary?", mock_settings, verbose=True)

            captured = capsys.readouterr()
            assert "The binary is a network backdoor." in captured.out

            mock_agent.run.assert_called_once_with("What is this binary?", verbose=True)

    def test_ask_creates_snapshot_tools(self, fixture_archive, mock_settings):
        """Ask should create SnapshotTools with archive directory."""
        with mock.patch("kernagent.cli.SnapshotTools") as mock_snapshot_class:
            with mock.patch("kernagent.cli.ReverseEngineeringAgent") as mock_agent_class:
                with mock.patch("kernagent.cli.build_tool_map"):
                    mock_agent = mock.Mock()
                    mock_agent.run.return_value = "Answer"
                    mock_agent_class.return_value = mock_agent

                    run_agent_and_print(fixture_archive, "Test question", mock_settings, verbose=False)

                    mock_snapshot_class.assert_called_once_with(fixture_archive)


class TestSettingsOverride:
    """Test that CLI arguments override settings."""

    def test_model_override_applied(self):
        """Test that --model overrides settings.model."""
        parser = build_parser()
        args = parser.parse_args(["--model", "gpt-4", "summary", "/test/binary"])

        settings = Settings()
        if args.model:
            settings.model = args.model

        assert settings.model == "gpt-4"

    def test_base_url_override_applied(self):
        """Test that --base-url overrides settings.base_url."""
        parser = build_parser()
        args = parser.parse_args(["--base-url", "http://custom", "summary", "/test/binary"])

        settings = Settings()
        if args.base_url:
            settings.base_url = args.base_url

        assert settings.base_url == "http://custom"

    def test_api_key_override_applied(self):
        """Test that --api-key overrides settings.api_key."""
        parser = build_parser()
        args = parser.parse_args(["--api-key", "sk-custom", "summary", "/test/binary"])

        settings = Settings()
        if args.api_key:
            settings.api_key = args.api_key

        assert settings.api_key == "sk-custom"
