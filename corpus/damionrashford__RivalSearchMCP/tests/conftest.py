"""
Pytest configuration - sets up file logging with timestamps for all test output.
"""

from tests.test_logging import get_log_path, log_test_event, setup_test_logging


def pytest_configure(config):
    """Configure logging before any tests run."""
    setup_test_logging()
    log_path = get_log_path()
    print(f"\n>>> All test output logged to: {log_path}\n")


def pytest_runtest_setup(item):
    """Log each test start."""
    log_test_event("START", tool=item.name, params="", status="running")


def pytest_runtest_teardown(item):
    """Log each test completion."""
    log_test_event("END", tool=item.name, params="", status="completed")


def pytest_runtest_logreport(report):
    """Log test results (pass/fail)."""
    if report.when == "call":
        status = "PASS" if report.passed else "FAIL"
        details = report.longreprtext if report.failed else ""
        log_test_event("RESULT", tool=report.nodeid, status=status, details=details[:200])


def pytest_sessionfinish(session, exitstatus):
    """Log session end and final summary."""
    from tests.test_logging import get_log_path

    log_test_event("SESSION_END", details=f"exitstatus={exitstatus}")
    print(f"\n>>> Full log: {get_log_path()}\n")
