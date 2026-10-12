import unittest
from unittest.mock import patch
from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completion
from core.completer import SmartCompleter


class TestSmartCompleter(unittest.TestCase):
    @patch("core.completer.get_current_module")
    @patch("core.completer.list_modules")
    @patch("core.completer.list_plugins")
    @patch("core.completer.list_exploits")
    def test_update_nested_creates_expected_keys(
        self, mock_exploits, mock_plugins, mock_modules, mock_get_current
    ):
        mock_modules.return_value = ["mod1"]
        mock_plugins.return_value = ["plug1"]
        mock_exploits.return_value = ["exp1"]
        mock_get_current.return_value = None

        completer = SmartCompleter()
        completer.update_nested()

        completions = list(completer.base_completer.get_completions(Document(""), None))
        keywords = [c.text for c in completions]

        expected = {
            "exit",
            "help",
            "use",
            "info",
            "list",
            "search",
            "run",
            "reload",
            "save",
            "load",
            "show",
            "set",
        }
        self.assertTrue(expected.issubset(set(keywords)))

    @patch("core.completer.PathCompleter.get_completions")
    def test_load_config_completion_calls_path_completer(self, mock_path_completions):
        mock_path_completions.return_value = [Completion("configs/sample.json")]

        completer = SmartCompleter()
        doc = Document("load config samp")
        result = list(completer.get_completions(doc, None))

        self.assertIn("configs/sample.json", [c.text for c in result])
        mock_path_completions.assert_called_once()

    @patch("core.completer.get_current_module")
    @patch("core.completer.list_modules")
    @patch("core.completer.list_plugins")
    @patch("core.completer.list_exploits")
    def test_generic_completion(
        self, mock_exploits, mock_plugins, mock_modules, mock_get_current
    ):
        mock_modules.return_value = ["mod1"]
        mock_plugins.return_value = []
        mock_exploits.return_value = []
        mock_get_current.return_value = None

        completer = SmartCompleter()
        doc = Document("use m")
        completions = list(completer.get_completions(doc, None))

        self.assertIn("mod1", [c.text for c in completions])
