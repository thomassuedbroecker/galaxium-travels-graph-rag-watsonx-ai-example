"""Scripts for creating knowledge graph with vector representation from the provided text."""

import os
import time
from datetime import datetime

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph, Neo4jVector
from neo4j import GraphDatabase
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate

from langchain_ibm import ChatWatsonx, WatsonxEmbeddings
from ibm_watsonx_ai import APIClient, Credentials

from dotenv import load_dotenv

###############################################
# Variables and model definitions

enviornment_path="../.env"
load_dotenv(dotenv_path= enviornment_path)

# Model ids
WATSONX_MODEL_ID = os.environ.get("WATSONX_MODEL_ID")
WATSONX_EMBEDDING_MODEL_ID = os.environ.get("WATSONX_EMBEDDING_MODEL_ID")

# Graph transformer options
USE_PROMPT=os.environ.get("USE_PROMPT")
USE_ADDITIONAL_INSTRUCTIONS=os.environ.get("USE_ADDITIONAL_INSTRUCTIONS")
USE_NODES_RELATION_DEFINITIONS=os.environ.get("USE_NODES_RELATION_DEFINITIONS")

# Define APIClient using env variables
print(f"***Log: Define APIClient using env variables")
api_client = APIClient(
    credentials=Credentials(
        url=os.environ.get("WATSONX_URL"),
        api_key=os.environ.get("WATSONX_APIKEY"),
        token=os.environ.get("WATSONX_TOKEN"),
    ),
    space_id=os.environ.get("WATSONX_SPACE_ID"),
    project_id=os.environ.get("WATSONX_PROJECT_ID"),
)


# Define llm and embedding models
print(f"***Log: define llm and embedding models")
llm = ChatWatsonx(model_id=WATSONX_MODEL_ID, watsonx_client=api_client, temperature=0)
size_min=256
size_max=512
size_big=768
#size_big=1024
#size_big=1200
size=size_big
embedding_func = WatsonxEmbeddings(
    model_id=WATSONX_EMBEDDING_MODEL_ID,
    watsonx_client=api_client,
    params={"truncate_input_tokens": size},
)

###############################################
# Functions

def prepare_documents(documents: list["Document"], in_size: int, overlap: int) -> list["Document"]:
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= in_size:
        raise ValueError("overlap must be smaller than chunk size")

    print(f"***Log: prepare the documents: ({len(documents)}) (size={in_size}, overlap={overlap})")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=in_size,
        chunk_overlap=overlap,
    )
    return text_splitter.split_documents(documents)

def get_text(filename):
    file = open(filename, "r")
    content = file.read()
    file.close()
    return content

def create_knowledge_graph(graph_documents: list[GraphDocument]) -> Neo4jGraph:
    # By default, url, username and password are read from env variables
    print(f"***Log: clear the existing graph data")
    #graph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
    #graph.query("DROP GRAPH")
    #graph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
    (f"***Log: create_knowledge_graph:\nBy default, url, username and password are read from env variables")
    graph = Neo4jGraph(refresh_schema=False)
    graph.add_graph_documents(
        graph_documents=graph_documents, baseEntityLabel=True, include_source=True
    )

    #  Create full text index for graph traversal
    graph.query(
        "CREATE FULLTEXT INDEX entity IF NOT EXISTS FOR (e:__Entity__) ON EACH [e.id]"
    )
    return graph


def create_vector_index_from_graph(graph: Neo4jGraph) -> None:
    # make sure the database is empty    
    print(f"***Log: create the vector index")
    _ = Neo4jVector.from_existing_graph(
        embedding=embedding_func,
        search_type="hybrid",
        node_label="Document",
        embedding_node_property="embedding",
        text_node_properties=["text"],
        graph=graph,
    )

def get_timestamp():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    return timestamp

def get_all_relationship_types(graph: GraphDatabase.driver) -> list[str]:
    """
    Retrieves a list of all relationship types in the database.
    """
    with graph.session() as session:
        # The Cypher query calls the built-in stored procedure
        result = session.execute_read(
            lambda tx: tx.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").data()
        )
        # Extract the relationship names into a Python list
        relationship_types = [record['relationshipType'] for record in result]
        return relationship_types

def graph_conf():
    return {
        "NEO4J_URI" : os.getenv('NEO4J_URI'),
        "NEO4J_USERNAME" : os.getenv('NEO4J_USERNAME'),
        "NEO4J_PASSWORD" : os.getenv('NEO4J_PASSWORD'),
        "NEO4J_DATABASE" : os.getenv('NEO4J_DATABASE')
    }

def connect_to_neo4j_graph() -> GraphDatabase.driver:
    """
    Connects to the Neo4j graph database using environment variables.
    """
    URI = graph_conf()['NEO4J_URI'] 
    AUTH = (graph_conf()['NEO4J_USERNAME'], graph_conf()['NEO4J_PASSWORD'])
    graph = GraphDatabase.driver(URI, auth=AUTH)
    # Verify connectivity (optional)
    graph.verify_connectivity()
    print("Connection established successfully.")
   
    return graph

def get_all_node_labels(graph: GraphDatabase.driver) -> list[str]:
    """
    Retrieves a list of all node labels in the database.
    """
    with graph.session() as session:
        # The Cypher query calls the built-in stored procedure
        result = session.execute_read(
            lambda tx: tx.run("CALL db.labels() YIELD label RETURN label").data()
        )
        # Extract the label names into a Python list
        node_labels = [record['label'] for record in result]
    return node_labels

###############################################
# Main script execution

if __name__ == "__main__":

    timestamp =get_timestamp()
    
    # Example text
    filename_1="./input_data/company_overview.md"

    # Example output file
    filename_output=f"./output_data/log_prepocessing_company_overview_output_{timestamp}.txt"
    text_1=get_text(filename_1)

    # Example prompt
    prompt_text=get_text("./prompts_and_additional_instructions/company_profile_prompt.md")

    # Example additional_instructions
    additional_instructions_text=get_text("./prompts_and_additional_instructions/company_profile_additional_instructions.md")

    # Example metadata for the graph documents
    metadata_1={"source": filename_1}
    documents = [Document(page_content=text_1, metadata=metadata_1)]
    chunk_size=512
    #chunk_size=768
    overlap=int( chunk_size/10)
    print(f"***Log: 1. Documents count: ({len(documents)} and size { chunk_size}, overlap {overlap})\n\n")
    chunks = prepare_documents(documents, chunk_size,overlap)
    print(f"***Log: 2. Chunks count: ({len(chunks)})\n\n")
    i = 1
    for chunk in chunks:
        print(f"****Log: 2.{i} Chunk:\n***\n{chunk}\n***\n")
        i = i + 1
    
    # Create a LLMGraphTransformer instance
    # Experimental LLM graph transformer that generates graph documents
    # Documentation: https://api.python.langchain.com/en/latest/graph_transformers/langchain_experimental.graph_transformers.llm.LLMGraphTransformer.html
    
    # Not using prompt template for now
    system_prompt = prompt_text
    chat_prompt = ChatPromptTemplate([("system", system_prompt)])
    print(f"***Log: - prompt:\n{chat_prompt}\n\n")

    # Using the additional_instructions parameter instead of prompt template for now
    additional_instructions = additional_instructions_text

    print(f"***Log: 3. Create LLMGraphTransformer with `llm`: ({llm})\n\n")
    allowed_nodes = ["Company", "Person", "Objective"]
    print(f"***Log: - allowed nodes: {allowed_nodes}")
    allowed_relationships = ["RELATED_TO", "ASSOCIATED_WITH", "PART_OF", "MENTIONS", "CHANGES"]
    print(f"***Log: - allowed relationships: {allowed_relationships}")

    # Prompt and additional instructions handling
    if USE_PROMPT.lower() == 'true':
        print(f"***Log: - using prompt template for graph transformer")
        print(f"***Log: - using additional instructions for graph transformer")
        if USE_NODES_RELATION_DEFINITIONS.lower() == 'true':    
            print(f"***Log: - using nodes and relationship definitions for graph transformer")
            additional_instructions = additional_instructions + f"\n\n Define the following nodes: {allowed_nodes} \n\n Define the following relationships: {allowed_relationships}"
            llm_transformer = LLMGraphTransformer(llm=llm, 
                                          strict_mode=False,
                                          prompt=chat_prompt,
                                          additional_instructions=additional_instructions,
                                          )
        else:
            llm_transformer = LLMGraphTransformer(llm=llm, 
                                            strict_mode=False,
                                            prompt=chat_prompt,
                                            )
    elif USE_ADDITIONAL_INSTRUCTIONS.lower() == 'true':
        print(f"***Log: - using additional instructions for graph transformer")
        if USE_NODES_RELATION_DEFINITIONS.lower() == 'true':
            print(f"***Log: - using nodes and relationship definitions for graph transformer")
            additional_instructions = additional_instructions + f"\n\n Define the following nodes: {allowed_nodes} \n\n Define the following relationships: {allowed_relationships}"
            llm_transformer = LLMGraphTransformer(llm=llm, 
                                            allowed_nodes=allowed_nodes,  
                                            allowed_relationships=allowed_relationships, 
                                            strict_mode=False,
                                            additional_instructions=additional_instructions,
                                            )
        else:
            llm_transformer = LLMGraphTransformer(llm=llm, 
                                            strict_mode=False,
                                            additional_instructions=additional_instructions,
                                            )
    else:
        print(f"***Log: - no prompt or additional instructions for graph transformer")
        llm_transformer = LLMGraphTransformer(llm=llm, 
                                          allowed_nodes=allowed_nodes,  
                                          allowed_relationships=allowed_relationships, 
                                          strict_mode=False,
                                          )
    

    
    start = time.time()
    print(f"***Log: 4. Start convert to graph documents using the chunks: ({len(chunks)})\n\n")
    graph_documents = llm_transformer.convert_to_graph_documents(chunks)
    
    end = time.time()
    length = end - start
    print(f"***Log: - time to convert in sec: {length} ")   
    print(f"***Log: 5. Create the graph using the grapg documents: ({len(graph_documents)})\n\n")
    i = 1

    # Save report
    file = open(filename_output,'w') 
    file.write(f"******** {timestamp} **********\n")
    
    file.write(f"************ Models *******************\n")
    file.write(f"llm model id (preprocessing and runtime agent execution): {WATSONX_MODEL_ID}\n")
    file.write(f"embedding model id: {WATSONX_EMBEDDING_MODEL_ID}\n")
    
    file.write(f"************ Chat configuratoin ********\n")
    file.write(f"llm chat configuration: {llm}\n")
    
    file.write(f"\n************ Time preprocessing *******************\n")
    file.write(f"conversion_time in sec: {length}\n")
    file.write(f"conversion_time in minutes: {length/60}\n")
    
    file.write(f"\n************ Ontology definition *****\n")
    file.write(f"transformer configuration:\n")
    file.write(f"- use_prompt (preprocessing): {USE_PROMPT}\n\n")
    if (USE_PROMPT.lower() == 'true'):
        file.write(f"   - system_prompt:\n{system_prompt}\n\n")
    file.write(f"- use_additional_instructions (preprocessing): {USE_ADDITIONAL_INSTRUCTIONS}\n\n")
    if (USE_ADDITIONAL_INSTRUCTIONS.lower() == 'true' or USE_PROMPT.lower() == 'true'):
        file.write(f"   - additional instructions:\n{additional_instructions}\n\n")
    file.write(f"- use_nodes_relation_definitions: {USE_NODES_RELATION_DEFINITIONS}\n\n")
    if (USE_NODES_RELATION_DEFINITIONS.lower() == 'true'):
        file.write(f" - allowed_nodes:\n{allowed_nodes}\n\n")
        file.write(f" - allowed_relationships:\n{allowed_relationships}\n\n")
    
    file.write(f"\n************ Generated Graph Data overview***********\n")
    file.write(f"generated_graph_documents_count: {len(graph_documents)}\n")
    file.write(f"| chunk size | chunks | chunk overlap |\n")
    file.write(f"| --- | --- | --- |\n")
    file.write(f"| {chunk_size} | {overlap}| {len(chunks)} |\n\n")
    graph = connect_to_neo4j_graph()
    
    file.write(f"\n*********** List of generated node lables\n")
    file.write(f"{get_all_node_labels(graph)}\n\n")
    
    file.write(f"\n*********** List of generated relationship types\n")
    file.write(f"{get_all_relationship_types(graph)}\n\n")
    
    file.write(f"\n************ Generated Graph Data Entries***********\n")

    for graph_document in graph_documents:
        print(f"****Log: 5.{i} Graph document: \n***\n{graph_document}\n***\n")
        i = i + 1
        file.write(f"{graph_document}\n")
    file.close()
    neo4j_graph = create_knowledge_graph(graph_documents=graph_documents)
    print(f"***Log: 6. graph result:\n{neo4j_graph}\n")
    print(f"***Log: 7. Create the vector index from the graph embedding model:{WATSONX_EMBEDDING_MODEL_ID}\n\n")
    create_vector_index_from_graph(neo4j_graph)
