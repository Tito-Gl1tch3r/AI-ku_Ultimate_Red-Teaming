import requests
from payloads.xss_payloads import ALL_PAYLOADS, PAYLOADS
from configs.settings import TIMEOUT

class Scanner:
    def __init__(self, target_url, category=None):
        self.target_url = target_url
        self.category = category
        if category and category in PAYLOADS:
            self.payloads = PAYLOADS[category]
        else:
            self.payloads = ALL_PAYLOADS

    def test_payload(self, payload, param='q'):
        """Test a single payload against the target URL with specified parameter"""
        try:
            # Test with GET parameter
            response = requests.get(self.target_url, params={param: payload}, timeout=TIMEOUT)
            if payload in response.text or payload.replace(' ', '') in response.text.replace(' ', ''):
                return True, response.status_code, response.text[:500]
            
            # Also test with POST data
            response = requests.post(self.target_url, data={param: payload}, timeout=TIMEOUT)
            if payload in response.text or payload.replace(' ', '') in response.text.replace(' ', ''):
                return True, response.status_code, response.text[:500]
                
            return False, response.status_code, None
        except requests.exceptions.Timeout:
            print(f"Timeout testing payload: {payload}")
            return False, 0, None
        except requests.exceptions.RequestException as e:
            print(f"Error testing payload: {payload}, Error: {e}")
            return False, 0, None

    def test_payload_in_path(self, payload):
        """Test payload injected into the URL path"""
        try:
            test_url = f"{self.target_url}/{payload}"
            response = requests.get(test_url, timeout=TIMEOUT)
            if payload in response.text:
                return True, response.status_code, response.text[:500]
            return False, response.status_code, None
        except requests.exceptions.RequestException as e:
            print(f"Error testing path injection: {e}")
            return False, 0, None

    def check_reflection(self, payload):
        """Check if payload is reflected in response"""
        results = []
        
        # Test common parameters
        common_params = ['q', 'search', 'query', 'input', 'text', 'keyword', 'id', 'name', 'page']
        for param in common_params:
            is_vulnerable, status_code, content = self.test_payload(payload, param)
            if is_vulnerable:
                results.append({
                    'parameter': param,
                    'method': 'GET/POST',
                    'status_code': status_code,
                    'vulnerable': True
                })
        
        # Test URL path injection
        is_vulnerable, status_code, content = self.test_payload_in_path(payload)
        if is_vulnerable:
            results.append({
                'parameter': 'URL_PATH',
                'method': 'PATH',
                'status_code': status_code,
                'vulnerable': True
            })
        
        return results

    def run_scan(self, verbose=False):
        """Run the XSS scan with optional verbose output"""
        results = []
        total_payloads = len(self.payloads)
        
        if verbose:
            print(f"\nStarting XSS scan on {self.target_url}")
            print(f"Testing {total_payloads} payloads...")
            if self.category:
                print(f"Category: {self.category}")
            print("-" * 60)
        
        for i, payload in enumerate(self.payloads, 1):
            if verbose:
                print(f"[{i}/{total_payloads}] Testing: {payload[:50]}...")
            
            reflection_results = self.check_reflection(payload)
            
            if reflection_results:
                for result in reflection_results:
                    results.append({
                        'payload': payload,
                        'category': self.category or 'all',
                        'parameter': result['parameter'],
                        'method': result['method'],
                        'status_code': result['status_code'],
                        'vulnerable': True
                    })
                if verbose:
                    print(f"  ✓ VULNERABLE - Parameter: {reflection_results[0]['parameter']}")
            elif verbose:
                print(f"  ✗ Safe")
        
        if verbose:
            print("-" * 60)
            vulnerable_count = len([r for r in results if r['vulnerable']])
            print(f"\nScan completed. Found {vulnerable_count} vulnerabilities out of {total_payloads} tests.")
        
        return results
