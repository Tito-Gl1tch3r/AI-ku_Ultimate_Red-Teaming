"""
Module for generating file paths.

Provides the PathGenerator class responsible for creating
correct paths for saving dumped libraries.
"""

import os
import re
from typing import Set


class PathGenerator:
    """
    Path generator for library dump files.

    Responsible for creating safe and unique file names
    for saving dumped libraries.
    """

    # Characters that cannot be used in file names
    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'

    def __init__(self, output_dir: str):
        """
        Initialize the path generator.

        Args:
            output_dir: Directory for saving files
        """
        self.output_dir = os.path.abspath(output_dir)
        self._used_paths: Set[str] = set()

        # Create the directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Clean the filename of invalid characters.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        # Replace invalid characters with underscores
        sanitized = re.sub(self.INVALID_FILENAME_CHARS, '_', filename)

        # Limit filename length
        if len(sanitized) > 100:
            # If the filename is too long, truncate it
            sanitized = sanitized[:100]

        return sanitized

    def get_unique_save_path(self, module_name: str, base_address: str, is_partial: bool = False) -> str:
        """
        Generate a unique path for saving a module.

        Args:
            module_name: Module name
            base_address: Module base address in memory
            is_partial: Is the dump partial

        Returns:
            Absolute path to the file for saving
        """
        # Clean the filename of invalid characters
        sanitized_name = self._sanitize_filename(module_name)

        # Form the filename with the base address
        filename_base = f"{sanitized_name}_{base_address.replace('0x', '')}"

        # Add a suffix if this is a partial dump
        if is_partial:
            filename_base += "_partial"

        # Add a number for uniqueness
        counter = 1
        while True:
            filename = f"{filename_base}_{counter}.bin"
            full_path = os.path.join(self.output_dir, filename)

            # Check if a file with this name already exists
            if full_path not in self._used_paths and not os.path.exists(full_path):
                self._used_paths.add(full_path)
                return full_path

            counter += 1
