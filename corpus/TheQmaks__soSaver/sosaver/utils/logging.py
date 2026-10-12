"""
Logging module for soSaver.

Provides a unified interface for logging messages
with various importance levels and formatting.
"""

import shutil
import sys
import threading
import time
from enum import Enum
from typing import Dict, NamedTuple, Optional, TextIO


class LogLevel(Enum):
    """Logging levels with corresponding prefixes."""
    DEBUG = ("DEBUG", "\033[36m")  # Cyan
    INFO = ("INFO", "\033[32m")    # Green
    WARNING = ("WARN", "\033[33m")  # Yellow
    ERROR = ("ERROR", "\033[31m")   # Red


class LogContext(NamedTuple):
    """
    Logging context for grouping and identifying messages.

    Context examples:
    - module:libart.so - operations with a specific module
    - component:frida - messages from the Frida component
    - process:device - operations on the device
    """
    component: str
    identifier: Optional[str] = None

    def __str__(self) -> str:
        """String representation of the context for display in logs."""
        if self.identifier:
            return f"[{self.component}:{self.identifier}]"
        return f"[{self.component}]"


class Logger:
    """
    Enhanced logger for structured message output.

    Supports contextual logging, color formatting
    and various logging levels.
    """

    RESET_COLOR = "\033[0m"

    # System components
    COMPONENT_CORE = "CORE"
    COMPONENT_FRIDA = "FRIDA"
    COMPONENT_DEVICE = "DEVICE"
    COMPONENT_FILE = "FILE"
    COMPONENT_MODULE = "MODULE"

    def __init__(
        self,
        min_level: LogLevel = LogLevel.INFO,
        output_stream: TextIO = sys.stdout
    ):
        """
        Initialize the logger.

        Args:
            min_level: Minimum logging level, messages below this level are not displayed
            output_stream: Output stream for logging (default sys.stdout)
        """
        self.min_level = min_level
        self.output_stream = output_stream
        self.use_colors = True
        self._lock = threading.RLock()  # To prevent message interleaving

        # For tracking progress bars
        self._progress_lines: Dict[str, str] = {}
        self._console_width = shutil.get_terminal_size().columns

    def set_level(self, level: LogLevel) -> None:
        """Set the minimum logging level."""
        self.min_level = level

    def log(self, level: LogLevel, message: str,
            context: Optional[LogContext] = None, end: str = "\n") -> None:
        """
        Display a message with the specified logging level and context.

        Args:
            level: Logging level
            message: Message to display
            context: Logging context (component/identifier)
            end: String to append at the end (default newline)
        """
        # Check the logging level
        if level.value[0] < self.min_level.value[0]:
            return

        with self._lock:
            # Format the level prefix
            level_prefix = f"[{level.value[0]}]"

            # Add context if available
            context_str = f"{context} " if context else ""

            # Format with color if enabled
            if self.use_colors:
                color = level.value[1]
                formatted_message = f"{color}{level_prefix} {context_str}{message}{self.RESET_COLOR}"
            else:
                formatted_message = f"{level_prefix} {context_str}{message}"

            # Display the message
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {formatted_message}", end=end, file=self.output_stream)
            self.output_stream.flush()  # Ensure immediate output

    def debug(self, message: str, context: Optional[LogContext] = None, end: str = "\n") -> None:
        """Display a debug message."""
        self.log(LogLevel.DEBUG, message, context, end)

    def info(self, message: str, context: Optional[LogContext] = None, end: str = "\n") -> None:
        """Display an informational message."""
        self.log(LogLevel.INFO, message, context, end)

    def warning(self, message: str, context: Optional[LogContext] = None, end: str = "\n") -> None:
        """Display a warning message."""
        self.log(LogLevel.WARNING, message, context, end)

    def error(self, message: str, context: Optional[LogContext] = None, end: str = "\n") -> None:
        """Display an error message."""
        self.log(LogLevel.ERROR, message, context, end)

    # Helper methods for common contexts

    def frida(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message from the Frida script."""
        context = LogContext(self.COMPONENT_FRIDA)
        self.log(level, message, context)

    def device(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message about device operations."""
        context = LogContext(self.COMPONENT_DEVICE)
        self.log(level, message, context)

    def file(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message about file operations."""
        context = LogContext(self.COMPONENT_FILE)
        self.log(level, message, context)

    def progress(self, message: str, percent: float,
                context: Optional[LogContext] = None) -> None:
        """
        Display a progress indicator.

        Args:
            message: Message to display
            percent: Completion percentage (0-100)
            context: Logging context
        """
        # In Windows console, progress bars work unstably with prefixes
        # So we just show a regular message with percentages
        percent_str = f"{percent:.1f}%"

        # Determine the key for tracking progress
        progress_key = str(context) if context else "global"

        # If the percentage is close to 100%, display as a regular message
        if percent >= 99.9:
            self.info(f"{message}: completed ({percent_str})", context=context)
            if progress_key in self._progress_lines:
                del self._progress_lines[progress_key]
        else:
            # Short progress form for console
            bar_length = min(20, max(10, self._console_width // 5))
            filled_length = int(bar_length * percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            # Save the current progress
            progress_message = f"{message}: {percent_str} [{bar}]"
            self._progress_lines[progress_key] = progress_message

            # Simply display as a regular message
            self.info(progress_message, context=context)

    def module_progress(self, module_name: str, message: str, percent: float) -> None:
        """Display progress of module operations."""
        context = LogContext(self.COMPONENT_MODULE, module_name)
        self.progress(message, percent, context)


# Global logger instance to be used throughout the application
logger = Logger()
