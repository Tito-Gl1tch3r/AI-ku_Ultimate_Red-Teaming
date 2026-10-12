# core/utils/formatter.py
from rich.console import Console
from rich.text import Text
from tqdm import tqdm

console = Console()


def printc(message, level: str = "info", use_tqdm: bool = False):
    """
    Print colored messages using `rich`.
    Optionally write through tqdm if progress bar is active.
    Accepts both strings and Text objects.
    """
    style_map = {
        "info": "white",
        "success": "bold green",
        "unsuccessful": "dim red",
        "warn": "yellow",
        "error": "bold red",
        "debug": "dim",
        "module": "bold blue",
        "selection": "bold yellow",
        "headline": "bold underline cyan",
        "url": "blue",
    }
    style = style_map.get(level, "white")

    text = message if isinstance(message, Text) else Text(message, style=style)

    if use_tqdm:
        with console.capture() as capture:
            console.print(text)
        tqdm.write(capture.get())  # Preserve rich formatting
    else:
        console.print(text)


def colorize(content: str, color: str = "cyan", style: str = "") -> Text:
    """
    Return a rich.Text object with the given color and style.
    Example: f"Link: {colorize(url, 'cyan', 'underline')}"
    """
    style_str = f"{color} {style}".strip()
    return Text(content, style=style_str)
