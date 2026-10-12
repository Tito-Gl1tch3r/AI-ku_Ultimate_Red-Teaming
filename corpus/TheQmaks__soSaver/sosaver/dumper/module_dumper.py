"""
Main module for dumping libraries from Android applications.

Provides the main ModuleDumper class that manages
the process of extracting libraries from Android application memory.
"""

import sys
from typing import Any, Dict, Optional, Union

from frida.core import Script, Session

from sosaver.device.connector import DeviceConnector
from sosaver.dumper.dump_manager import ModuleDumpManager

# Import required classes
from sosaver.dumper.message_handler import MessageHandler
from sosaver.frida.script_manager import script_manager
from sosaver.fs.file_manager import FileManager
from sosaver.utils.exceptions import ScriptLoadError, SOSaverError
from sosaver.utils.logging import LogContext, logger


class ModuleDumper:
    """
    Main class for dumping .so files from Android applications.

    Manages the process of connecting to the device, loading the script
    and saving the extracted libraries.
    """

    def __init__(
        self,
        target: Union[str, int],
        output_folder: str = "dumped_so"
    ):
        """
        Initialize the module dumper.

        Args:
            target: Target process name or PID
            output_folder: Path to the directory for saving dumped libraries
        """
        self.target = target
        self.session: Optional[Session] = None
        self.script: Optional[Script] = None

        # Initialize and bind components
        self.device_connector = DeviceConnector(target)

        # Create components, following the correct order of dependencies
        self.file_manager = FileManager(output_folder)
        self.path_generator = self.file_manager.path_generator
        self.dump_manager = ModuleDumpManager(self.path_generator)

        # Create a message handler and set its dump manager
        self.message_handler = MessageHandler()
        self.message_handler.set_dump_manager(self.dump_manager)

        # Set the dependency in file_manager
        self.file_manager.set_dump_manager(self.dump_manager)

        logger.info(f"Output directory for files: {self.file_manager.output_folder}",
                   context=LogContext(logger.COMPONENT_CORE))

    def run(self) -> None:
        """
        Run the module dumper.

        Connects to the device, loads the script and waits for completion.
        """
        try:
            # Step 1: Connect to the device and process
            self._connect_to_device()

            # Step 2: Load and run the Frida script
            self._load_and_run_script()

            # Step 3: Wait for completion (interrupted by the user)
            logger.info("Dumper started. Press Ctrl+C to stop.",
                       context=LogContext(logger.COMPONENT_CORE))
            try:
                sys.stdin.read()
            except KeyboardInterrupt:
                logger.info("\nCtrl+C detected. Exiting...",
                           context=LogContext(logger.COMPONENT_CORE))
        except SOSaverError as e:
            logger.error(f"soSaver error: {e}",
                        context=LogContext(logger.COMPONENT_CORE))
        except Exception as e:
            logger.error(f"Unexpected error: {e}",
                        context=LogContext(logger.COMPONENT_CORE))
        finally:
            self.cleanup_resources()

    def _connect_to_device(self) -> None:
        """
        Connect to the device and process.

        Raises:
            SOSaverError: If connection fails
        """
        logger.info(f"Connecting to process {self.target}...",
                   context=LogContext(logger.COMPONENT_DEVICE))
        self.session = self.device_connector.attach_to_process()
        self.session.on("detached", self._on_detached)

    def _load_and_run_script(self) -> None:
        """
        Load and run the Frida script.

        Raises:
            ScriptLoadError: If script loading fails
        """
        logger.info("Loading script...",
                   context=LogContext(logger.COMPONENT_FRIDA))
        self.script = self._load_script()

    def _load_script(self) -> Script:
        """
        Load the Frida script for dumping modules.

        Returns:
            Loaded Frida script

        Raises:
            ScriptLoadError: If script loading fails
        """
        if self.session is None:
            raise ScriptLoadError("Session must be initialized before loading the script")

        try:
            # Load the script using the message handler
            script = script_manager.load_script(
                self.session,
                "agent",
                self.on_message
            )

            logger.info("Script loaded successfully",
                       context=LogContext(logger.COMPONENT_FRIDA))
            return script

        except Exception as e:
            error_msg = f"Error loading script: {e}"
            logger.error(error_msg, context=LogContext(logger.COMPONENT_FRIDA))
            raise ScriptLoadError(error_msg) from e

    def on_message(self, message: Dict[str, Any], data: Optional[bytes]) -> None:
        """
        Handle messages from the Frida script.

        Delegates message handling to a specialized handler.

        Args:
            message: Message from the script
            data: Binary data, if any
        """
        self.message_handler.handle_message(message, data)

    def _on_detached(self, reason: str, crash: Optional[Any]) -> None:
        """
        Handle the detachment of the Frida session.

        Args:
            reason: Reason for detachment
            crash: Crash information, if any
        """
        logger.warning(f"Session detached! Reason: {reason}",
                      context=LogContext(logger.COMPONENT_DEVICE))
        if crash:
            logger.error(f"Process crashed: {crash}",
                        context=LogContext(logger.COMPONENT_DEVICE))

        # Close all active dump files
        self.file_manager.cleanup_active_dumps(log_incomplete=True)

        logger.warning("Exiting due to session detachment",
                      context=LogContext(logger.COMPONENT_CORE))

    def cleanup_resources(self) -> None:
        """Clean up resources before exiting."""
        # Close all active dump files
        self.file_manager.cleanup_active_dumps()

        # Unload the script
        if self.script:
            try:
                self.script.unload()
                logger.debug("Script unloaded",
                           context=LogContext(logger.COMPONENT_FRIDA))
            except Exception as e:
                logger.warning(f"Error unloading script: {e}",
                              context=LogContext(logger.COMPONENT_FRIDA))
            self.script = None

        # Detach the session
        if self.session:
            try:
                self.session.detach()
                logger.debug("Session detached",
                           context=LogContext(logger.COMPONENT_DEVICE))
            except Exception as e:
                logger.warning(f"Error detaching session: {e}",
                              context=LogContext(logger.COMPONENT_DEVICE))
            self.session = None

        logger.info("Resources cleaned up",
                   context=LogContext(logger.COMPONENT_CORE))

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the results.

        Returns:
            Dictionary with statistics
        """
        stats = self.file_manager.get_dump_stats()

        return {
            "dumped_modules_count": stats["dumped_modules_count"],
            "files_count": stats["files_count"],
            "total_size_mb": stats["total_size_mb"]
        }
