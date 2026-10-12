# core/utils/ssh_handler.py
import paramiko


def create_ssh_client(host, port, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=host, port=port, username=username, password=password)
        return ssh

    except Exception as e:
        if "Authentication failed" in str(e):
            raise ValueError("SSH authentication failed. Check your credentials.")
        elif "No route to host" in str(e):
            raise ConnectionError("Could not connect to the host. Check the network.")
        elif "timed out" in str(e):
            raise TimeoutError("SSH connection timed out. Check the host and port.")
        else:
            # For any other exceptions, we can just raise the original exception
            raise e


def ssh_exec(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdin, stdout.read().decode(), stderr.read().decode()


def sftp_upload(ssh, local_path, remote_path):
    sftp = ssh.open_sftp()
    try:
        sftp.put(str(local_path), remote_path)
    finally:
        sftp.close()


def sftp_download(ssh, remote_path, local_path):
    sftp = ssh.open_sftp()
    try:
        sftp.get(remote_path, local_path)
    finally:
        sftp.close()
