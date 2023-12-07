# Install NeuralDB Enterprise on Azure

Spin up an Azure VM cluster and launch NeuralDB Enterprise on that cluster in minutes.

### Instructions for MacOS
1. Install the Azure CLI on your machine: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos.
2. Log into the Azure CLI: https://learn.microsoft.com/en-us/cli/azure/get-started-with-azure-cli#how-to-sign-into-the-azure-cli. This is the Azure account that will be used to spin up the resources for the cluster.
3. Install `homebrew`: https://brew.sh.
4. Install or upgrade `bash` by running `brew install bash` in the Terminal.
5. Install `jq` by running `brew install jq` in the Terminal.
6. Navigate into the `install-on-azure` directory in this repository.
7. Edit the `variables.sh` file to reflect your desired settings. Ensure that `license_path` is set correctly, as NeuralDB Enterprise will not work properly if this is incorrect.
8. Run `bash setup.sh` in the Terminal.

Wait for the setup process to complete (approximately 10 minutes), and you have launched NeuralDB Enterprise on your own Azure VM cluster!

In the `config.json` file in the `install-on-azure` directory, find the value for `HEADNODE_IP`. Paste the IP address into your browser, and you should see a login screen, where you can create an account, verify your email, and start training NeuralDB's!

Note that all the nodes' IP's are exposed to the public internet. Therefore, ensure that network security precautions are taken before uploading sensitive files to this instance of NeuralDB Enterprise. The network settings can be changed in the `create_vms.sh` file if you wish to launch on a VPC.
We will also be introducing user-friendly features shortly that will enable the deployment of NeuralDB Enterprise within a private VPC on Azure.