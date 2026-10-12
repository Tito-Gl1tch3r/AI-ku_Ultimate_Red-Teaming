"""Unit tests for tengu.tools.social.set_toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tengu.exceptions import InvalidInputError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.report_progress = AsyncMock()
    return ctx


def _mock_config() -> MagicMock:
    cfg = MagicMock()
    cfg.tools.paths.setoolkit = ""
    cfg.tools.defaults.scan_timeout = 300
    return cfg


def _setup_rate_limited_mock() -> MagicMock:
    mock_rl_ctx = MagicMock()
    mock_rl_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_rl_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_rl_ctx


def _setup_audit_mock() -> AsyncMock:
    mock_audit = AsyncMock()
    mock_audit.log_target_blocked = AsyncMock()
    mock_audit.log_tool_call = AsyncMock()
    return mock_audit


# ---------------------------------------------------------------------------
# TestBuildAnswerFile
# ---------------------------------------------------------------------------


class TestBuildAnswerFile:
    def test_creates_file_with_newline_separated_answers(self):
        """Answer file contains each answer on its own line."""
        from tengu.tools.social.set_toolkit import _build_answer_file

        answers = ["1", "2", "3", "192.168.1.100", "https://example.com"]
        path = _build_answer_file(answers)
        try:
            content = Path(path).read_text()
            assert content == "1\n2\n3\n192.168.1.100\nhttps://example.com\n"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_creates_real_file(self):
        """_build_answer_file creates a file that actually exists."""
        from tengu.tools.social.set_toolkit import _build_answer_file

        path = _build_answer_file(["1", "2"])
        try:
            assert Path(path).exists()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_empty_answers_creates_empty_file(self):
        """Empty answers list creates a file with just a newline."""
        from tengu.tools.social.set_toolkit import _build_answer_file

        path = _build_answer_file([])
        try:
            content = Path(path).read_text()
            assert content == "\n"
        finally:
            Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TestSetCredentialHarvester
# ---------------------------------------------------------------------------


class TestSetCredentialHarvester:
    @pytest.mark.asyncio
    async def test_success_returns_expected_structure(self):
        """Successful run returns dict with all expected keys."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("SET output", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/fake_set.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_credential_harvester

            result = await set_credential_harvester(
                ctx,
                target_url="https://login.example.com",
                lhost="192.168.1.100",
                listen_port=80,
            )

        assert result["tool"] == "set_credential_harvester"
        assert result["target_url"] == "https://login.example.com"
        assert result["lhost"] == "192.168.1.100"
        assert result["listen_port"] == 80
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "output" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_allowlist_blocked_raises_and_logs(self):
        """Allowlist denial re-raises and calls log_target_blocked."""
        ctx = _make_ctx()
        mock_audit = _setup_audit_mock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
        ):
            allowlist_instance = MagicMock()
            allowlist_instance.check.side_effect = PermissionError("target not allowed")
            mock_allowlist.return_value = allowlist_instance

            from tengu.tools.social.set_toolkit import set_credential_harvester

            with pytest.raises(PermissionError, match="target not allowed"):
                await set_credential_harvester(
                    ctx,
                    target_url="https://blocked.example.com",
                    lhost="192.168.1.100",
                )

        mock_audit.log_target_blocked.assert_awaited_once()
        call_args = mock_audit.log_target_blocked.call_args[0]
        assert call_args[0] == "set_credential_harvester"

    @pytest.mark.asyncio
    async def test_run_command_failure_logs_and_reraises(self):
        """run_command exception logs 'failed' and re-raises."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(side_effect=TimeoutError("timed out")),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/fake_set.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_credential_harvester

            with pytest.raises(TimeoutError):
                await set_credential_harvester(
                    ctx,
                    target_url="https://login.example.com",
                    lhost="192.168.1.100",
                )

        # Verify 'failed' audit entry was written
        failed_calls = [
            c
            for c in mock_audit.log_tool_call.call_args_list
            if c.kwargs.get("result") == "failed" or (c.args and "failed" in c.args)
        ]
        assert len(failed_calls) >= 1

    @pytest.mark.asyncio
    async def test_invalid_target_url_raises_invalid_input(self):
        """Non-URL target raises InvalidInputError."""
        ctx = _make_ctx()

        with patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()):
            from tengu.tools.social.set_toolkit import set_credential_harvester

            with pytest.raises(InvalidInputError):
                await set_credential_harvester(
                    ctx,
                    target_url="not-a-url",
                    lhost="192.168.1.100",
                )

    @pytest.mark.asyncio
    async def test_answer_file_cleaned_up_on_success(self):
        """Temporary answer file is deleted after successful execution."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/tengu_set_test.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_credential_harvester

            await set_credential_harvester(
                ctx,
                target_url="https://login.example.com",
                lhost="192.168.1.100",
            )

        mock_path_class.assert_called_with("/tmp/tengu_set_test.txt")
        mock_path_instance.unlink.assert_called_once_with(missing_ok=True)

    @pytest.mark.asyncio
    async def test_answer_file_cleaned_up_on_failure(self):
        """Temporary answer file is deleted even when execution fails."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(side_effect=RuntimeError("seautomate crashed")),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/tengu_set_fail.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_credential_harvester

            with pytest.raises(RuntimeError):
                await set_credential_harvester(
                    ctx,
                    target_url="https://login.example.com",
                    lhost="192.168.1.100",
                )

        mock_path_class.assert_called_with("/tmp/tengu_set_fail.txt")
        mock_path_instance.unlink.assert_called_once_with(missing_ok=True)

    @pytest.mark.asyncio
    async def test_nonzero_returncode_sets_success_false(self):
        """Non-zero return code results in success=False."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("", "error occurred", 1)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/fake_set.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_credential_harvester

            result = await set_credential_harvester(
                ctx,
                target_url="https://login.example.com",
                lhost="192.168.1.100",
            )

        assert result["success"] is False
        assert result["returncode"] == 1


# ---------------------------------------------------------------------------
# TestSetQrcodeAttack
# ---------------------------------------------------------------------------


class TestSetQrcodeAttack:
    @pytest.mark.asyncio
    async def test_success_returns_expected_structure(self):
        """Successful QR code generation returns dict with expected keys."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("QR code created", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/fake_set.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_qrcode_attack

            result = await set_qrcode_attack(ctx, url="https://phish.example.com")

        assert result["tool"] == "set_qrcode_attack"
        assert result["url"] == "https://phish.example.com"
        assert result["success"] is True
        assert "output" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_invalid_url_raises_invalid_input(self):
        """Non-URL input raises InvalidInputError."""
        ctx = _make_ctx()

        with patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()):
            from tengu.tools.social.set_toolkit import set_qrcode_attack

            with pytest.raises(InvalidInputError):
                await set_qrcode_attack(ctx, url="not-a-valid-url")

    @pytest.mark.asyncio
    async def test_allowlist_blocked_raises(self):
        """Allowlist denial re-raises exception."""
        ctx = _make_ctx()
        mock_audit = _setup_audit_mock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
        ):
            allowlist_instance = MagicMock()
            allowlist_instance.check.side_effect = PermissionError("blocked")
            mock_allowlist.return_value = allowlist_instance

            from tengu.tools.social.set_toolkit import set_qrcode_attack

            with pytest.raises(PermissionError):
                await set_qrcode_attack(ctx, url="https://blocked.example.com")

    @pytest.mark.asyncio
    async def test_answer_file_uses_correct_menu_path(self):
        """Answer file contains the correct SET QR code menu path."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()
        captured_answers: list[list[str]] = []

        def fake_build_answer_file(answers: list[str]) -> str:
            captured_answers.append(answers)
            return "/tmp/fake_set.txt"

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                side_effect=fake_build_answer_file,
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_qrcode_attack

            await set_qrcode_attack(ctx, url="https://phish.example.com")

        # Menu path: 1 → 9 → url
        assert len(captured_answers) == 1
        assert captured_answers[0][0] == "1"
        assert captured_answers[0][1] == "9"
        assert captured_answers[0][2] == "https://phish.example.com"


# ---------------------------------------------------------------------------
# TestSetPayloadGenerator
# ---------------------------------------------------------------------------


class TestSetPayloadGenerator:
    @pytest.mark.asyncio
    async def test_success_powershell_alphanumeric(self):
        """Successful payload generation returns expected structure."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("payload created", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/fake_set.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_payload_generator

            result = await set_payload_generator(
                ctx,
                payload_type="powershell_alphanumeric",
                lhost="192.168.1.100",
                lport=4444,
            )

        assert result["tool"] == "set_payload_generator"
        assert result["payload_type"] == "powershell_alphanumeric"
        assert result["lhost"] == "192.168.1.100"
        assert result["lport"] == 4444
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_invalid_payload_type_raises(self):
        """Unknown payload_type raises InvalidInputError."""
        ctx = _make_ctx()

        with patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()):
            from tengu.tools.social.set_toolkit import set_payload_generator

            with pytest.raises(InvalidInputError):
                await set_payload_generator(
                    ctx,
                    payload_type="unknown_payload",
                    lhost="192.168.1.100",
                    lport=4444,
                )

    @pytest.mark.asyncio
    async def test_all_valid_payload_types_accepted(self):
        """All documented payload types execute without sanitization error."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        valid_types = ["powershell_alphanumeric", "powershell_reverse", "hta"]

        for ptype in valid_types:
            with (
                patch(
                    "tengu.tools.social.set_toolkit.get_config",
                    return_value=_mock_config(),
                ),
                patch(
                    "tengu.tools.social.set_toolkit.get_audit_logger",
                    return_value=mock_audit,
                ),
                patch(
                    "tengu.tools.social.set_toolkit.resolve_tool_path",
                    return_value="/usr/bin/seautomate",
                ),
                patch(
                    "tengu.tools.social.set_toolkit.rate_limited",
                    return_value=mock_rl_ctx,
                ),
                patch(
                    "tengu.tools.social.set_toolkit.make_allowlist_from_config"
                ) as mock_allowlist,
                patch(
                    "tengu.tools.social.set_toolkit.run_command",
                    AsyncMock(return_value=("", "", 0)),
                ),
                patch(
                    "tengu.tools.social.set_toolkit._build_answer_file",
                    return_value="/tmp/fake_set.txt",
                ),
                patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
            ):
                mock_allowlist.return_value.check.return_value = None

                from tengu.tools.social.set_toolkit import set_payload_generator

                result = await set_payload_generator(
                    ctx, payload_type=ptype, lhost="10.0.0.1", lport=4444
                )

            assert result["payload_type"] == ptype

    @pytest.mark.asyncio
    async def test_payload_menu_option_correct_for_hta(self):
        """HTA payload uses menu option '3' in the answer file."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()
        captured_answers: list[list[str]] = []

        def fake_build(answers: list[str]) -> str:
            captured_answers.append(answers)
            return "/tmp/fake_set.txt"

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                side_effect=fake_build,
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_payload_generator

            await set_payload_generator(ctx, payload_type="hta", lhost="10.0.0.1", lport=9090)

        # Menu: 1 → 4 → 3 (hta) → lhost → lport
        assert len(captured_answers) == 1
        answers = captured_answers[0]
        assert answers[0] == "1"
        assert answers[1] == "4"
        assert answers[2] == "3"
        assert answers[3] == "10.0.0.1"
        assert answers[4] == "9090"

    @pytest.mark.asyncio
    async def test_allowlist_blocked_logs_and_raises(self):
        """Blocked lhost logs target_blocked and raises."""
        ctx = _make_ctx()
        mock_audit = _setup_audit_mock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
        ):
            allowlist_instance = MagicMock()
            allowlist_instance.check.side_effect = PermissionError("lhost not allowed")
            mock_allowlist.return_value = allowlist_instance

            from tengu.tools.social.set_toolkit import set_payload_generator

            with pytest.raises(PermissionError):
                await set_payload_generator(
                    ctx,
                    payload_type="powershell_reverse",
                    lhost="1.2.3.4",
                    lport=4444,
                )

        mock_audit.log_target_blocked.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_lhost_raises_invalid_input(self):
        """Invalid lhost (shell metacharacters) raises InvalidInputError."""
        ctx = _make_ctx()

        with patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()):
            from tengu.tools.social.set_toolkit import set_payload_generator

            with pytest.raises(InvalidInputError):
                await set_payload_generator(
                    ctx,
                    payload_type="powershell_reverse",
                    lhost="192.168.1.1; rm -rf /",
                    lport=4444,
                )

    @pytest.mark.asyncio
    async def test_answer_file_cleaned_up_on_success(self):
        """Answer file is deleted after successful payload generation."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_path_class = MagicMock()
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                AsyncMock(return_value=("", "", 0)),
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/tengu_payload.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_payload_generator

            await set_payload_generator(
                ctx, payload_type="powershell_reverse", lhost="10.0.0.1", lport=4444
            )

        mock_path_class.assert_called_with("/tmp/tengu_payload.txt")
        mock_path_instance.unlink.assert_called_once_with(missing_ok=True)

    @pytest.mark.asyncio
    async def test_run_command_called_with_seautomate_and_answer_file(self):
        """run_command is called with [seautomate_path, answer_file]."""
        ctx = _make_ctx()
        mock_rl_ctx = _setup_rate_limited_mock()
        mock_audit = _setup_audit_mock()
        mock_run_command = AsyncMock(return_value=("", "", 0))
        mock_path_class = MagicMock()
        mock_path_class.return_value.unlink = MagicMock()

        with (
            patch("tengu.tools.social.set_toolkit.get_config", return_value=_mock_config()),
            patch("tengu.tools.social.set_toolkit.get_audit_logger", return_value=mock_audit),
            patch(
                "tengu.tools.social.set_toolkit.resolve_tool_path",
                return_value="/usr/bin/seautomate",
            ),
            patch("tengu.tools.social.set_toolkit.rate_limited", return_value=mock_rl_ctx),
            patch("tengu.tools.social.set_toolkit.make_allowlist_from_config") as mock_allowlist,
            patch(
                "tengu.tools.social.set_toolkit.run_command",
                mock_run_command,
            ),
            patch(
                "tengu.tools.social.set_toolkit._build_answer_file",
                return_value="/tmp/set_answers.txt",
            ),
            patch("tengu.tools.social.set_toolkit.Path", mock_path_class),
        ):
            mock_allowlist.return_value.check.return_value = None

            from tengu.tools.social.set_toolkit import set_payload_generator

            await set_payload_generator(ctx, payload_type="hta", lhost="10.0.0.1", lport=8080)

        mock_run_command.assert_awaited_once()
        call_args = mock_run_command.call_args[0][0]
        assert call_args == ["/usr/bin/seautomate", "/tmp/set_answers.txt"]


# ---------------------------------------------------------------------------
# TestPayloadMenuOptions (constants)
# ---------------------------------------------------------------------------


class TestPayloadMenuOptions:
    def test_all_valid_types_have_menu_options(self):
        """Every valid payload type has a corresponding menu option."""
        from tengu.tools.social.set_toolkit import _PAYLOAD_MENU_OPTIONS, _VALID_PAYLOAD_TYPES

        for ptype in _VALID_PAYLOAD_TYPES:
            assert ptype in _PAYLOAD_MENU_OPTIONS

    def test_menu_options_are_numeric_strings(self):
        """All menu option values are numeric strings."""
        from tengu.tools.social.set_toolkit import _PAYLOAD_MENU_OPTIONS

        for ptype, option in _PAYLOAD_MENU_OPTIONS.items():
            assert option.isdigit(), f"Expected digit for {ptype}, got {option!r}"

    def test_powershell_alphanumeric_is_option_1(self):
        """powershell_alphanumeric maps to menu option 1."""
        from tengu.tools.social.set_toolkit import _PAYLOAD_MENU_OPTIONS

        assert _PAYLOAD_MENU_OPTIONS["powershell_alphanumeric"] == "1"

    def test_powershell_reverse_is_option_2(self):
        """powershell_reverse maps to menu option 2."""
        from tengu.tools.social.set_toolkit import _PAYLOAD_MENU_OPTIONS

        assert _PAYLOAD_MENU_OPTIONS["powershell_reverse"] == "2"

    def test_hta_is_option_3(self):
        """hta maps to menu option 3."""
        from tengu.tools.social.set_toolkit import _PAYLOAD_MENU_OPTIONS

        assert _PAYLOAD_MENU_OPTIONS["hta"] == "3"
