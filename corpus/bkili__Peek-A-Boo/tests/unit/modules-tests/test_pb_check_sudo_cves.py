import pytest
from modules.pb_check_sudo_cves import Module as PbCheckSudoCVEs


@pytest.fixture
def shared_data():
    return {}


def test_run_with_shared_data(capfd, shared_data):
    # Arrange
    shared_data["pb_check_sudo_version"] = (1, 9, 9, 0)
    module = PbCheckSudoCVEs()

    # Act
    module.run(shared_data)
    out, err = capfd.readouterr()

    # Assert
    assert "8 CVE(s) matched for sudo 1.9.9.0" in out
    assert "pb_check_sudo_cves" in shared_data
    assert isinstance(shared_data["pb_check_sudo_cves"], list)
    assert any("CVE" in cve["id"] for cve in shared_data["pb_check_sudo_cves"])


def test_run_with_options_fallback(capfd, shared_data):
    # Arrange
    module = PbCheckSudoCVEs()
    module.options["version"] = "1.9.9p0"
    module.options["rhost"] = ""
    module.run(shared_data)

    # Act
    out, err = capfd.readouterr()

    # Assert
    assert "8 CVE(s) matched for sudo 1.9.9p0" in out
    assert "pb_check_sudo_cves" in shared_data


def test_run_with_no_version(capfd, shared_data):
    # Arrange
    module = PbCheckSudoCVEs()
    module.options["version"] = ""
    module.options["rhost"] = ""
    module.run(shared_data)

    # Act
    out, err = capfd.readouterr()

    # Assert
    assert "No sudo version found in shared_data or options" in out
    assert "pb_check_sudo_cves" not in shared_data
