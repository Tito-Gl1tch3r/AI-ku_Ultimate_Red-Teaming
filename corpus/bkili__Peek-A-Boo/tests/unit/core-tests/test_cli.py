# tests/test_cli.py
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO


class TestStartCLI(unittest.TestCase):
    @patch("core.cli.PromptSession")
    @patch("core.cli.printc")
    @patch("core.cli.COMMAND_HANDLERS", new_callable=dict)
    def test_start_cli_basic_commands(
        self, mock_handlers, mock_printc, mock_prompt_session
    ):
        # Arrange
        mock_handler_func = MagicMock()
        mock_handlers.update({"help": mock_handler_func, "exit": mock_handler_func})

        mock_prompt = MagicMock()
        mock_prompt.prompt.side_effect = ["help", "exit", KeyboardInterrupt()]
        mock_prompt_session.return_value = mock_prompt

        # Act
        from core.cli import start_cli

        with patch("sys.stdout", new=StringIO()):
            start_cli()

        # Assert
        self.assertGreaterEqual(mock_handler_func.call_count, 2)
        mock_printc.assert_any_call(
            "Welcome to Peek-A-Boo CLI. Type 'help' to see available commands.",
            level="headline",
        )
        mock_printc.assert_any_call("Exiting...", level="warn")
