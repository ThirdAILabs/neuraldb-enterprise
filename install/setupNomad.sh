echo "JOB STARTED"

git clone -b single-machine https://github.com/ThirdAILabs/neuraldb-enterprise.git

cd neuraldb-enterprise/

sudo bash ./nomad/nomad_scripts/install_nomad.sh -y
