import paramiko
import copy


class SSHClientHandler:
    def __init__(
        self,
        node_ssh_username,
        web_ingress_ssh_username,
        web_ingress_public_ip,
        web_ingress_private_ip,
        logger,
    ):
        self.node_ssh_username = node_ssh_username
        self.web_ingress_ssh_username = web_ingress_ssh_username
        self.web_ingress_public_ip = web_ingress_public_ip
        self.web_ingress_private_ip = web_ingress_private_ip
        self.logger = logger

    def create_ssh_client(self, ip, username, use_jump=False):
        self.logger.debug("func: create_ssh_client")
        try:
            jumpbox_channel = None
            if use_jump:
                jumpbox = paramiko.SSHClient()
                jumpbox.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                jumpbox.connect(
                    self.web_ingress_public_ip, username=self.web_ingress_ssh_username
                )
                jumpbox_transport = jumpbox.get_transport()
                src_addr = (self.web_ingress_private_ip, 22)
                dest_addr = (ip, 22)
                jumpbox_channel = jumpbox_transport.open_channel(
                    "direct-tcpip", dest_addr, src_addr
                )
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                ip,
                username=username,
                sock=jumpbox_channel,
                banner_timeout=30,
                timeout=30,
            )
            return client
        except Exception as e:
            self.logger.error(f"Failed to create SSH client for {ip}: {e}")
            return None

    def execute_commands(self, commands, ip, use_jump=False, run_sequenctially=False):
        self.logger.debug("func: execute_commands")
        proxy = None
        try:
            ssh_client = self.create_ssh_client(ip, self.node_ssh_username, use_jump)
            if ssh_client:
                output = ""
                if run_sequenctially:
                    for command in commands:
                        self.logger.info(f"command: {command}")
                        _, stdout, stderr = ssh_client.exec_command(command)
                        last_command_output = (
                            f"{stdout.read().decode('utf-8').strip()}\n"
                        )
                        output += last_command_output
                        self.logger.info(f"stdout: {last_command_output}")
                        self.logger.info(f"stderr: {stderr.read().decode()}")

                    ssh_client.close()
                    return output

                else:
                    full_command = " && ".join(commands)
                    self.logger.info(f"command: {full_command}")
                    _, stdout, stderr = ssh_client.exec_command(full_command)
                    output = stdout.read().decode("utf-8").strip()
                    self.logger.info(f"stdout: {output}")
                    self.logger.info(f"stderr: {stderr.read().decode()}")
                    ssh_client.close()
                    self.logger.info("==========")
                    self.logger.info(output)
                    return output
        except Exception as e:
            self.logger.error(f"Failed to execute command on {ip}: {e}")
            self.logger.error(f"commands: {commands}")
            return None

    def copy_file(
        self, local_path, remote_path, ip, username, direction="get", use_jump=False
    ):
        self.logger.debug("func: copy_file")
        proxy = None
        try:
            ssh_client = self.create_ssh_client(ip, username, use_jump)
            self.logger.info(
                f"File transfer {'from' if direction == 'get' else 'to'} {ip} remote-path={remote_path} local-path={local_path}"
            )
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
