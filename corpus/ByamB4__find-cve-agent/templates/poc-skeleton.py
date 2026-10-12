#!/usr/bin/env python3
"""
CVE-CANDIDATE: {{VULN_TYPE}} in {{PACKAGE_NAME}}
CWE: CWE-{{NUMBER}}
CVSS: {{SCORE}} {{SEVERITY}}
Affected Version: {{VERSION}}
Tested On: Python {{PYTHON_VERSION}}

Description: {{One-line description}}

Usage: python3 poc_{{vuln_type}}.py
"""

import {{package_name}}


def main():
    # Step 1: Setup
    print('[*] Setting up test environment...')

    # Step 2: Craft malicious input
    print('[*] Crafting malicious input...')
    payload = '{{PAYLOAD}}'

    # Step 3: Trigger the vulnerability
    print('[*] Triggering vulnerability...')
    try:
        result = {{package_name}}.vulnerable_function(payload)

        # Step 4: Verify exploitation
        print('[+] Vulnerability triggered successfully!')
        print(f'[+] Evidence: {result}')
    except Exception as e:
        print(f'[+] Vulnerability triggered: {e}')

    # Step 5: Cleanup
    print('[*] Done.')


if __name__ == '__main__':
    main()
