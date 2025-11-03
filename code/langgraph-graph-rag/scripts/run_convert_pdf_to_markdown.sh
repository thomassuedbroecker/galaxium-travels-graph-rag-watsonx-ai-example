echo "Convert PDF to markdown ..."

echo "Loading environment variables and activating virtual environment ..."
source ../.env
source ../../.venv/bin/activate

echo "Running generate markdown ..."
poetry run convert_pdf_to_markdown.py