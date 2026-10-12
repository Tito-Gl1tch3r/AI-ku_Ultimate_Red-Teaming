import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scanner import Scanner
from payloads.xss_payloads import PAYLOADS, ALL_PAYLOADS

class TestScanner(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.test_url = "http://example.com"
        self.scanner = Scanner(self.test_url)
    
    def test_scanner_initialization(self):
        """Test scanner initializes correctly"""
        scanner = Scanner("http://test.com")
        self.assertEqual(scanner.target_url, "http://test.com")
        self.assertEqual(scanner.category, None)
        self.assertEqual(len(scanner.payloads), len(ALL_PAYLOADS))
    
    def test_scanner_with_category(self):
        """Test scanner with specific category"""
        scanner = Scanner("http://test.com", category="basic")
        self.assertEqual(scanner.category, "basic")
        self.assertEqual(len(scanner.payloads), len(PAYLOADS["basic"]))
    
    def test_payload_structure(self):
        """Test that payload structure is correct"""
        result = self.scanner.test_payload("<script>alert('XSS')</script>")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)  # (is_vulnerable, status_code, content)
    
    def test_payload_return_types(self):
        """Test payload returns correct types"""
        is_vulnerable, status_code, content = self.scanner.test_payload("<script>alert('XSS')</script>")
        self.assertIsInstance(is_vulnerable, bool)
        self.assertIsInstance(status_code, int)
    
    def test_run_scan_returns_list(self):
        """Test that run_scan returns a list"""
        results = self.scanner.run_scan()
        self.assertIsInstance(results, list)
    
    def test_run_scan_result_structure(self):
        """Test that scan results have correct structure"""
        results = self.scanner.run_scan()
        if results:  # If there are any results
            result = results[0]
            self.assertIn('payload', result)
            self.assertIn('vulnerable', result)
            self.assertIn('category', result)
    
    def test_payload_categories_exist(self):
        """Test that payload categories are defined"""
        self.assertIn("basic", PAYLOADS)
        self.assertIn("encoded", PAYLOADS)
        self.assertIn("event_handlers", PAYLOADS)
        self.assertIn("filter_bypass", PAYLOADS)
    
    def test_all_payloads_not_empty(self):
        """Test that payloads list is not empty"""
        self.assertGreater(len(ALL_PAYLOADS), 0)

if __name__ == '__main__':
    unittest.main()
