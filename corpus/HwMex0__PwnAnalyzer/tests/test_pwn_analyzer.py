import json
import hashlib
import sys
import types

# Provide a minimal colorama stub for testing environments without colorama
colorama_stub = types.ModuleType("colorama")
colorama_stub.Fore = types.SimpleNamespace(RED="", GREEN="", BLUE="", YELLOW="", CYAN="")
colorama_stub.Style = types.SimpleNamespace(RESET_ALL="")
colorama_stub.init = lambda autoreset=True: None
sys.modules.setdefault("colorama", colorama_stub)

from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import PwnAnalyzer


def test_compute_file_hash(tmp_path):
    test_file = tmp_path / "sample.txt"
    data = b"hello world"
    test_file.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    result = PwnAnalyzer.compute_file_hash(str(test_file))
    assert result == expected


def test_search_in_file_with_wildcard(tmp_path, capsys):
    logs_dir = tmp_path / "logs" / "session_logs" / "abc"
    logs_dir.mkdir(parents=True)
    file1 = logs_dir / "session_HTTP_1.log"
    file2 = logs_dir / "session_HTTP_2.log"
    file1.write_text("start\n<INCLUDE>\nend\n")
    file2.write_text("something\n<INCLUDE>\n")

    template = {
        "templates": [
            {
                "name": "WildcardTest",
                "search_tasks": [
                    {
                        "file_path": str(tmp_path / "logs" / "session_logs" / "*" / "session_HTTP_*.log"),
                        "patterns": [
                            {"pattern": "<INCLUDE>", "case_sensitive": False, "severity": "low", "context_lines": 0, "actions": []}
                        ]
                    }
                ],
                "log_file": "test.log"
            }
        ]
    }

    template_file = tmp_path / "template.json"
    template_file.write_text(json.dumps(template))

    PwnAnalyzer.run_search(str(template_file), template_file.name, False)
    captured = capsys.readouterr().out

    assert str(file1) in captured
    assert str(file2) in captured


def test_run_search_returns_results(tmp_path):
    log_file = tmp_path / "attack.log"
    log_file.write_text("something exploit happened\n")

    template = {
        "templates": [
            {
                "name": "ReturnTest",
                "search_tasks": [
                    {
                        "file_path": str(log_file),
                        "patterns": [
                            {"pattern": "exploit", "case_sensitive": False, "severity": "high", "context_lines": 0, "actions": []}
                        ]
                    }
                ],
                "log_file": "test.log",
            }
        ]
    }

    template_file = tmp_path / "template.json"
    template_file.write_text(json.dumps(template))

    results = PwnAnalyzer.run_search(str(template_file), template_file.name, False)

    assert len(results) == 1
    assert results[0]["file"] == str(log_file)
