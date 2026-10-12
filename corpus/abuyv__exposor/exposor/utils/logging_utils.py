import logging
import os


class ColorFormatter(logging.Formatter):
    """
    Custom formatter to apply colors based on log level.
    """
    COLORS = {
        "DEBUG": "\033[31m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[90m",    # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    DATE_COLOR = "\033[36m"
    RESET = "\033[0m"  # Reset color to default

    def format(self, record):
        # Apply color based on the log level
        color = self.COLORS.get(record.levelname, self.RESET)
        log_line = super().format(record)
        prefix_end_index = log_line.index("] ")  # Find the end of the prefix
        date_prefix = log_line[:prefix_end_index]
        prefix = f"[{record.levelname}]"
        message = record.getMessage()
        return f"{self.DATE_COLOR}[{date_prefix}]{color}{prefix}{self.RESET} {message}"


def setup_logging(verbosity, color_supported):
    """
    Configures the logging based on the verbosity level.
    Args:
        verbosity (int): The verbosity level (0 for WARNING, 1 for INFO, 2 for DEBUG).
    """
    date_format = "%Y-%m-%d %H:%M:%S"
    handler = logging.StreamHandler()

    if verbosity >= 2:
        handler.setLevel(logging.DEBUG)
    elif verbosity == 1:
        handler.setLevel(logging.INFO)
    else:
        handler.setLevel(logging.WARNING)

    if color_supported:
        handler.setFormatter(ColorFormatter("\r[%(asctime)s] - [%(levelname)s] %(message)s", datefmt=date_format))
    else:
        handler.setFormatter(logging.Formatter("\r[%(asctime)s] - [%(levelname)s] %(message)s", datefmt=date_format))

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(handler.level)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    log_file = os.path.join(project_root, "exposor.log")
 
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("\r[%(asctime)s] - [%(levelname)s] %(message)s", datefmt=date_format)) 
    logger.addHandler(file_handler)
