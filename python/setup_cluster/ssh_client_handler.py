import paramiko


class SSHClientHandler:
    def __init__(
        self, node_ssh_username, web_ingress_ssh_username, web_ingress_public_ip, logger
    ):
        self.node_ssh_username = node_ssh_username
        self.web_ingress_ssh_username = web_ingress_ssh_username
        self.web_ingress_public_ip = web_ingress_public_ip
        self.logger = logger

    def create_ssh_client(self, ip, username, proxy=None):
        try:
            sock = paramiko.ProxyCommand(proxy) if proxy else None
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, sock=sock)
            return client
        except Exception as e:
            self.logger.error(f"Failed to create SSH client for {ip}: {e}")
            return None

    def execute_command(self, commands, ip, use_jump=False):
        proxy = None
        if use_jump:
            proxy = f"ssh -o StrictHostKeyChecking=no {self.web_ingress_ssh_username}@{self.web_ingress_public_ip}"
        try:
            ssh_client = self.create_ssh_client(ip, self.node_ssh_username, proxy)
            if ssh_client:
                full_command = " && ".join(commands)
                self.logger.info(f"command: {full_command}")
                _, stdout, stderr = ssh_client.exec_command(full_command)
                self.logger.info(f"stdout: {stdout.read().decode()}")
                self.logger.info(f"stderr: {stderr.read().decode()}")
                ssh_client.close()
                return stdout.read().decode().strip()
        except Exception as e:
            self.logger.error(f"Failed to execute command on {ip}: {e}")
            return None

    def copy_file(
        self, local_path, remote_path, ip, username, direction="get", use_jump=False
    ):
        proxy = None
        if use_jump:
            proxy = f"ssh -o StrictHostKeyChecking=no {self.web_ingress_ssh_username}@{self.web_ingress_public_ip}"
        try:
            ssh_client = self.create_ssh_client(ip, username, proxy)
            if ssh_client:
                with paramiko.SFTPClient.from_transport(
                    ssh_client.get_transport()
                ) as sftp:
                    if direction == "get":
                        sftp.get(remote_path, local_path)
                    elif direction == "put":
                        sftp.put(local_path, remote_path)
                    else:
                        self.logger.error(f"Invalid direction: {direction}")
                        return False
                ssh_client.close()
            self.logger.info(
                f"File transfer {'from' if direction == 'get' else 'to'} {ip} completed successfully"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error during file transfer: {e}")
            return False
