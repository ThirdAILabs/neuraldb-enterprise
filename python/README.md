# NeuralDB Cluster Setup Tool

The scripts here automate the setup of NeuralDB clusters across various environments including AWS, Azure, and self-hosted configurations. It manages everything from infrastructure deployment to application setup.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed and configured:

- **Python 3.8 or higher**
- **`pip` for Python package management**
- **`git`** (optional, if cloning the repository)

### Cloud Environment Setup

- **AWS CLI:**
  - Install the AWS CLI on your machine. Detailed installation instructions can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
  - Log into the AWS CLI using the AWS account that will be used to spin up the resources for the cluster. Instructions for configuring the CLI can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

- **Azure CLI:**
  - Install the Azure CLI on your machine. Detailed installation instructions can be found [here](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos).
  - Log into the Azure CLI using the Azure account that will be used to spin up the resources for the cluster. Instructions for signing into the CLI can be found [here](https://learn.microsoft.com/en-us/cli/azure/get-started-with-azure-cli#how-to-sign-into-the-azure-cli).

Ensure that API keys and access credentials are correctly configured for the environment you intend to use (AWS or Azure).

## Installation

1. **Clone the repository** (optional):

   ```bash
   git clone https://github.com/ThirdAILabs/neuraldb-enterprise.git
   cd neuraldb-enterprise/python
   ```

2. **Install required Python packages**:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create and update a YAML configuration file from the provided templates in the `configuration_files` directory. Adjust the file with your specific settings for AWS, Azure, or self-hosted environments.

## Usage

Run the setup tool with the following command:

```bash
python start-cluster.py -y path/to/your/config.yaml
```

Options:
- `-y, --yaml`: Specifies the path to the YAML configuration file.
- `-l, --logfile`: (Optional) Specifies the path to the log file.

## Logging

Logs are written to `neuraldb_enterprise.log` by default, which can be configured via the `-l` option.

## Troubleshooting

- Verify network permissions and security groups allow required traffic.
- Check the logs for detailed error messages.

