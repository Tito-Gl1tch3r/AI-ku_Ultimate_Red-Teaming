import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.utils import log_scan_results, sanitize_input, validate_url

class TestUtils(unittest.TestCase):

    def test_log_scan_results(self):
        """Test logging function with sample data"""
        results = [
            {
                'payload': "<script>alert('XSS')</script>",
                'vulnerable': True,
                'parameter': 'q',
                'method': 'GET/POST',
                'status_code': 200
            }
        ]
        log_scan_results(results)
        # Check if the log file exists and contains the right log
        with open('logs/scan.log', 'r') as log_file:
            logs = log_file.read()
            self.assertIn("Payload: <script>alert('XSS')</script>", logs)
            self.assertIn("Vulnerable: True", logs)
            self.assertIn("Parameter: q", logs)
    
    def test_sanitize_input_removes_dangerous_chars(self):
        """Test that sanitize_input removes dangerous characters"""
        dangerous_input = "<script>alert('XSS')</script>"
        sanitized = sanitize_input(dangerous_input)
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
        self.assertNotIn("'", sanitized)
    
    def test_sanitize_input_empty_string(self):
        """Test sanitize_input with empty string"""
        self.assertEqual(sanitize_input(""), "")
        self.assertEqual(sanitize_input(None), "")
    
    def test_sanitize_input_safe_string(self):
        """Test sanitize_input preserves safe strings"""
        safe_input = "Hello World 123"
        sanitized = sanitize_input(safe_input)
        self.assertEqual(safe_input, sanitized)
    
    def test_validate_url_valid_http(self):
        """Test URL validation with valid HTTP URL"""
        self.assertTrue(validate_url("http://example.com"))
        self.assertTrue(validate_url("http://example.com/path"))
        self.assertTrue(validate_url("http://example.com:8080/path"))
    
    def test_validate_url_valid_https(self):
        """Test URL validation with valid HTTPS URL"""
        self.assertTrue(validate_url("https://example.com"))
        self.assertTrue(validate_url("https://sub.example.com/path"))
    
    def test_validate_url_localhost(self):
        """Test URL validation with localhost"""
        self.assertTrue(validate_url("http://localhost"))
        self.assertTrue(validate_url("http://localhost:8080"))
    
    def test_validate_url_ip_address(self):
        """Test URL validation with IP address"""
        self.assertTrue(validate_url("http://192.168.1.1"))
        self.assertTrue(validate_url("http://127.0.0.1:8080"))
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs"""
        self.assertFalse(validate_url("not-a-url"))
        self.assertFalse(validate_url("ftp://example.com"))
        self.assertFalse(validate_url(""))

if __name__ == '__main__':
    unittest.main()
