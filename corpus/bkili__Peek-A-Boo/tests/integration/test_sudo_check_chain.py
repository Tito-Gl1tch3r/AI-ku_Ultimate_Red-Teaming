import pytest  # noqa: F401
from modules.pb_check_sudo_version import Module as SudoVersionModule
from modules.pb_check_sudo_cves import Module as SudoCVEModule


def test_integration_sudo_version_to_cves(monkeypatch):
    shared_data = {}

    class DummySSH:
        def close(self):
            pass

    def mock_create_ssh_client(host, port, username, password):
        return DummySSH()

    def mock_ssh_exec(ssh, cmd):
        return (None, "Sudo version 1.9.9p0", None)

    monkeypatch.setattr(
        "modules.pb_check_sudo_version.create_ssh_client", mock_create_ssh_client
    )
    monkeypatch.setattr("modules.pb_check_sudo_version.ssh_exec", mock_ssh_exec)

    sudo_mod = SudoVersionModule()
    sudo_mod.options.update(
        {
            "rhost": "127.0.0.1",
            "rport": "22",
            "username": "testuser",
            "password": "testpass",
        }
    )
    sudo_mod.run(shared_data)

    assert "pb_check_sudo_version" in shared_data
    assert shared_data["pb_check_sudo_version"] == (1, 9, 9, 0)

    cves_mod = SudoCVEModule()
    cves_mod.run(shared_data)

    assert "pb_check_sudo_cves" in shared_data
    assert isinstance(shared_data["pb_check_sudo_cves"], list)
    assert any("CVE-" in cve["id"] for cve in shared_data["pb_check_sudo_cves"])
