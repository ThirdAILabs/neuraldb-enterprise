# Clean Models and Deployments

Models and deployments that have failed or become redundant can consume valuable resources. The following instructions guide you on how to clean up such instances.

These instructions assume that you already have the enterprise cluster set up, along with the corresponding `config.json` and `variables.sh` values.

## Clean Model
1. Execute `source clean_models.sh <status> <model_id>`
    - **Status:** not_started | starting | in_progress | stopping | complete | failed
    - **Model_id:** Find it on the Nomad UI job using the following instructions:
        * a. Go to http://<`head node ip`>:4646/
        * b. Open the `Jobs` tab
        * c. The required model will be `train-<model_id>`

   **Default:** `All`. Delete all models with the given status.

2. Log in to the head node
    * a. `ssh <admin_name>@<head-node ip>`
    * b. Navigate to the directory `shared_dir/clean_up`
    * c. Run the script `source clean_models.sh`

   The script will interactively ask for confirmation before deleting the model.

## Clean Deployment
1. Execute `source clean_deployments.sh <status> <deployment_id>`
    - **Status:** not_started | starting | in_progress | stopping | complete | failed
    - **Deployment_id:** Find it on the Nomad UI job using the following instructions:
        * a. Go to http://<`head node ip`>:4646/
        * b. Open the `Jobs` tab
        * c. The required deployment will be `deployment-<deployment_id>`

   **Default:** `All`. Delete all deployments with the given status.

2. Log in to the head node
    * a. `ssh <admin_name>@<head-node ip>`
    * b. Navigate to the directory `<shared_dir>/clean_up`
    * c. Run the script `source clean_deployments.sh`

   The script will interactively ask for confirmation before deleting the deployment.

# Restart Enterprise

These instructions will restart the enterprise, deleting all models and deployments and reverting the enterprise to its initial state.

Run `source restart_enterprise.sh`
