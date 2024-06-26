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
        """
        Create and return an SSH client connected to the specified IP address.
        If use_jump is True, uses a jumpbox for the SSH connection.

        Parameters:
        - ip (str): IP address to connect to.
        - username (str): SSH username for the connection.
        - use_jump (bool): Whether to use a jump host for the connection.

        Returns:
        - SSHClient object if successful, None otherwise.
        """
        
        self.logger.debug(f"func: create_ssh_client {ip=} {username=} {use_jump=}")
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
                banner_timeout=120,
                timeout=120,
            )
            return client
        except Exception as e:
            self.logger.error(f"Failed to create SSH client for {ip}: {e}")
            return None

    def execute_commands(
        self, commands, ip, use_jump=False, run_sequentially=False, expect_stderr=False
    ):
        """
        Execute a list of commands on a remote server and return the output.

        Parameters:
        - commands (list of str): Commands to execute.
        - ip (str): IP address of the server.
        - use_jump (bool): Whether to use a jump host for the SSH connection.
        - run_sequentially (bool): Whether to run commands one after the other.
        - expect_stderr (bool): Whether to log stderr without raising a warning.

        Returns:
        - The output of the commands if successful, None otherwise.
        """

        self.logger.debug("func: execute_commands")
        try:
            ssh_client = self.create_ssh_client(ip, self.node_ssh_username, use_jump)
            if ssh_client:
                output = ""
                if run_sequentially:
                    for command in commands:
                        self.logger.info(f"command: {command}")
                        _, stdout, stderr = ssh_client.exec_command(command)
                        last_command_output = (
                            f"{stdout.read().decode('utf-8').strip()}\n"
                        )
                        output += last_command_output
                        self.logger.info(f"stdout: {last_command_output}")
                        err_output = stderr.read().decode()
                        if err_output and not expect_stderr:
                            self.logger.warning(f"stderr: {err_output}")

                    ssh_client.close()
                    return output

                else:
                    full_command = " && ".join(commands)
                    self.logger.info(f"command: {full_command}")
                    _, stdout, stderr = ssh_client.exec_command(full_command)
                    output = stdout.read().decode("utf-8").strip()
                    self.logger.info(f"stdout: {output}")
                    err_output = stderr.read().decode()
                    if err_output and not expect_stderr:
                        self.logger.warning(f"stderr: {err_output}")
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
        """
        Transfer a file between the local machine and a remote server.

        Parameters:
        - local_path (str): Path to the local file.
        - remote_path (str): Path to the remote file.
        - ip (str): IP address of the server.
        - username (str): SSH username for the connection.
        - direction (str): Transfer direction, either 'get' for downloading or 'put' for uploading.
        - use_jump (bool): Whether to use a jump host for the connection.

        Returns:
        - True if the file transfer is successful, False otherwise.
        """
        
        self.logger.debug("func: copy_file")
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
