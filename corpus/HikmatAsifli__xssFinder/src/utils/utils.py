import logging

def setup_logging():
    # Ensure logs directory exists
    import os
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(filename='logs/scan.log', 
                        format='%(asctime)s %(message)s', 
                        level=logging.INFO)

def log_scan_results(results):
    setup_logging()
    for result in results:
        payload = result['payload']
        vulnerable = result['vulnerable']
        parameter = result.get('parameter', 'N/A')
        method = result.get('method', 'N/A')
        status_code = result.get('status_code', 'N/A')
        logging.info(f"Payload: {payload}, Vulnerable: {vulnerable}, Parameter: {parameter}, Method: {method}, Status: {status_code}")

def sanitize_input(input_string):
    """Basic input sanitization utility"""
    if not input_string:
        return ""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';']
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')
    return input_string

def validate_url(url):
    """Validate URL format"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None
