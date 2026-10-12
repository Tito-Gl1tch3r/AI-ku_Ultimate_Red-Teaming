"""Text replacement utilities"""
import logging
import re
from typing import Dict, Optional


class TextReplacer:
    """Handles text replacement operations with proper escaping"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_replacements(self, text: str, replacements: Optional[Dict],
                           reverse: bool = False) -> str:
        """Apply keyword replacements to text"""
        if not replacements:
            return text

        # Reverse the dictionary if needed
        if reverse:
            replacements = {v: k for k, v in replacements.items()}

        # Sort by length to avoid substring issues
        sorted_items = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)

        # Build regex pattern
        escaped_keys = [re.escape(key) for key, _ in sorted_items]
        pattern = '|'.join(escaped_keys)

        if not pattern:
            return text

        # Create replacement mapping
        mapping = dict(sorted_items)

        def replace_match(match):
            return mapping[match.group(0)]

        try:
            result = re.sub(pattern, replace_match, text)
            self.logger.debug(f"Applied {len(replacements)} replacements")
            return result
        except Exception as e:
            self.logger.error(f"Error in text replacement: {e}")
            return text

    def merge_replacements(self, *dicts: Dict) -> Dict:
        """Merge multiple replacement dictionaries"""
        result = {}
        for d in dicts:
            if d:
                result.update(d)
        self.logger.debug(f"Merged {len(dicts)} dictionaries into {len(result)} replacements")
        return result
