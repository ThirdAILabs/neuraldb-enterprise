from thirdai.neural_db import ModelBazaar
from thirdai import neural_db as ndb
import thirdai


filenames = [
    "/Users/pratikqpranav/Downloads/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data/22ZOCVPAF2GSGXR357RM7UT4Z22RS2LH.pdf",
    "/Users/pratikqpranav/Downloads/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data/23JCEIKVL65X2RGSARNY2VOUNXBTJ5AS.pdf"
]



thirdai.licensing.activate("002099-64C584-3E02C8-7E51A0-DE65D9-V3")

bazaar = ModelBazaar(
    base_url="http://13.86.92.162/api/"
) 

bazaar.log_in(email="pratik@thirdai.com", password="thirdai")

train_extra_options = {
    "num_models_per_shard": 2,
    "num_shards": 2,
    "allocation_memory": 10000,
    "model_cores": 6,
    "model_memory": 6800,
}

model_name = "pdf-test-model-7"


model = bazaar.train(
    model_name=model_name,
    unsupervised_docs=filenames,
    doc_type="local",
    sharded=True,
    is_async=True,
    train_extra_options=train_extra_options,
)
bazaar.await_train(model)
print("Done Training")

ndb_client = bazaar.deploy(
    model_identifier=model.model_identifier,
    deployment_name="deployment-4",
    is_async=True,
)

bazaar.await_deploy(ndb_client)

results = ndb_client.search(query="tell me about something", top_k="5")

query_text = results["query_text"]
references = results["references"]
for reference in references:
    print(reference["text"])
