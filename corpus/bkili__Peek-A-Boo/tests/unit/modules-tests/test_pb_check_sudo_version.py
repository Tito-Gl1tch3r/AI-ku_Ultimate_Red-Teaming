# tests/unit/test_pb_check_sudo_version.py
from unittest import TestCase
from unittest.mock import patch, MagicMock
from modules import pb_check_sudo_version


class TestPbCheckSudoVersion(TestCase):
    @patch("modules.pb_check_sudo_version.ssh_exec")
    @patch("modules.pb_check_sudo_version.create_ssh_client")
    def test_sudo_version_shared_data(self, mock_create_ssh_client, mock_ssh_exec):
        # Arrange
        mock_ssh = MagicMock()
        mock_create_ssh_client.return_value = mock_ssh
        mock_ssh_exec.return_value = (None, "Sudo version 1.9.9p2\n", None)

        module = pb_check_sudo_version.Module()
        module.options.update(
            {"rhost": "dummy", "rport": "22", "username": "user", "password": "pass"}
        )
        shared_data = {}

        # Act
        module.run(shared_data)

        # Assert
        self.assertIn("pb_check_sudo_version", shared_data)
        self.assertEqual(shared_data["pb_check_sudo_version"], (1, 9, 9, 2))
