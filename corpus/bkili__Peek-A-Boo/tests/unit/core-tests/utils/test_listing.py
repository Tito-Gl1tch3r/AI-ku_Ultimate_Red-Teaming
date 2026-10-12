import unittest
from unittest.mock import patch, MagicMock
from core.utils import listing


class TestListingUtils(unittest.TestCase):

    @patch("core.utils.listing.importlib.import_module")
    @patch("core.utils.listing.list_modules", return_value=["pb_alpha", "pb_beta"])
    def test_list_modules_by_category(self, mock_list_modules, mock_import_module):
        # Mock module instances
        fake_module = MagicMock()
        fake_module.Module.return_value.category = "osint"
        mock_import_module.return_value = fake_module

        result = listing.list_modules_by_category()
        self.assertEqual(set(result["osint"]), {"pb_alpha", "pb_beta"})

    @patch("core.utils.listing.importlib.import_module")
    @patch("core.utils.listing.list_plugins", return_value=["plugin_a"])
    def test_list_plugins_by_category(self, mock_list_plugins, mock_import_module):
        fake_plugin = MagicMock()
        fake_plugin.Module.return_value.category = "utility"
        mock_import_module.return_value = fake_plugin

        result = listing.list_plugins_by_category()
        self.assertIn("utility", result)
        self.assertIn("plugin_a", result["utility"])

    @patch("core.utils.listing.importlib.import_module")
    @patch("core.utils.listing.list_exploits", return_value=["exp_cve"])
    def test_list_exploits_by_category(self, mock_list_exploits, mock_import_module):
        fake_exploit = MagicMock()
        fake_exploit.Module.return_value.category = "privilege_escalation"
        mock_import_module.return_value = fake_exploit

        result = listing.list_exploits_by_category()
        self.assertIn("privilege_escalation", result)
        self.assertIn("exp_cve", result["privilege_escalation"])
