import sys
import time
import itertools

SPINNER_SETS = {
    "braille": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "classic": ["|", "/", "-", "\\"],
    "circle": ["◐", "◓", "◑", "◒"],
    "arrows": ["←", "↑", "→", "↓"],
    "corners": ["▖", "▘", "▝", "▗"],
    "dots": ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"],
}


def create_spinner(spinner_name):
    if spinner_name not in SPINNER_SETS:
        raise ValueError(f"Unknown spinner name: {spinner_name}")
    return itertools.cycle(SPINNER_SETS[spinner_name])


def progress_bar(bar_length, current, total, start_time, spinner_cycle):
    percent = current / total
    bar_len = int(bar_length)
    center_text = f"{current}/{total}"
    center_len = len(center_text)

    side_total = bar_len - center_len
    left_len = side_total // 2
    right_len = side_total - left_len
    filled_slots = int(percent * side_total)

    left_filled = min(filled_slots, left_len)
    right_filled = max(0, filled_slots - left_len)

    left = "#" * left_filled + "." * (left_len - left_filled)
    right = "#" * right_filled + "." * (right_len - right_filled)

    bar = f"{left} {center_text} {right}"

    elapsed = int(time.time() - start_time)
    elapsed_str = (
        f"{elapsed}s" if elapsed < 60 else f"{elapsed // 60}m{elapsed % 60:02d}s"
    )
    spin_char = next(spinner_cycle)

    sys.stdout.write(f"\r{spin_char} {bar} {elapsed_str}")
    sys.stdout.flush()
