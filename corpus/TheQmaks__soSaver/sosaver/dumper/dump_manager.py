"""
Module for managing module dumps from Android processes.

Provides a central point for coordinating the dumping of modules,
with file management and progress tracking.
"""

import os
import time
from typing import Any, BinaryIO, Dict

from sosaver.fs.path_generator import PathGenerator
from sosaver.utils.logging import LogContext, logger


class ModuleDumpManager:
    """
    Module dump manager.

    Responsible for creating, writing and completing module dumps.
    Manages active files and dump progress.
    """

    def __init__(self, path_generator: PathGenerator):
        """
        Initialize the dump manager.

        Args:
            path_generator: Path generator for files
        """
        self.path_generator = path_generator
        self.active_dumps: Dict[str, Dict[str, Any]] = {}

    def start_module_dump(self, module_name: str, base_address: str, module_size: int, is_partial: bool = False) -> str:
        """
        Start writing a module dump.

        Args:
            module_name: Module name
            base_address: Module base address
            module_size: Module size in bytes
            is_partial: Whether the dump is partial

        Returns:
            Path to the file where the dump will be written

        Raises:
            IOError: If failed to create the file
        """
        module_context = LogContext(logger.COMPONENT_MODULE, module_name)

        # Get a unique path for saving
        save_path = self.path_generator.get_unique_save_path(module_name, base_address, is_partial)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        try:
            # Open the file for writing
            dump_file = open(save_path, 'wb')

            # Add dump information to active dumps
            self.active_dumps[module_name] = {
                "file": dump_file,
                "path": save_path,
                "size": module_size,
                "received": 0,
                "start_time": time.time()
            }

            return save_path

        except Exception as e:
            error_msg = f"Failed to create file for dump: {e}"
            logger.error(error_msg, context=module_context)
            raise OSError(error_msg) from e

    def write_module_chunk(self, module_name: str, data: bytes, offset: int, chunk_size: int) -> None:
        """
        Write a part of the module data.

        Args:
            module_name: Module name
            data: Data to write
            offset: Offset from the beginning of the file
            chunk_size: Size of the data part

        Raises:
            ValueError: If the module is not found in active dumps
            IOError: If failed to write data
        """
        module_context = LogContext(logger.COMPONENT_MODULE, module_name)

        # Check if the module is active
        if module_name not in self.active_dumps:
            error_msg = f"Module {module_name} not found in active dumps"
            logger.error(error_msg, context=module_context)
            raise ValueError(error_msg)

        dump_info = self.active_dumps[module_name]
        dump_file = dump_info["file"]
        expected_size = dump_info["size"]

        try:
            # Move to the desired position in the file
            dump_file.seek(offset)

            # Write the data
            dump_file.write(data)

            # Update the received data size
            dump_info["received"] += chunk_size

            # Display progress
            if expected_size > 0:
                percent = min(100.0, dump_info["received"] / expected_size * 100)
                logger.module_progress(module_name, "Writing data", percent)

        except Exception as e:
            error_msg = f"Error writing module data: {e}"
            logger.error(error_msg, context=module_context)
            raise OSError(error_msg) from e

    def complete_module_dump(self, module_name: str) -> str:
        """
        Complete writing a module dump.

        Args:
            module_name: Module name

        Returns:
            Path to the saved file

        Raises:
            ValueError: If the module is not found in active dumps
        """
        module_context = LogContext(logger.COMPONENT_MODULE, module_name)

        # Check if the module is active
        if module_name not in self.active_dumps:
            error_msg = f"Module {module_name} not found in active dumps"
            logger.error(error_msg, context=module_context)
            raise ValueError(error_msg)

        dump_info = self.active_dumps[module_name]
        dump_file: BinaryIO = dump_info["file"]
        save_path: str = dump_info["path"]

        try:
            # Close the file
            dump_file.close()

            # Display final progress
            logger.module_progress(module_name, "Writing data", 100.0)

            # Display information about successful completion
            elapsed_time = time.time() - dump_info["start_time"]
            logger.info(
                f"Module dump successfully completed: {save_path} "
                f"(in {elapsed_time:.2f} seconds)",
                context=module_context
            )

            # Remove from active dumps
            del self.active_dumps[module_name]

            return save_path

        except Exception as e:
            error_msg = f"Error completing module dump: {e}"
            logger.error(error_msg, context=module_context)
            # Don't raise an exception to avoid interrupting resource cleanup
            result: str = "" if "save_path" not in locals() else save_path
            return result

    def cleanup_active_dumps(self, log_incomplete: bool = False) -> None:
        """
        Close all active dump files.

        Args:
            log_incomplete: Whether to log incomplete dumps
        """
        if not self.active_dumps:
            return

        logger.info(f"Closing {len(self.active_dumps)} active dump files...",
                   context=LogContext(logger.COMPONENT_FILE))

        for module_name, dump_info in list(self.active_dumps.items()):
            module_context = LogContext(logger.COMPONENT_MODULE, module_name)

            try:
                # Close the file
                dump_info["file"].close()

                # Log incomplete dumps
                if log_incomplete:
                    received = dump_info["received"]
                    expected = dump_info["size"]
                    if received != expected:
                        logger.warning(
                            f"Incomplete module dump: received {received} "
                            f"bytes out of {expected} (difference: {expected - received} bytes)",
                            context=module_context
                        )

                # Remove from active dumps
                del self.active_dumps[module_name]

            except Exception as e:
                logger.error(f"Error closing file for module: {e}",
                            context=module_context)

        logger.info("All active dump files closed",
                   context=LogContext(logger.COMPONENT_FILE))
