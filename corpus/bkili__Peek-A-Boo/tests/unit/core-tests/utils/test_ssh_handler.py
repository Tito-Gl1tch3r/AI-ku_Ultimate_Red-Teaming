import sys
import unittest

from unittest.mock import patch, MagicMock
from core.utils import ssh_handler

print(sys.executable)
print(sys.path)


class TestSSHHandler(unittest.TestCase):

    @patch("paramiko.SSHClient")
    def test_create_ssh_client_success(self, MockSSHClient):
        mock_ssh = MagicMock()
        MockSSHClient.return_value = mock_ssh

        client = ssh_handler.create_ssh_client("127.0.0.1", 22, "user", "pass")

        mock_ssh.connect.assert_called_with(
            hostname="127.0.0.1", port=22, username="user", password="pass"
        )
        self.assertEqual(client, mock_ssh)

    @patch("paramiko.SSHClient")
    def test_create_ssh_client_failure(self, MockSSHClient):
        mock_ssh = MagicMock()
        mock_ssh.connect.side_effect = Exception("Connection error")
        MockSSHClient.return_value = mock_ssh

        with self.assertRaises(Exception) as context:
            ssh_handler.create_ssh_client("127.0.0.1", 22, "user", "wrong")

        self.assertIn("Connection error", str(context.exception))

    def test_ssh_exec(self):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.read.return_value = b"output"
        mock_stderr.read.return_value = b"error"

        mock_ssh.exec_command.return_value = (None, mock_stdout, mock_stderr)

        stdin, out, err = ssh_handler.ssh_exec(mock_ssh, "ls -la")
        self.assertEqual(out, "output")
        self.assertEqual(err, "error")

    def test_sftp_upload(self):
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp

        ssh_handler.sftp_upload(mock_ssh, "local.txt", "/remote.txt")
        mock_sftp.put.assert_called_with("local.txt", "/remote.txt")
        mock_sftp.close.assert_called_once()

    def test_sftp_download(self):
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh.open_sftp.return_value = mock_sftp

        ssh_handler.sftp_download(mock_ssh, "/remote.txt", "local.txt")
        mock_sftp.get.assert_called_with("/remote.txt", "local.txt")
        mock_sftp.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
