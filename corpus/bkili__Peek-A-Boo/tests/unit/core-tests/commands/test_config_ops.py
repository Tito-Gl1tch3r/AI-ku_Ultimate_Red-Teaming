import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from core.commands.config_ops import handle_save, handle_load


class TestConfigOpsCommands(unittest.TestCase):

    @patch("core.commands.config_ops.printc")
    @patch("core.commands.config_ops.get_current_module")
    @patch("core.commands.config_ops.open", new_callable=mock_open)
    @patch("core.commands.config_ops.Path.mkdir")
    def test_handle_save_valid(
        self, mock_mkdir, mock_open_file, mock_get_module, mock_printc
    ):
        # Arrange
        mod = MagicMock()
        mod.options = {"a": "b"}
        mock_get_module.return_value = mod
        args = ["config", "myconfig.json"]
        expected_path = Path("configs/myconfig.json")

        # Act
        handle_save(args, shared_data={})

        # Assert
        mock_open_file.assert_called_with(mock_open_file.call_args[0][0], "w")
        mock_printc.assert_called_with(
            f"Configuration saved to {expected_path}", level="success"
        )

    @patch("core.commands.config_ops.printc")
    def test_handle_save_invalid_usage(self, mock_printc):
        handle_save([], shared_data={})
        mock_printc.assert_called_with("Usage: save config <filename>", level="warn")

    @patch("core.commands.config_ops.printc")
    @patch("core.commands.config_ops.get_current_module")
    @patch("core.commands.config_ops.Path.exists", return_value=True)
    @patch(
        "core.commands.config_ops.open",
        new_callable=mock_open,
        read_data='{"opt1": "val1"}',
    )
    def test_handle_load_valid_config(
        self, mock_open_file, mock_exists, mock_get_module, mock_printc
    ):
        mock_module = MagicMock()
        mock_get_module.return_value = mock_module
        args = ["config", "myconfig.json"]
        expected_path = Path("configs/myconfig.json")

        handle_load(args, shared_data={})
        mock_module.set_option.assert_called_with("opt1", "val1")
        mock_printc.assert_called_with(
            f"Configuration loaded from {expected_path}", level="success"
        )

    @patch("core.commands.config_ops.printc")
    def test_handle_load_invalid_args(self, mock_printc):
        handle_load([], shared_data={})
        mock_printc.assert_called_with(
            "Usage: load <config|module> <value>", level="warn"
        )

    @patch("core.commands.config_ops.printc")
    @patch("core.commands.config_ops.get_current_module", return_value=None)
    def test_handle_load_no_module(self, mock_get_module, mock_printc):
        args = ["config", "missing.json"]
        handle_load(args, shared_data={})
        mock_printc.assert_called_with(
            "No module selected. Use a module before loading config.", level="warn"
        )

    @patch("core.commands.config_ops.printc")
    @patch("core.commands.config_ops.get_current_module")
    @patch("core.commands.config_ops.Path.exists", return_value=False)
    def test_handle_load_file_not_found(
        self, mock_exists, mock_get_module, mock_printc
    ):
        mock_get_module.return_value = MagicMock()
        args = ["config", "notfound.json"]
        handle_load(args, shared_data={})
        mock_printc.assert_called_with("File not found.", level="error")
