#!/usr/bin/env python3
"""
Test script for Bounty Hunter Pro security modules
"""

from security_modules import VulnerabilityScanner
import json

def test_scanner():
    """Test the vulnerability scanner"""
    print("🎯 Testing Bounty Hunter Pro Security Scanner")
    print("="*50)
    
    scanner = VulnerabilityScanner()
    
    # Test with a safe target
    test_url = "https://httpbin.org"
    
    print(f"Testing URL: {test_url}")
    print("Starting scan...")
    
    def progress_callback(message):
        print(f"[PROGRESS] {message}")
    
    try:
        results = scanner.full_scan(test_url, progress_callback)
        
        print("\n✅ Scan completed successfully!")
        print(f"Status: {results['scan_status']}")
        print(f"Vulnerabilities found: {len(results['vulnerabilities'])}")
        print(f"Directories found: {len(results['directories'])}")
        print(f"Information gathered: {len(results['information'])} items")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        return False

if __name__ == "__main__":
    success = test_scanner()
    if success:
        print("\n🎉 All tests passed! The scanner is ready to use.")
    else:
        print("\n💥 Tests failed! Please check the error messages above.")

