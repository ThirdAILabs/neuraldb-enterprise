# Install NeuralDB Enterprise on Any Cluster

Launch NeuralDB Enterprise on your own cluster in minutes.

This installation assumes the following:
- Every node is running a clean image of Ubuntu Server 22.04 LTS
- Your current machine has SSH access to each node in the cluster through their public IPs, and your public key is an accepted host on every node
- Every node can pull from the internet
- Every node can access any other node in the cluster through the nodes' private IPs
- Every node has at least 8GB of memory and 1 CPU

### Installation Instructions

These instructions will walk through how to set up NeuralDB Enterprise on your Linux cluster, using your personal machine as an access point. Note that these instructions should not be executed directly on the cluster nodes, but rather on a machine that has SSH access to nodes in the cluster.

1. Populate `config.json` with the IPs of the nodes in your cluster
   - `HEADNODE_IP` and `PRIVATE_HEADNODE_IP` should be the public and private IPs respectively of one of your nodes. NeuralDB Enterprise's UI will be accessible from `HEADNODE_IP`.
   - Enter the the public and private IPs of the rest of your nodes in `CLIENTNODE_IP` and `PRIVATE_CLIENTNODE_IP` respectively. If you don't have any nodes other than the HEADNODE, then you can leave these lists empty. 
   - Public IP requirements: they should be accessible to the machine you are setting up NeuralDB Enterprise with. They don't necessarily have to be exposed to the public internet, but they should be exposed to the network where you expect users to interact with NeuralDB Enterprise from.
   - Private IP requirements: they should be accessible to all the nodes in the cluster. This is the IP that will be used by every node to communicate with each other. This can technically be the same as the public IP.
2. The following steps should be executed in a bash shell on the machine you with to launch NeuralDB Enterprise with. This can be any machine (e.g. laptop, VM, etc.)
3. Install or upgrade `bash` in your Terminal.
   - On MacOS, run `brew install bash` in the Terminal. You may have to first install `homebrew`: https://brew.sh.
   - On Debian/Ubuntu, run `sudo apt install bash` in the Terminal. 
   - On other platforms, please look up how to install `bash` to the Terminal.
4. Install `jq` in your Terminal.
   - On MacOS, run `brew install jq` in the Terminal. You may have to first install `homebrew`: https://brew.sh.
   - On Debian/Ubuntu, run `sudo apt install jq` in the Terminal.
   - On other platforms, please look up how to install `jq` to the Terminal.
5. Navigate into the `install` directory in this repository.
6. Edit the `variables.sh` file to reflect your desired settings. 
   - Ensure that `license_path` is set correctly to a path on your machine. This should point to the NeuralDB Enterprise License that you recieved in an email.
   - Set `admin_name` to the username used to SSH into each of the nodes in your cluster
   - `admin_mail` and `admin_password` will be your login information to NeuralDB Enterprise
   - Set `genai_key` to the API key for your generative model. Currently, `genai_key` must be an OpenAI key. 
   - Set `shared_dir` to the location of the shared directory which should be accessible by every node. (leave this field if nodes were set up using our `install-on-azure` script). Useful when neural-db enterprise needs to be installed on private clusters.
   - Set `setup_nfs`:
      -  `True`: Sets up a NFS on the shared-directory so that nodes can access each others file (leave this field if nodes were set up using our `install-on-azure` script.)
      - `False`: Doesn't set up a NFS on the shared-directory. Generally, the nodes of private cluster already have the access of the shared-directory.
7. Run `bash setup.sh` in the Terminal.

Wait for the setup process to complete (approximately 10 minutes), and you have launched NeuralDB Enterprise on your own VM cluster!

Paste the `HEADNODE_IP` into your browser, and you should see a login screen, where you can create an account, verify your email, and start training NeuralDB's! An admin account will already be created for you using `admin_mail` and `admin_password` as the login credentials.

Ensure that network security precautions are taken before uploading sensitive files to this instance of NeuralDB Enterprise, if your public IPs are exposed to the internet.


COMING SOON:
- Scripts to launch NeuralDB Enterprise on a cluster containing a single node with a public IP, while the rest of the nodes have private IPs. 
