"""Scripts for creating knowledge graph with vector representation from the provided text."""

import os

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
embedding_func = WatsonxEmbeddings(
    model_id=WATSONX_EMBEDDING_MODEL_ID,
    watsonx_client=api_client,
    params={"truncate_input_tokens": 512},
)


def prepare_documents(documents: list[Document], size) -> list[Document]:
    print(f"***Log: prepare the documents: ({len(documents)}) ({size})")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=256)
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
    filename="./input_data/company_overview.md"
    text=get_text(filename)
    documents = [Document(page_content=text)]
    size_min=256
    size_max=512
    print(f"***Log: 1. Document count: ({len(documents)} and size {size_max})\n\n")
    chunks = prepare_documents(documents,size_max)
    print(f"***Log: 2. Chunks count: ({len(chunks)})\n\n")
    i = 1
    for chunk in chunks:
        print(f"****Log: 2.{i} Chunk:\n***\n{chunk}\n***\n")
        i = i + 1

    # Experimental LLM graph transformer that generates graph documents
    print(f"***Log: 3. Start LLMGraphTransformer with llm: ({llm})\n\n")
    llm_transformer = LLMGraphTransformer(llm=llm)
    print(f"***Log: 4. Start convert to graph documents using the chunks: ({len(chunks)})\n\n")
    graph_documents = llm_transformer.convert_to_graph_documents(chunks)
    print(f"***Log: 5. Create the graph using the grapg documents: ({len(graph_documents)})\n\n")
    i = 1
    for graph_document in graph_documents:
        print(f"****Log: 5.{i} Graph document: \n***\n{graph_document}\n***\n")
        i = i + 1
    neo4j_graph = create_knowledge_graph(graph_documents=graph_documents)
    print(f"***Log: 6. Create the vector index from the graph\n\n")
    create_vector_index_from_graph(neo4j_graph)
