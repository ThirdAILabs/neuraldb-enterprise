# NeuralDB Enterprise for On-Prem Cluster

Launch NeuralDB Enterprise on your own cluster in minutes.

This installation assumes the following:
- Each node in the cluster has a public and private IP
- You have at least 2 nodes in the cluster
- Each node is running Ubuntu Server 22.04 LTS
- Your current machine has SSH access to each node in the cluster, and your public key is an accepted host on each node
- Each node can pull from the internet
- Every node can access any other node in the cluster through the nodes' private IPs

### Instructions for MacOS
1. Populate `config.json` with the IPs of the nodes in your cluster
   - `HEADNODE_IP` and `PRIVATE_HEADNODE_IP` should be the public and private IPs respectively of one of your nodes.
   - `PROXY_CLIENT_IP` and `PRIVATE_PROXY_CLIENT_IP` should be the public and private IPs respectively of another one of your nodes. The public IP of this node will be used to interact with the NeuralDB Enterprise UI through a browser.
   - Enter the the public and private IPs of the rest of your nodes in `CLIENTNODE_IP` and `PRIVATE_CLIENTNODE_IP` respectively.
2. Install `homebrew`: https://brew.sh.
3. Install or upgrade `bash` by running `brew install bash` in the Terminal.
4. Install `jq` by running `brew install jq` in the Terminal.
5. Navigate into the `on-prem` directory in this repository.
6. Edit the `variables.sh` file to reflect your desired settings. 
   - Ensure that `license_path` is set correctly to a path on your local machine.
   - Set `admin_name` to the username used to SSH into each of the nodes in your cluster
   - `admin_mail` and `admin_password` will be your login information to NeuralDB Enterprise
   - `postgresql_data_dir` shouldn't have to change, unless the version of postgresql is different on your machines. Then you can set this variable to the correct version of postgresql.
7. Run `bash setup.sh` in the Terminal.

Wait for the setup process to complete (approximately 10 minutes), and you have launched NeuralDB Enterprise on your own Azure VM cluster!

In the `config.json` file in the `on-prem` directory, find the value for `PROXY_CLIENT_IP`. Paste the IP address into your browser, and you should see a login screen, where you can create an account, verify your email, and start training NeuralDB's!