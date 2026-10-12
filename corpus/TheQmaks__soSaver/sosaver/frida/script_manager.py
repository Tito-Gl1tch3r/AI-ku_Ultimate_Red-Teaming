"""
Module for managing Frida JavaScript scripts.

Provides classes and functions for loading and preparing
Frida scripts used for library extraction.
"""

import os
from pathlib import Path
from typing import Any, Dict

from frida.core import Script, Session

from sosaver.utils.exceptions import ScriptLoadError
from sosaver.utils.logging import logger


class ScriptManager:
    """
    Class for managing Frida JavaScript scripts.

    Responsible for loading, preparing, and executing
    Frida scripts in the target process.
    """

    def __init__(self):
        """Initialize the script manager."""
        self.script_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "scripts"
        self.loaded_scripts: Dict[str, Script] = {}

    def get_script_code(self, script_name: str) -> str:
        """
        Get the JavaScript script code.

        Args:
            script_name: Script name (without .js extension)

        Returns:
            Prepared script code

        Raises:
            ScriptLoadError: If the script is not found or cannot be read
        """
        js_file_path = self.script_dir / f"{script_name}.js"

        try:
            with open(js_file_path, encoding="utf-8") as f:
                js_code = f.read()

            return js_code

        except FileNotFoundError as e:
            error_msg = f"Script {script_name}.js not found in {self.script_dir}"
            logger.error(error_msg)
            raise ScriptLoadError(error_msg, script_name) from e
        except Exception as e:
            error_msg = f"Error reading script {script_name}.js: {e}"
            logger.error(error_msg)
            raise ScriptLoadError(error_msg, script_name) from e

    def load_script(
        self,
        session: Session,
        script_name: str,
        on_message_callback: Any = None
    ) -> Script:
        """
        Load a script into a Frida session.

        Args:
            session: Frida session
            script_name: Script name (without .js extension)
            on_message_callback: Callback function for messages from the script

        Returns:
            Loaded Frida script

        Raises:
            ScriptLoadError: If the script could not be loaded
        """
        try:
            script_code = self.get_script_code(script_name)

            script = session.create_script(script_code)

            if on_message_callback:
                script.on("message", on_message_callback)

            script.load()
            self.loaded_scripts[script_name] = script

            logger.info(f"Script {script_name} loaded successfully")
            return script

        except Exception as e:
            error_msg = f"Error loading script {script_name}: {e}"
            logger.error(error_msg)
            raise ScriptLoadError(error_msg, script_name) from e


# Create a standard instance for convenience of import
script_manager = ScriptManager()
