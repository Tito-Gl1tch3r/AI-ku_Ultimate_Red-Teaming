"""Claude API client with retry logic"""
import json
import logging
import time
from typing import Optional, Dict

import requests


class ClaudeAPIClient:
    """Claude API client with retry logic and error handling"""

    def __init__(self, api_key: str, api_url: str, max_retries: int = 3):
        self.api_key = api_key
        self.api_url = api_url
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })

    def call_with_retry(self,
                        payload: Dict,
                        interval: float = 2.0) -> Optional[Dict]:
        """Call API with exponential backoff retry"""

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = interval * (2 ** (attempt - 1))  # Exponential backoff
                    self.logger.info(f"Retrying API call (attempt {attempt + 1}/{self.max_retries}) "
                                     f"after {wait_time}s...")
                    time.sleep(wait_time)

                response = self.session.post(
                    self.api_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()
                self.logger.info(f"API call successful on attempt {attempt + 1}")
                return data

            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed on attempt {attempt + 1}: {e}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response on attempt {attempt + 1}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")

        self.logger.error(f"All {self.max_retries} API attempts failed")
        return None

    def get_safe_equivalents(self, harmful_prompt: str, rejected_cot: str,
                             template: str) -> Optional[Dict]:
        """Get safe equivalents for a harmful prompt"""
        payload = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 512,
            "messages": [
                {"role": "user",
                 "content": template.format(harmful=harmful_prompt, reason=rejected_cot)}
            ]
        }

        response = self.call_with_retry(payload)
        if not response:
            return None

        return self._parse_json_response(response)

    def get_cot_safe_equivalents(self, harmful_prompt: str, safe_prompt: str,
                                 safe_cot: str, template: str) -> Optional[Dict]:
        """Get safe equivalents for chain of thought"""
        payload = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 512,
            "messages": [
                {"role": "user",
                 "content": template.format(
                     safe=safe_prompt,
                     harmful=harmful_prompt,
                     safe_cot=safe_cot
                 )}
            ]
        }

        response = self.call_with_retry(payload)
        if not response:
            return None

        return self._parse_json_response(response)

    def truncate_cot(self, cot: str, template: str) -> str:
        """Truncate chain of thought"""
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": template.format(COT=cot)}
            ]
        }

        response = self.call_with_retry(payload)
        if not response:
            self.logger.warning("Failed to truncate CoT, returning original")
            return cot

        try:
            return response["content"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            self.logger.error(f"Failed to extract truncated CoT from response: {e}")
            return cot

    def _parse_json_response(self, response: Dict) -> Optional[Dict]:
        """Parse JSON from API response"""
        try:
            text_content = response["content"][0]["text"]
            if not text_content:
                self.logger.warning("Empty response text from API")
                return None

            # Clean up JSON formatting
            text_content = text_content.strip()
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            elif text_content.startswith("```"):
                text_content = text_content[3:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]

            parsed = json.loads(text_content.strip())
            self.logger.debug(f"Successfully parsed JSON with {len(parsed)} items")
            return parsed

        except (KeyError, IndexError) as e:
            self.logger.error(f"Unexpected response structure: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return None
