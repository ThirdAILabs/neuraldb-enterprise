# Install NeuralDB Enterprise on Any Cluster

Launch NeuralDB Enterprise on your own cluster in minutes.

This installation assumes the following:
- Every node is running a clean image of Ubuntu Server 22.04 LTS
- There is at least one node in the cluster with a public IP
  - You are able to SSH into every node using the node with a public IP as a proxy jump node, and you have sudo access to each node
  - This node must expose ports 22 and 80 to the public network
- Every node can access any other node in the cluster through the nodes' private IPs
  - Every node in the cluster must expose ports 22, 80, 4646, and 2049 to the private network
  - The node running the PostgreSQL server must expose port 5432 to the private network
- Every node can pull from the internet
- Every node has at least 8GB of memory and 1 CPU

### Installation Instructions

These instructions will walk through how to set up NeuralDB Enterprise on your Linux cluster, using your personal machine as an access point. These instructions should not be executed directly on the cluster nodes, but rather on a machine that has SSH access to the node with the public IP.

1. Populate `config.json` with the IPs of the nodes in your cluster
   - `config.json` is currently populated with an example of what a valid configuration might look like. There are two attributes in the top level json object:
     - `nodes` is where you will set the configuration of the nodes in your cluster for NeuralDB Enterprise. In the `nodes` attribute, you will define the IPs of all the nodes in your cluster. Each entry in `nodes` is a json object that must have an attribute called `private_ip`, specifying the private IP of that node. You must also define which nodes get assigned which services. There are 4 main services (web ingress, SQL server, NFS server, and Nomad server) that need to run on the cluster, and you can choose which nodes run which services.
       - `web_ingress` must be an attribute in the node that has a public IP. In the `web_ingress` object, there are three attributes:
         - `public_ip` is the public IP of this node. This public IP should direct requests to the node's private IP.
         - `run_jobs` is a boolean that specifies whether to run CPU/memory intensive jobs (such as training or deploying neuralDBs) on this node. For example, if the node possessing the public IP is not compute-heavy and is used solely as a proxy server, this attribute can be set to false.
         - `ssh_username` is the username used to SSH into this node using the `public_ip` from your personal machine used to set up NeuralDB Enterprise. This will most likely be the same as the `ssh_username` supplied below, so you can copy that value here.
       - `sql_server` should be placed in exactly one node where you would like the Postgres server to run. This database will contain the data that tracks NeuralDB creation/deployment, user creation, and other information relating to the Model Bazaar. The data for the SQL server will be stored on the disk of the node where `sql_server` is specified. If you wish to use an existing Postgres database, please refer to the `sql_uri` key and omit this key. Only one of `sql_server` and `sql_uri` may be specified.
         - `database_dir` is the path on this node where the SQL database data will be stored.
         - `database_password` is the password for the SQL database created. The name of the database is `modelbazaar` and the username for the database is `modelbazaaruser`, as specified in the file `setup_postgresql.sh`.
       - `shared_file_system` should be placed in exactly one node where the shared directory will be set up for the nodes in the cluster. We need a shared filesystem that each node has access to so we can train a model on one node, and be able to deploy that model from any other node.
         - `shared_dir` is the path to the directory that will be used as a shared filesystem for all the nodes in the cluster. The setup scripts will automatically create this directory if it doesn't exist.
         - `create_nfs_server` should be set to true if `shared_dir` is not already accessible by all nodes. In this case, an NFS server will be set up on this node and all other nodes will mount this NFS onto itself at `shared_dir`. If `shared_dir` is in a directory that is already shared to all nodes, this attribute can be set to false, and `shared_file_system` can technically be placed in any node, as no NFS server will be created.
       - `nomad_server` should be placed in exactly one node where the Nomad Server will run. Generally, this should be placed in a node with a higher uptime, as this process handles the orchestration of all the other services in NeuralDB Enterprise.
     - `ssh_username` is the username used to SSH into all other nodes in the cluster using their private IPs. The general setup for each node is to SSH into it using it's private IP through a proxy jump from the `web_ingress` node. Therefore, your local machine's public key should be listed in the `~/.ssh/authorized_keys` file of the `ssh_username` user your are supplying here. Check out https://askubuntu.com/questions/46424/how-do-i-add-ssh-keys-to-authorized-keys-file for more info.
     - `sql_uri` is a Postgres connection string for an existing Postgres database. Ensure that the user in this URI has access to edit the database, and ensure that all nodes are granted network access to the database. If you do not have an existing Postgres database, refer to the `sql_server` key and omit this key. Only one of `sql_uri` and `sql_server` may be specified. If you would like to populate the connection string using environment variables, set `sql_uri` to `"ENV"`. This will assume the following environment variables are present on the machine that is running the `nomad_server`.
       - `DB_USERNAME`
       - `DB_PASSWORD`
       - `DB_HOSTNAME`
       - `DB_NAME`
       - The Postgres connection string will be constructed like so: `postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOSTNAME}:5432/${DB_NAME}`
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
   - `admin_mail`, `admin_username`, and `admin_password` will used to create a default admin user for your installation of NeuralDB Enterprise. You will be able to log in to Model Bazaar using these credentials. `admin_username` and `admin_password` has to be alpha-numeric.
   - Set `genai_key` to the API key for your generative model. Currently, `genai_key` must be an OpenAI key. If this is not set, then generative answers will not be displayed when querying a NeuralDB.
   - `jwt_secret` is used to encrypt authentication tokens for logins to Model Bazaar. This can be set to any random string, but make sure to save this value.
   - `autoscaling_enabled` determines whether NeuralDB Enterprise automatically autoscales the number of deployments under heavy query loads.
   - `autoscaler_max_count` determines the maximum number of deployment jobs that are spun up to handle large query loads.
   - (Optional arg. Only applies for users that have specifically contacted us about airgapped support) `airgapped_license_path` is a path to the file license we'll send you. The file must be named `license.serialized`.
7. Run `bash setup.sh` in the Terminal.

Wait for the setup process to complete (approximately 10 minutes), and you have launched NeuralDB Enterprise on your own VM cluster!

Paste the `public_ip` of your `web_ingress` node into your browser, and you should see a login screen, where you can create an account, verify your email, and start training NeuralDB's! An admin account will already be created for you using `admin_mail` and `admin_password` as the login credentials.

Ensure that network security precautions are taken before uploading sensitive files to this instance of NeuralDB Enterprise, if your public IP is exposed to the internet.


#### Extra Precautions

By default, port 4646 is exposed on nodes all nodes running a Nomad client. This means that if a node has a public IP, that port can be accessed externally. Port 4646 allows you to see the Nomad GUI in your browser. You can see the nodes in your cluster as well as all docker containers launched on the cluster. This is a good way to debug issues with train/deploy jobs.

To restrict access to the Nomad GUI port, you can set up firewall rules on your nodes so that only localhost will have access to those ports. SSH into each node where you wish to restrict the port, and run the following commands to use `ufw` (uncomplicated firewall) to block external network calls to interact with port 4646.

```
sudo apt install ufw
sudo ufw allow ssh
sudo ufw enable
sudo ufw default allow incoming
sudo ufw allow in from 172.17.0.0/16 to any port 4646
sudo ufw deny 4646
```

If you want to visit the Nomad GUI, or any other service on a port that you wish to block using the above steps, you will have to port forward the corresponding port to your local machine. To do this, run the following command, replacing the placeholder values with your values.
```
ssh -L {port}:localhost:{port} {ssh_username}@{node_ip}
```

For example, if my node's IP was 12.34.56.78, and I wanted to see the Nomad GUI, I would run the following:
```
ssh -L 4646:localhost:4646 user@12.34.56.78
```

Now I can paste localhost:4646 into my browser and view the Nomad GUI.

As an extra security feature, we enable the Nomad ACL system, so that the Nomad GUI is only able to be accessed to individuals with a management token. This token can be found on your headnode at the path `/opt/neuraldb_enterprise/nomad_data/management_token.txt` as the field `Secret ID`. You can paste this key into the GUI to gain access to the Nomad dashboard.