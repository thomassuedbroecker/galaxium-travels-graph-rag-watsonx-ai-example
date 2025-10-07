"""Scripts for creating knowledge graph with vector representation from the provided text."""

import os
import time

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate

from langchain_ibm import ChatWatsonx, WatsonxEmbeddings
from ibm_watsonx_ai import APIClient, Credentials

from dotenv import load_dotenv

enviornment_path="../.env"
load_dotenv(dotenv_path= enviornment_path)

# Model ids
WATSONX_MODEL_ID = os.environ.get("WATSONX_MODEL_ID")
WATSONX_EMBEDDING_MODEL_ID = os.environ.get("WATSONX_EMBEDDING_MODEL_ID")

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
size_big=1024
size=size_big
embedding_func = WatsonxEmbeddings(
    model_id=WATSONX_EMBEDDING_MODEL_ID,
    watsonx_client=api_client,
    params={"truncate_input_tokens": size},
)


def prepare_documents(documents: list[Document], size) -> list[Document]:
    print(f"***Log: prepare the documents: ({len(documents)}) ({size})")
    size_min=256
    size_max=512
    size_big=1024
    size=size_max
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=size)
    return text_splitter.split_documents(documents)

def get_text(filename):
    file = open(filename, "r")
    content = file.read()
    file.close()
    return content

def create_knowledge_graph(graph_documents: list[GraphDocument]) -> Neo4jGraph:
    # By default, url, username and password are read from env variables
    print(f"***Log: create_knowledge_graph:\nBy default, url, username and password are read from env variables")
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
    print(f"***Log: create the vector index")
    _ = Neo4jVector.from_existing_graph(
        embedding=embedding_func,
        search_type="hybrid",
        node_label="Document",
        embedding_node_property="embedding",
        text_node_properties=["text"],
        graph=graph,
    )


if __name__ == "__main__":
    # Example text
    filename_1="./input_data/company_overview.md.md"
    #filename_2="./input_data/X.md"
    #filename_3="./input_data/X.md"
    #filename_4="./input_data/X.md"
    filename_output="./input_data/company_overview.md.json"
    text_1=get_text(filename_1)
    #text_2=get_text(filename_2)
    #text_3=get_text(filename_3)
    #text_4=get_text(filename_4)
    metadata_1={"source": filename_1}
    #metadata_2={"source": filename_2}
    #metadata_3={"source": filename_3}
    #metadata_4={"source": filename_4}
    #documents = [Document(page_content=text_1, metadata=metadata_1), Document(page_content=text_2, metadata=metadata_2),  Document(page_content=text_3,  metadata=metadata_3), Document(page_content=text_4,  metadata=metadata_4)]
    documents = [Document(page_content=text_1, metadata=metadata_1)]
    size_min=256
    size_max=512
    size_big=1024
    size=size_max
    print(f"***Log: 1. Documents count: ({len(documents)} and size {size})\n\n")
    chunks = prepare_documents(documents,size)
    print(f"***Log: 2. Chunks count: ({len(chunks)})\n\n")
    i = 1
    for chunk in chunks:
        print(f"****Log: 2.{i} Chunk:\n***\n{chunk}\n***\n")
        i = i + 1

    # Experimental LLM graph transformer that generates graph documents
    # Documentation: https://api.python.langchain.com/en/latest/graph_transformers/langchain_experimental.graph_transformers.llm.LLMGraphTransformer.html
    print(f"***Log: 3. Start LLMGraphTransformer with `llm`: ({llm})\n\n")
    allowed_nodes = ["Company", "Person", "Objective"]
    print(f"***Log: - allowed nodes: {allowed_nodes}")
    allowed_relationships = ["RELATED_TO", "ASSOCIATED_WITH", "PART_OF", "MENTIONS", "CHANGES"]
    print(f"***Log: - allowed nodes: {allowed_relationships}")
    prompt = ChatPromptTemplate([("system", "You are an business expert for 'Company Profiles'. You can understand the impact and dependencies of the information, impacting requirments, to identify nodes and relations.")])
    print(f"***Log: - prompt: {prompt}")


    llm_transformer = LLMGraphTransformer(llm=llm, 
                                          allowed_nodes=allowed_nodes,  
                                          allowed_relationships=allowed_relationships, 
                                          #strict_mode=True,
                                          prompt=prompt)
    
    start = time.time()
    print(f"***Log: 4. Start convert to graph documents using the chunks: ({len(chunks)})\n\n")
    graph_documents = llm_transformer.convert_to_graph_documents(len(chunks))
    
    end = time.time()
    length = end - start
    print(f"***Log: - time to convert in sec: {length} ")   
    print(f"***Log: 5. Create the graph using the grapg documents: ({len(graph_documents)})\n\n")
    i = 1

    # Save re
    file = open(filename_output,'w')   
    file.write(f"model: {llm}\n")
    file.write(f"conversion_time in sec: {length}\n")
    file.write(f"conversion_time in minutes: {length/60}\n")
    file.write(f"graph_documents: {len(graph_documents)}\n")
    file.write(f"chunk size: {size}\n")
    file.write(f"chunks: {len(chunks)}\n")

    for graph_document in graph_documents:
        print(f"****Log: 5.{i} Graph document: \n***\n{graph_document}\n***\n")
        i = i + 1
        file.write(f"{graph_document}\n")
    file.close()
    neo4j_graph = create_knowledge_graph(graph_documents=graph_documents)
    print(f"***Log: 6. graph result:\n{neo4j_graph}\n")
    print(f"***Log: 7. Create the vector index from the graph embedding model:{WATSONX_EMBEDDING_MODEL_ID}\n\n")
    create_vector_index_from_graph(neo4j_graph)
