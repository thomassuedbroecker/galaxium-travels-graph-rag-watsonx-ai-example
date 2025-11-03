## Fast start

This is a quick-start document that contains only the main configuration steps, with no additional documentation. For details, please visit the blog post above.

### 1. Clone the repository

```sh
git clone https://github.com/thomassuedbroecker/galaxium-travels-graph-rag-watsonx-ai-example.git
cd galaxium-travels-graph-rag-watsonx-ai-example
```

### 2. Add the credentials

* Create an environment file and a `config.toml` file.

```sh
cd code
cat ./langgraph-graph-rag/template.env > ./langgraph-graph-rag/.env
cat ./langgraph-graph-rag/config.toml.example > ./langgraph-graph-rag/config.toml
```

* Insert the needed configurations

**Environment variable** file content:

```sh
# One of the below is required.
# To determine your `watsonx_apikey`, refer to `IBM Cloud console API keys <https://cloud.ibm.com/iam/apikeys>`_.
export WATSONX_APIKEY=
export WATSONX_TOKEN=
export REGION=us-south

# should follow the format: `https://{REGION}.ml.cloud.ibm.com`
export WATSONX_URL=https://${REGION}.ml.cloud.ibm.com

# Deployment space id is required to create deployment with AI service content.
export WATSONX_SPACE_ID=

# variable, that is populated with last created deployment_id every time when command `watsonx-ai service new` finish successfully
export WATSONX_DEPLOYMENT_ID=

# Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export NEO4J_DATABASE="neo4j"

# Model IDs
export WATSONX_MODEL_ID="meta-llama/llama-3-3-70b-instruct"
export WATSONX_EMBEDDING_MODEL_ID="ibm/granite-embedding-278m-multilingual"

#Langfuse you need to generate the keys
export LANGFUSE_PUBLIC_KEY=YOUR_KEY
export LANGFUSE_SECRET_KEY=YOUR_KEY
export LANGFUSE_HOST=http://localhost:3000

# Filename runtime log output
export FILENAME_AGENT_LOG_OUTPUT="../../scripts/output_data"

# LangChain GraphTransformer
export USE_PROMPT=false
export USE_ADDITIONAL_INSTRUCTIONS=true
export USE_NODES_RELATION_DEFINITIONS=false
```

**Config.toml** file content:

```sh
[cli.options]
  # If true, cli `invoke` command is trying to use `ai_service.generate_stream` function for local tests, and `ai_service.generate` otherwise.
  # Default: true
 stream = true

  # Path to json file with a complete payload that will be send to proper AI service generate function.
  # Note that, the payload file will be only used when no `query` is provided when running `invoke ` command
  # Default: None
 payload_path = ""

[deployment]
  # One of the below is required.
  # To determine your `api_key`, refer to `IBM Cloud console API keys <https://cloud.ibm.com/iam/apikeys>`_.
 watsonx_apikey = ""
 watsonx_token = ""

  # should follow the format: `https://{REGION}.ml.cloud.ibm.com`
 watsonx_url = ""
  

  # Deployment space id is required to create deployment with AI service content.
 space_id = "PLACEHOLDER_FOR_YOUR_SPACE_ID"

  # variable, that is populated with last created deployment_id every time when command `watsonx-ai service new` finish successfully
 deployment_id = ""
  
[deployment.online.parameters]
  # during creation of deployment additional parameters can be provided inside `ONLINE` object for further referencing
  # please refer to the API docs: https://cloud.ibm.com/apidocs/machine-learning-cp#deployments-create
 model_id = "meta-llama/llama-3-3-70b-instruct"  # underlying model of WatsonxChat
 embedding_model_id = "ibm/slate-125m-english-rtrvr-v2"
 knowledge_graph_description=""
 url = ""  # should follow the format: `https://{REGION}.ml.cloud.ibm.com`
  
  # Secret Manager configuration
  # Required:
 service_manager_service_url = "<YOUR_SECRETS_MANAGER_SERVICE_URL>"
 secret_id = "<YOUR_SECRET_ID>"

[deployment.software_specification]
  # Name for derived software specification. If not provided, default one is used that will be build based on the package name: "{pkg_name}-sw-spec"
 name = ""

  # Whether to overwrite (delete existing and create new with the same name) watsonx derived software specification
  # Default: false
 overwrite = false

  # The base software specification used to deploy the AI service. The template dependencies will be installed based on the packages included in the selected base software specification
  # Default: "runtime-24.1-py3.11"
 base_sw_spec = "runtime-24.1-py3.11"
```

### 3. Generate a virtual Python environment

```sh
cd code
source ./.venv/bin/activate
cd langgraph-graph-rag
poetry install
#Langfuse
#poetry add --no-cache langfuse==3.3.3
# Docling
#poetry add --no-cache docling
```

### 4. Start a new Neo4j container

Open the **first** terminal and execute the following bash file.

```sh
cd code/langgraph-graph-rag/scripts
bash run_new_neo4j_container.sh
```

### 5. Create a new Graph and Vector index (preprocessing)

Open the **second** terminal and execute the following bash file.

* Optional:

```sh
cd code/langgraph-graph-rag/scripts
bash run_convert_pdf_to_markdown.sh
```

* Graph generation:

```sh
cd code/langgraph-graph-rag/scripts
bash create_graph.sh
```

The bash execution will generate a log file in the output folder.

For example, `code/langgraph-graph-rag/scripts/output_data/log_preocessing_company_overview_output_2025-11-03_13-36-14.txt`, which you can examine.

### 6. Open the Neo4j in a browser and examine the graph

Open http://localhost:7474/ in your browser.

```sh
User: neo4j
Password: password
```

### 7. Prepare Langfuse for agent observation

Open the **third** terminal and execute the following bash file.
(for the detailed configuration, please visit the blog post)

```sh
cd code/local_monitoring
bash start_cangfuse.sh
```

### 8. Open Langfuse in the browser

* URL: http://localhost:3000
* Organization: graphrag
* Owner: graphrag
* Project name: graphrag


### 9. Run the agent in a local chat and ask test questions

Open the **fourth** terminal and execute the following bash file.

Test questions:
* "Hi! How are you?"
* "Which relation has the Galaxium Travels company?"
* "What does the vision mention?"
* "What does the mission statement mention?"

```sh
cd code/langgraph-graph-rag/scripts
bash create_graph.sh
```

Example interaction:

```sh
The following commands are supported:
 --> help | h : prints this help message
 --> quit | q : exits the prompt and ends the program
 --> list_questions : prints a list of available questions


Choose a question or ask one of your own.
 --> Which relation has the Galaxium Travels company?

 ============================== Assistant Message ===============================
The Galaxium Travels company has the following relations:

1. FOUNDED -> 2025 

This indicates that Galaxium Travels was founded in the year 2025.
```

### 10. Inspect the results

1. Now you can inspect in Langfuse the interaction of the agent.
2. During the interaction with the agent, the agent has generated a customized log file in the output folder. 

For example, `code/langgraph-graph-rag/scripts/output_data/log_preocessing_company_overview_output_2025-11-03_13-36-14.txt`, which you can examine.