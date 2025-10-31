echo "Running local chat with LangGraph Graph RAG ..."

echo "Loading environment variables and activating virtual environment ..."
source ../.env
source ../../.venv/bin/activate

echo "Setting up paths ..."
export BASH_HOME=$(pwd)
cd ..
export FILENAME_AGENT_LOG_OUTPUT="$(pwd)/scripts/output_data"
cd $BASH_HOME

echo "Executing local chat with LangGraph Graph RAG ..."
cd ..
poetry run python scripts/execute_ai_service_locally.py