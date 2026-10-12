import pytest
import os
import sys
import subprocess
import re
import shutil


pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win") and not sys.stdin.isatty(),
    reason="prompt_toolkit requires a real terminal on Windows",
)


@pytest.fixture(autouse=True, scope="session")
def isolate_test_config_and_history(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("test_env")
    sys.stderr.write(f"[DEBUG] Test dir: {test_dir}\n")
    os.environ["PB_CONFIG_PATH"] = str(test_dir / "test_config.yaml")
    os.environ["PB_HISTORY_PATH"] = str(test_dir / "test_history")
    yield
    del os.environ["PB_CONFIG_PATH"]
    del os.environ["PB_HISTORY_PATH"]
    shutil.rmtree(test_dir)

def strip_ansi(text):
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)


def run_peekaboo_with_input(cmd_input):
    """
    Run the CLI with the given input string as if typed interactively.
    """
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    stdout, _ = process.communicate(input=cmd_input)
    return stdout


# CLI command tests for Peek-A-Boo
def test_custom_paths_are_used():
    assert "test_config.yaml" in os.environ["PB_CONFIG_PATH"]
    assert "test_history" in os.environ["PB_HISTORY_PATH"]


# test unknown command
def test_unknown_command():
    output = run_peekaboo_with_input("foo\nexit\n")
    assert "Unknown command: foo" in output


# help command tests
def test_help_command():
    output = run_peekaboo_with_input("help\nexit\n")
    assert "Available commands:" in output


# exit command tests
def test_exit_command():
    output = run_peekaboo_with_input("exit\n")
    assert "Exiting.." in output or output.endswith("\n")


# clear command tests
def test_clear_command():
    output = run_peekaboo_with_input("clear\n")
    assert (
        "\n" in output or output == ""
    )  # Clear command should produce an empty output


# info command tests
def test_info_no_module_selected():
    output = run_peekaboo_with_input("info\nexit\n")
    assert "No module selected." in output


def test_info_explicit_module_info():
    output = run_peekaboo_with_input("info pb_holehe_check_email\nexit\n")
    assert "Module: pb_holehe_check_email" in output


def test_info_after_use_command():
    output = run_peekaboo_with_input("use pb_wayback\ninfo\nexit\n")
    assert "Module: pb_wayback" in output


def test_info_nonexistent_module():
    output = run_peekaboo_with_input("info pb_foo\nexit\n")
    assert "Error loading module: No module named 'modules.pb_foo'" in output


# list command tests
def test_list():
    output = run_peekaboo_with_input("list\nexit\n")
    assert "Available modules:" in output
    assert "[utility]" in output  # Example category, adjust as needed
    assert "[-] pb_screenshot" in output

    assert "Available exploits:" in output
    assert "[privilege_escalation]" in output  # Example category, adjust as needed
    assert "[-] exp_cve_2025_32463" in output  # Example exploit, adjust as needed

    assert "Available plugins:" in output


def test_list_modules():
    output = run_peekaboo_with_input("list modules\nexit\n")
    assert "Available modules:" in output
    assert "[utility]" in output  # Example category, adjust as needed
    assert "[-] pb_scrape_keywords" in output


def test_list_exploits():
    output = run_peekaboo_with_input("list exploits\nexit\n")
    assert "Available exploits:" in output
    assert "[privilege_escalation]" in output  # Example category, adjust as needed
    assert "[-] exp_cve_2025_32463" in output  # Example exploit, adjust as needed


def test_list_plugins():
    output = run_peekaboo_with_input("list plugins\nexit\n")
    assert "Available plugins:" in output


def test_list_all():
    output = run_peekaboo_with_input("list\nexit\n")
    assert "Available modules:" in output
    assert "[utility]" in output  # Example category, adjust as needed
    assert "[-] pb_screenshot" in output

    assert "Available exploits:" in output
    assert "[privilege_escalation]" in output  # Example category, adjust as needed
    assert "[-] exp_cve_2025_32463" in output  # Example exploit, adjust as needed

    assert "Available plugins:" in output


# save command tests
def test_save_no_module():
    output = run_peekaboo_with_input("save config test\nexit\n")
    assert "No module selected. Use a module before saving config." in output


def test_save_config():
    output = run_peekaboo_with_input(
        "use pb_wayback\n"
        "set url https://www.example.com\n"
        "set output_directory test_dir\n"
        "save config test_cli_commands\nexit\n"
    )
    assert "Configuration saved to configs/test_cli_commands" in output


# load command tests
def test_load_no_module_config():
    output = run_peekaboo_with_input("load config test_cli_commands\nexit\n")
    assert "No module selected. Use a module before loading config." in output


def test_load_config():
    output = run_peekaboo_with_input(
        "use pb_wayback\nload config test_cli_commands\nshow options\nexit\n"
    )
    assert "Configuration loaded from configs/test_cli_commands" in output
    assert "https://www.example.com" in output
    assert "test_dir" in output


def test_load_nonexistent_config():
    output = run_peekaboo_with_input(
        "use pb_wayback\nload config nonexistent\nshow options\nexit\n"
    )
    assert "File not found." in output


# reload command tests
def test_reload_no_module():
    output = run_peekaboo_with_input("reload\nexit\n")
    assert "No module found: reload not supported." in output


def test_reload():
    output = run_peekaboo_with_input("use pb_wayback\nreload\nexit\n")
    assert "Options reloaded to default." in output


# run command tests
def test_run_no_module():
    output = run_peekaboo_with_input("run\nexit\n")
    assert "No module selected." in output


def test_run_module():
    output = run_peekaboo_with_input(
        "use pb_phone_lookup\nset phone_number 911\nrun\nexit"
    )
    assert "Missing or invalid default region." in output


# search command tests
def test_search_no_query():
    output = run_peekaboo_with_input("search\nexit\n")
    assert "Usage: search <keyword>" in output


def test_search_keyword():
    output = run_peekaboo_with_input("search pb_screenshot\nexit\n")
    assert "- pb_screenshot" in output


# set command tests
def test_set_no_module():
    output = run_peekaboo_with_input("set option value\nexit\n")
    assert "No module selected." in output


def test_set_option():
    output = run_peekaboo_with_input(
        "use pb_wayback\nset url https://www.example.com\nshow options\nexit\n"
    )
    assert "https://www.example.com" in output


def test_set_invalid_option():
    output = run_peekaboo_with_input("use pb_wayback\nset invalid_option value\nexit\n")
    assert "invalid_option set to value" in output


# show command tests
def test_show_no_module():
    output = run_peekaboo_with_input("show\nexit\n")
    assert "No module selected." in output


def test_show_options():
    output = run_peekaboo_with_input("use pb_wayback\nshow options\nexit\n")
    assert "Option" in output
    assert "url" in output
    assert "output_directory" in output


# show summary command tests
def test_show_summary_no_module():
    output = run_peekaboo_with_input("show summary\nexit\n")
    assert "No module selected." in output


def test_show_summary_no_data():
    output = run_peekaboo_with_input("use pb_wayback\nshow summary\nexit\n")
    assert "No summary available." in output


# use command tests
def test_use_no_module():
    output = run_peekaboo_with_input("use\nexit\n")
    assert "Usage: use <module_name>" in output


def test_use_nonexistent_module():
    output = run_peekaboo_with_input("use pb_nonexistent\nexit\n")
    assert "Failed to import module 'pb_nonexistent':" in output


# history command tests
def test_clear_history():
    output = run_peekaboo_with_input("clear history\necho wait\nexit\n")
    assert "Command history cleared." in output


def test_history():
    run_peekaboo_with_input("use pb_wayback\nset url https://a.com\nexit\n")
    output = run_peekaboo_with_input("history\nexit\n")
    clean_output = strip_ansi(output)
    assert "Command History:" in clean_output


def test_alias():
    output = run_peekaboo_with_input("alias la = list all\nl\nexit\n")
    assert "Alias 'la: list all' added to config." in output
