# Install NeuralDB Enterprise on AWS

Spin up an AWS VM cluster to launch NeuralDB Enterprise on.

### Instructions for MacOS
1. Install the AWS CLI on your machine: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html.
2. Log into the AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html. This is the AWS account that will be used to spin up the resources for the cluster.
3. Install `homebrew`: https://brew.sh.
4. Install or upgrade `bash` by running `brew install bash` in the Terminal.
5. Install `jq` by running `brew install jq` in the Terminal.
6. Navigate into the `install-on-aws` directory in this repository.
7. Edit the `variables.sh` file to reflect your desired settings.
8. Run `bash setup.sh`

Wait for the setup process to complete (approximately 10 minutes), and you have launched a cluster on AWS that can be used to host NeuralDB Enterprise!

To launch NeuralDB Enterprise on this newly created AWS cluster, copy the `config.json` file from the `install-on-aws` directory and paste it into the `install` directory. Then follow the instructions at `install/README.md` file, starting from step 2.

### Notes
- All the nodes' IP's are exposed to the public internet in the current configuration. Therefore, ensure that network security precautions are taken before uploading sensitive files to this instance of NeuralDB Enterprise. The network settings can be changed in the `create_vms.sh` file if you wish to restrict port access.