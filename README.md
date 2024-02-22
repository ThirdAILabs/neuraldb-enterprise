# NeuralDB Enterprise for MoniA Customers

This branch is for MoniA customers only.

### Obtain a NeuralDB Enterprise License from Cercle Business
Visit https://cercle.business/en/inscription-neuraldb to receive a license to deploy NeuralDB Enterprise on your own cluster. Enter your email and specify the size of your cluster, and a license will be emailed to you.

### Quick Start with Python

Once you have configured your cluster settings and are ready to start NeuralDB Enterprise, move to the `python` directory within the cloned or downloaded repository. Here, you can start your cluster using a simple command:

```bash
cd python
python start-cluster.py -y path/to/your/config.yaml
```

This command initiates the cluster setup using the configuration specified in `config.yaml`. Ensure you have updated this file with your cluster's specifics before running the command.

### Deploy ThirdAI's NeuralDB Enterprise on any cluster within a few minutes.

Follow the instructions located in the `install` directory to get started with NeuralDB Enterprise on any cluster, whether it be on-prem or in the cloud

We also provide instructions to spin up your own cluster on a cloud provider of your choice. Check out the `install-on-azure` directory to get started with NeuralDB Enterprise on your Azure account (AWS and GCP instructions coming soon).


### Log in to other MoniA Customers' NeuralDB Enterprise Instances
In the MoniA-specific version of NeuralDB Enterprise, there is an additional GET endpoint at /api/user/monia-login. This endpoint should be supplied with a Bearer token, which will be the MoniA Customer Token. The endpoint will return an auth token that corresponds to a NeuralDB Enterprise account for that specific customer. This auth token can be used as a replacement token that would have been retrieved from /api/user/email-login. These credentials will have protected access to all other MoniA customers' NeuralDBs, which will allow for MoniA customers to share their knowledge bases with each other.


### Documentation
You can interact with NeuralDB Enterprise through the UI, or through the API included in the `thirdai` python package. The `documentation` directory contains the docs on how to use the NeuralDB Enterprise API.
