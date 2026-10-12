import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence


def _is_working_semgrep_command(command: Sequence[str]) -> bool:
    try:
        result = subprocess.run(
            [*command, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


@lru_cache(maxsize=1)
def get_semgrep_command() -> Optional[List[str]]:
    semgrep_on_path = shutil.which("semgrep")
    project_root = Path(__file__).resolve().parents[1]
    venv_semgrep = project_root / ".venv" / "bin" / "semgrep"

    candidates = [
        ["semgrep"],
        [sys.executable, "-m", "semgrep"],
    ]

    if semgrep_on_path:
        candidates.append([semgrep_on_path])

    if venv_semgrep.exists():
        candidates.append([str(venv_semgrep)])

    homebrew_semgrep = "/opt/homebrew/bin/semgrep"
    if Path(homebrew_semgrep).exists():
        candidates.append([homebrew_semgrep])

    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key in seen:
            continue
        seen.add(key)
        if _is_working_semgrep_command(candidate):
            return list(candidate)

    return None


def is_semgrep_available() -> bool:
    return get_semgrep_command() is not None


def semgrep_install_hint() -> str:
    return (
        "Install dependencies with `pip install -r requirements.txt` "
        "to include Semgrep."
    )
