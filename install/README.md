# Install NeuralDB Enterprise on Any Cluster

Launch NeuralDB Enterprise on your own cluster in minutes.

This installation assumes the following:
- Every node is running a clean image of Ubuntu Server 22.04 LTS
- Your current machine has SSH access to each node in the cluster through their public IPs, and your public key is an accepted host on every node
- Every node can pull from the internet
- Every node can access any other node in the cluster through the nodes' private IPs

### Instructions for MacOS
1. Populate `config.json` with the IPs of the nodes in your cluster
   - `HEADNODE_IP` and `PRIVATE_HEADNODE_IP` should be the public and private IPs respectively of one of your nodes. NeuralDB Enterprise's UI will be accessible from `HEADNODE_IP`.
   - Enter the the public and private IPs of the rest of your nodes in `CLIENTNODE_IP` and `PRIVATE_CLIENTNODE_IP` respectively. If you don't have any nodes other than the HEADNODE, then you can leave these lists empty. 
   - Public IP requirements: they should be accessible to the machine you are setting up NeuralDB Enterprise with. They don't necessarily have to be exposed to the public internet, but they should be exposed to the network where you expect users to interact with NeuralDB Enterprise from.
   - Private IP requirements: they should be accessible to all the nodes in the cluster. This is the IP that will be used by every node to communicate with each other. This can technically be the same as the public IP.
2. The following steps should be executed in a bash shell on the machine you with to launch NeuralDB Enterprise with. This can be any machine (e.g. laptop, VM, etc.)
3. Install `homebrew`: https://brew.sh.
4. Install or upgrade `bash` by running `brew install bash` in the Terminal.
5. Install `jq` by running `brew install jq` in the Terminal.
6. Navigate into the `install` directory in this repository.
7. Edit the `variables.sh` file to reflect your desired settings. 
   - Ensure that `license_path` is set correctly to a path on your machine. This should point to the NeuralDB Enterprise License that you recieved in an email.
   - Set `admin_name` to the username used to SSH into each of the nodes in your cluster
   - `admin_mail` and `admin_password` will be your login information to NeuralDB Enterprise
8. Run `bash setup.sh` in the Terminal.

Wait for the setup process to complete (approximately 10 minutes), and you have launched NeuralDB Enterprise on your own Azure VM cluster!

Paste the `HEADNODE_IP` into your browser, and you should see a login screen, where you can create an account, verify your email, and start training NeuralDB's! An admin account will already be created for you using `admin_mail` and `admin_password` as the login credentials.

Ensure that network security precautions are taken before uploading sensitive files to this instance of NeuralDB Enterprise, if your public IPs are exposed to the internet.

COMING SOON:
- Scripts to launch NeuralDB Enterprise on a cluster containing a single node with a public IP, while the rest of the nodes have private IPs. 