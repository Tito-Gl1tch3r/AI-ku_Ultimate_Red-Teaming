import unittest
from unittest.mock import patch, MagicMock
from core.commands import display


class TestDisplayCommands(unittest.TestCase):

    @patch("core.commands.display.get_current_module")
    @patch("core.commands.display.printc")
    def test_show_no_module(self, mock_printc, mock_get_mod):
        mock_get_mod.return_value = None
        display.handle_show(["options"], {})
        mock_printc.assert_called_with("No module selected.", level="error")

    @patch("core.commands.display.get_current_module")
    @patch("core.commands.display.printc")
    def test_show_no_args(self, mock_printc, mock_get_mod):
        mock_get_mod.return_value = MagicMock()
        display.handle_show([], {})
        mock_printc.assert_called_with("Usage: show <options|summary>", level="warn")

    @patch("core.commands.display.get_current_module")
    @patch("builtins.print")
    def test_show_options_output(self, mock_print, mock_get_mod):
        fake_mod = MagicMock()
        fake_mod.options = {"rhost": "", "rport": "22"}
        fake_mod.required_options = ["rhost", "rport"]
        mock_get_mod.return_value = fake_mod

        display.handle_show(["options"], {})

        mock_print.assert_any_call(f"{'Option':<20} {'Value':<35} {'Required':<10}")
        mock_print.assert_any_call(f"{'rhost':<20} {'':<35} {'yes':<10}")
        mock_print.assert_any_call(f"{'rport':<20} {'22':<35} {'yes':<10}")

    @patch("core.commands.display.get_current_module")
    @patch("core.commands.display.printc")
    def test_show_summary_no_data(self, mock_printc, mock_get_mod):
        mock_get_mod.return_value = MagicMock()
        display.handle_show(["summary"], {})
        mock_printc.assert_called_with("No summary available.", level="warn")

    @patch("core.commands.display.get_current_module")
    def test_show_summary_with_data(self, mock_get_mod):
        fake_mod = MagicMock()
        mock_get_mod.return_value = fake_mod
        summary = {"dummy": "data"}

        display.handle_show(["summary"], {"last_summary": summary})
        fake_mod.print_summary.assert_called_with(summary)

    @patch("core.commands.display.list_modules_by_category")
    @patch("core.commands.display.list_plugins_by_category")
    @patch("core.commands.display.list_exploits_by_category")
    @patch("core.commands.display.get_current_module")
    @patch("core.commands.display.printc")
    def test_list_all(self, mock_printc, mock_get_mod, mock_exp, mock_plug, mock_mod):
        mock_mod.return_value = {"default": ["mod1"]}
        mock_plug.return_value = {"plugin": ["plug1"]}
        mock_exp.return_value = {"exploit": ["exp1"]}
        mock_get_mod.return_value = None

        display.handle_list(["all"], {})
        mock_printc.assert_any_call("Available modules:", level="headline")
        mock_printc.assert_any_call("  [-] mod1", level="dim")
        mock_printc.assert_any_call("Available plugins:", level="headline")
        mock_printc.assert_any_call("  [-] plug1", level="dim")
        mock_printc.assert_any_call("Available exploits:", level="headline")
        mock_printc.assert_any_call("  [-] exp1", level="dim")

    @patch("core.commands.display.get_current_module", return_value=None)
    @patch("core.commands.display.list_modules", return_value=["mod_alpha", "mod_beta"])
    @patch("core.commands.display.printc")
    def test_search_keyword_matches(
        self, mock_printc, mock_list_modules, mock_get_current_module
    ):
        from core.commands.display import handle_search

        handle_search(["alpha"], {})

        # print("Calls made to printc:", mock_printc.call_args_list)

        mock_printc.assert_any_call("  - mod_alpha", level="info")
        mock_printc.assert_called_with("  - mod_alpha", level="info")

    @patch("core.commands.display.printc")
    def test_search_no_args(self, mock_printc):
        display.handle_search([], {})
        mock_printc.assert_called_with("Usage: search <keyword>", level="warn")
