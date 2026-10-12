"""
Test logging configuration - writes ALL output to a timestamped log file.
Import this at the start of test runs to enable file logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Log directory - create if needed
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file with timestamp for each run
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILENAME = f"tool_tests_{TIMESTAMP}.log"
LOG_FILEPATH = LOG_DIR / LOG_FILENAME

# File handle for TeeWriter - kept open for session
_log_file_handle = None


class TeeWriter:
    """Writes to both file and original stream."""

    def __init__(self, file_handle, stream):
        self.file = file_handle
        self.stream = stream

    def write(self, data):
        try:
            self.file.write(data)
            self.file.flush()
        except (ValueError, OSError):
            pass
        self.stream.write(data)
        self.stream.flush()

    def flush(self):
        try:
            self.file.flush()
        except (ValueError, OSError):
            pass
        self.stream.flush()

    def isatty(self):
        return self.stream.isatty() if hasattr(self.stream, "isatty") else False

    def fileno(self):
        return self.stream.fileno() if hasattr(self.stream, "fileno") else -1


def setup_test_logging() -> Path:
    """
    Configure logging to write ALL output to a timestamped file.
    Returns the log file path.
    """
    global _log_file_handle
    _log_file_handle = open(LOG_FILEPATH, "w", encoding="utf-8")

    # Write header
    header = f"""
{'='*80}
RivalSearchMCP - Comprehensive Tool Test Log
Started: {datetime.now().isoformat()}
Log file: {LOG_FILEPATH}
{'='*80}

"""
    _log_file_handle.write(header)
    _log_file_handle.flush()

    # Tee stdout and stderr to log file (preserves console output)
    sys.stdout = TeeWriter(_log_file_handle, sys.__stdout__)
    sys.stderr = TeeWriter(_log_file_handle, sys.__stderr__)

    # Configure all loggers to write to file with timestamps
    file_handler = logging.FileHandler(LOG_FILEPATH, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    logging.getLogger("rival_search_mcp").addHandler(file_handler)

    return LOG_FILEPATH


def log_test_event(
    event: str, tool: str = "", params: str = "", status: str = "", details: str = ""
) -> None:
    """Write a timestamped test event to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    parts = [f"{timestamp} | TEST | {event}"]
    if tool:
        parts.append(f"tool={tool}")
    if params:
        parts.append(f"params={params}")
    if status:
        parts.append(f"status={status}")
    if details:
        parts.append(details[:500])
    line = " | ".join(parts) + "\n"

    try:
        with open(LOG_FILEPATH, "a", encoding="utf-8") as f:
            f.write(line)
    except (OSError, ValueError):
        pass


def get_log_path() -> Path:
    """Return the current log file path."""
    return LOG_FILEPATH
