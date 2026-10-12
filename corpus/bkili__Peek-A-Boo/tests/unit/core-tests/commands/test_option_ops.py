import unittest
from unittest.mock import patch, MagicMock
from core.commands.option_ops import handle_set


class TestOptionOpsCommand(unittest.TestCase):

    @patch("core.commands.option_ops.printc")
    @patch("core.commands.option_ops.get_current_module")
    def test_handle_set_success(self, mock_get_module, mock_printc):
        # Arrange
        mock_module = MagicMock()
        mock_get_module.return_value = mock_module
        args = ["example_option", "value"]
        shared_data = {}

        # Act
        handle_set(args, shared_data)

        # Assert
        mock_module.set_option.assert_called_with("example_option", "value")
        mock_printc.assert_any_call("[+] example_option set to value", level="success")

    @patch("core.commands.option_ops.printc")
    @patch("core.commands.option_ops.get_current_module", return_value=None)
    def test_handle_set_no_module_selected(self, mock_get_module, mock_printc):
        handle_set(["some_option", "value"], {})
        mock_printc.assert_called_with("No module selected.", level="error")

    @patch("core.commands.option_ops.printc")
    @patch("core.commands.option_ops.get_current_module")
    def test_handle_set_no_args(self, mock_get_module, mock_printc):
        mock_get_module.return_value = MagicMock()
        handle_set([], {})
        mock_printc.assert_called_with("Usage: set <option> [value]", level="warn")
