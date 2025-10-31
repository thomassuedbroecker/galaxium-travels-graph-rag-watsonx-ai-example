echo "Creating knowledge graph with LangGraph Graph RAG ..."

echo "Loading environment variables and activating virtual environment ..."
source ../.env
source ../../.venv/bin/activate

echo "Running create_knowledge_graph.py ..."
poetry run python create_knowledge_graph.py