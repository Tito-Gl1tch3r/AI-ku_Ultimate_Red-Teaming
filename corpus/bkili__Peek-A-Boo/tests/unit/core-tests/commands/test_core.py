# tests/test_core_commands.py
import unittest
from unittest.mock import patch
import os


class TestCoreCommands(unittest.TestCase):

    @patch("core.commands.core.printc")
    @patch("sys.exit")
    def test_handle_exit(self, mock_exit, mock_printc):
        from core.commands.core import handle_exit

        handle_exit([], {})
        mock_printc.assert_called_with("Exiting...", level="warn")
        mock_exit.assert_called_once()

    @patch("core.commands.core.printc")
    @patch(
        "core.registry.COMMAND_HANDLERS",
        new={"exit": None, "help": None, "clear": None},
    )
    def test_handle_help(self, mock_printc):
        from core.commands.core import handle_help

        with patch("builtins.print") as mock_builtin_print:
            handle_help([], {})
            mock_printc.assert_called_with("Available commands:", level="info")
            mock_builtin_print.assert_any_call("  - clear")
            mock_builtin_print.assert_any_call("  - exit")
            mock_builtin_print.assert_any_call("  - help")

    @patch("os.system")
    def test_handle_clear(self, mock_system):
        from core.commands.core import handle_clear

        handle_clear([], {})
        expected_command = "cls" if os.name == "nt" else "clear"
        mock_system.assert_called_with(expected_command)
