# Table of Contents

* [bazaar\_client](#bazaar_client)
  * [Model](#bazaar_client.Model)
  * [NeuralDBClient](#bazaar_client.NeuralDBClient)
    * [\_\_init\_\_](#bazaar_client.NeuralDBClient.__init__)
    * [search](#bazaar_client.NeuralDBClient.search)
    * [insert](#bazaar_client.NeuralDBClient.insert)
    * [associate](#bazaar_client.NeuralDBClient.associate)
    * [upvote](#bazaar_client.NeuralDBClient.upvote)
    * [downvote](#bazaar_client.NeuralDBClient.downvote)
  * [ModelBazaar](#bazaar_client.ModelBazaar)
    * [\_\_init\_\_](#bazaar_client.ModelBazaar.__init__)
    * [sign\_up](#bazaar_client.ModelBazaar.sign_up)
    * [log\_in](#bazaar_client.ModelBazaar.log_in)
    * [push\_model](#bazaar_client.ModelBazaar.push_model)
    * [pull\_model](#bazaar_client.ModelBazaar.pull_model)
    * [list\_models](#bazaar_client.ModelBazaar.list_models)
    * [train](#bazaar_client.ModelBazaar.train)
    * [await\_train](#bazaar_client.ModelBazaar.await_train)
    * [deploy](#bazaar_client.ModelBazaar.deploy)
    * [await\_deploy](#bazaar_client.ModelBazaar.await_deploy)
    * [undeploy](#bazaar_client.ModelBazaar.undeploy)
    * [list\_deployments](#bazaar_client.ModelBazaar.list_deployments)
    * [connect](#bazaar_client.ModelBazaar.connect)

<a id="bazaar_client"></a>

# bazaar\_client

<a id="bazaar_client.Model"></a>

## Model

```python
class Model()
```

A class representing a model listed on NeuralDB Enterprise.

**Attributes**:

- `_model_identifier` _str_ - The unique identifier for the model.
  

**Methods**:

  __init__(self, model_identifier: str) -> None:
  Initializes a new instance of the Model class.
  

**Arguments**:

- `model_identifier` _str_ - An optional model identifier.
  
  model_identifier(self) -> str:
  Getter method for accessing the model identifier.
  

**Returns**:

- `str` - The model identifier, or None if not set.

<a id="bazaar_client.NeuralDBClient"></a>

## NeuralDBClient

```python
class NeuralDBClient()
```

A client for interacting with the deployed NeuralDB model.

**Attributes**:

- `deployment_identifier` _str_ - The identifier for the deployment.
- `base_url` _str_ - The base URL for the deployed NeuralDB model.
  

**Methods**:

  __init__(self, deployment_identifier: str, base_url: str) -> None:
  Initializes a new instance of the NeuralDBClient.
  
  search(self, query: str, top_k: int = 10) -> List[dict]:
  Searches the ndb model for relevant search results.
  
  insert(self, files: List[str]) -> None:
  Inserts documents into the ndb model.
  
  associate(self, text_pairs: List[Dict[str, str]]) -> None:
  Associates source and target string pairs in the ndb model.
  
  upvote(self, text_id_pairs: List[Dict[str, str | int]]) -> None:
  Upvotes a response in the ndb model.
  
  downvote(self, text_id_pairs: List[Dict[str, str | int]]) -> None:
  Downvotes a response in the ndb model.

<a id="bazaar_client.NeuralDBClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(deployment_identifier, base_url)
```

Initializes a new instance of the NeuralDBClient.

**Arguments**:

- `deployment_identifier` _str_ - The identifier for the deployment.
- `base_url` _str_ - The base URL for the deployed NeuralDB model.

<a id="bazaar_client.NeuralDBClient.search"></a>

#### search

```python
@check_deployment_decorator
def search(query, top_k=10)
```

Searches the ndb model for similar queries.

**Arguments**:

- `query` _str_ - The query to search for.
- `top_k` _int_ - The number of top results to retrieve (default is 10).
  

**Returns**:

-  `Dict` - A dict of search results containing keys: `query_text` and `references`.

<a id="bazaar_client.NeuralDBClient.insert"></a>

#### insert

```python
@check_deployment_decorator
def insert(files: List[str])
```

Inserts documents into the ndb model.

**Arguments**:

- `files` _List[str]_ - A list of file paths to be inserted into the ndb model.

<a id="bazaar_client.NeuralDBClient.associate"></a>

#### associate

```python
@check_deployment_decorator
def associate(text_pairs: List[Dict[str, str]])
```

Associates source and target string pairs in the ndb model.

**Arguments**:

- `text_pairs` _List[Dict[str, str]]_ - List of dictionaries where each dictionary has `source` and `target` keys.

<a id="bazaar_client.NeuralDBClient.upvote"></a>

#### upvote

```python
@check_deployment_decorator
def upvote(text_id_pairs: List[Dict[str, str | int]])
```

Upvotes a response in the ndb model.

**Arguments**:

- `text_id_pairs` _List[Dict[str, Union[str, int]]]_ -  List of dictionaries where each dictionary has 'query_text' and 'reference_id' keys.

<a id="bazaar_client.NeuralDBClient.downvote"></a>

#### downvote

```python
@check_deployment_decorator
def downvote(text_id_pairs: List[Dict[str, str | int]])
```

Downvotes a response in the ndb model.

**Arguments**:

- `text_id_pairs` _List[Dict[str, Union[str, int]]]_ -  List of dictionaries where each dictionary has 'query_text' and 'reference_id' keys.

<a id="bazaar_client.ModelBazaar"></a>

## ModelBazaar

```python
class ModelBazaar(Bazaar)
```

A class representing ModelBazaar, providing functionality for managing models and deployments.

**Attributes**:

- `_base_url` _str_ - The base URL for the Model Bazaar.
- `_cache_dir` _Union[Path, str]_ - The directory for caching downloads.
  

**Methods**:

  __init__(self, base_url: str, cache_dir: Union[Path, str] = "./bazaar_cache") -> None:
  Initializes a new instance of the ModelBazaar class.
  
  sign_up(self, email: str, password: str, username: str) -> None:
  Signs up a user and sets the username for the ModelBazaar instance.
  
  log_in(self, email: str, password: str) -> None:
  Logs in a user and sets user-related attributes for the ModelBazaar instance.
  
  push_model(self, model_name: str, local_path: str, access_level: str = "public") -> None:
  Pushes a model to the Model Bazaar.
  
  pull_model(self, model_identifier: str) -> NeuralDBClient:
  Pulls a model from the Model Bazaar and returns a NeuralDBClient instance.
  
  list_models(self) -> List[dict]:
  Lists available models in the Model Bazaar.
  
  train(self, model_name: str, docs: List[str], doc_type: str = "local", sharded: bool = False, is_async: bool = False, base_model_identifier: str = None, train_extra_options: dict = {}) -> Model:
  Initiates training for a model and returns a Model instance.
  
  await_train(self, model: Model) -> None:
  Waits for the training of a model to complete.
  
  deploy(self, model_identifier: str, deployment_name: str, is_async: bool = False) -> NeuralDBClient:
  Deploys a model and returns a NeuralDBClient instance.
  
  await_deploy(self, ndb_client: NeuralDBClient) -> None:
  Waits for the deployment of a model to complete.
  
  undeploy(self, ndb_client: NeuralDBClient) -> None:
  Undeploys a deployed model.
  
  list_deployments(self) -> List[dict]:
  Lists the deployments in the Model Bazaar.
  
  connect(self, deployment_identifier: str) -> NeuralDBClient:
  Connects to a deployed model and returns a NeuralDBClient instance.

<a id="bazaar_client.ModelBazaar.__init__"></a>

#### \_\_init\_\_

```python
def __init__(base_url: str, cache_dir: Union[Path, str] = "./bazaar_cache")
```

Initializes a new instance of the ModelBazaar class.

**Arguments**:

- `base_url` _str_ - The base URL for the Model Bazaar.
- `cache_dir` _Union[Path, str]_ - The directory for caching downloads.

<a id="bazaar_client.ModelBazaar.sign_up"></a>

#### sign\_up

```python
def sign_up(email, password, username)
```

Signs up a user and sets the username for the ModelBazaar instance.

**Arguments**:

- `email` _str_ - The email of the user.
- `password` _str_ - The password of the user.
- `username` _str_ - The desired username.

<a id="bazaar_client.ModelBazaar.log_in"></a>

#### log\_in

```python
def log_in(email, password)
```

Logs in a user and sets user-related attributes for the ModelBazaar instance.

**Arguments**:

- `email` _str_ - The email of the user.
- `password` _str_ - The password of the user.

<a id="bazaar_client.ModelBazaar.push_model"></a>

#### push\_model

```python
def push_model(model_name: str, local_path: str, access_level: str = "public")
```

Pushes a model to the Model Bazaar.

**Arguments**:

- `model_name` _str_ - The name of the model.
- `local_path` _str_ - The local path of the model.
- `access_level` _str_ - The access level for the model (default is "public").

<a id="bazaar_client.ModelBazaar.pull_model"></a>

#### pull\_model

```python
def pull_model(model_identifier: str)
```

Pulls a model from the Model Bazaar and returns a NeuralDBClient instance.

**Arguments**:

- `model_identifier` _str_ - The identifier of the model.
  

**Returns**:

- `NeuralDBClient` - A NeuralDBClient instance.

<a id="bazaar_client.ModelBazaar.list_models"></a>

#### list\_models

```python
def list_models()
```

Lists available models in the Model Bazaar.

**Returns**:

- `List[dict]` - A list of dictionaries containing information about available models.

<a id="bazaar_client.ModelBazaar.train"></a>

#### train

```python
def train(model_name: str,
          docs: List[str],
          doc_type: str = "local",
          sharded: bool = False,
          is_async: bool = False,
          base_model_identifier: str = None,
          train_extra_options: dict = {})
```

Initiates training for a model and returns a Model instance.

**Arguments**:

- `model_name` _str_ - The name of the model.
- `docs` _List[str]_ - A list of document paths for training.
- `doc_type` _str_ - Specifies document location type : "local"(default), "nfs" or "s3".
- `sharded` _bool_ - Single or mixture of model training (default is False).
- `is_async` _bool_ - Whether training should be asynchronous (default is False).
- `base_model_identifier` _str_ - The identifier of the base model (optional).
- `train_extra_options` _dict_ - Describes required parameters of sharded training :
    * num_model_shards : number of shards in which data is divided; one model trains on each data shard.
    * allocation_memory: amount of memory(in MBs) to assign for data sharding job. (Suggested : 10x data size)
    * model_cores      : cpu cores to be allocated for each model train job.
    * model_memory     : amount of memory(in MBs) to assign for each data train job.
    * fhr              : input_dimension for individual model.
    * embedding_dim    : hidden_dimension for individual model.
    * output_dim       : output_dimension for individual model.
    * max_in_memory_batches    : number of batches to train in one iteration.

    * In case of using .csv documents, user must provide required values for `csv_*` fields : `csv_id_column`, `csv_strong_columns`, `csv_weak_columns` and `csv_reference_columns`.
  

**Returns**:

- `Model` - A Model instance.

<a id="bazaar_client.ModelBazaar.await_train"></a>

#### await\_train

```python
def await_train(model: Model)
```

Waits for the training of a model to complete.

**Arguments**:

- `model` _Model_ - The Model instance.

<a id="bazaar_client.ModelBazaar.deploy"></a>

#### deploy

```python
def deploy(model_identifier: str, deployment_name: str, is_async=False)
```

Deploys a model and returns a NeuralDBClient instance.

**Arguments**:

- `model_identifier` _str_ - The identifier of the model.
- `deployment_name` _str_ - The name for the deployment.
- `is_async` _bool_ - Whether deployment should be asynchronous (default is False).
  

**Returns**:

- `NeuralDBClient` - A NeuralDBClient instance.

<a id="bazaar_client.ModelBazaar.await_deploy"></a>

#### await\_deploy

```python
def await_deploy(ndb_client: NeuralDBClient)
```

Waits for the deployment of a model to complete.

**Arguments**:

- `ndb_client` _NeuralDBClient_ - The NeuralDBClient instance.

<a id="bazaar_client.ModelBazaar.undeploy"></a>

#### undeploy

```python
def undeploy(ndb_client: NeuralDBClient)
```

Undeploys a deployed model.

**Arguments**:

- `ndb_client` _NeuralDBClient_ - The NeuralDBClient instance.

<a id="bazaar_client.ModelBazaar.list_deployments"></a>

#### list\_deployments

```python
def list_deployments()
```

Lists the deployments in the Model Bazaar.

**Returns**:

- `List[dict]` - A list of dictionaries containing information about deployments.

<a id="bazaar_client.ModelBazaar.connect"></a>

#### connect

```python
def connect(deployment_identifier: str)
```

Connects to a deployed model and returns a NeuralDBClient instance.

**Arguments**:

- `deployment_identifier` _str_ - The identifier of the deployment.
  

**Returns**:

- `NeuralDBClient` - A NeuralDBClient instance.

