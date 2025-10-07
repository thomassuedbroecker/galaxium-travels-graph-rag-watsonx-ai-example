from docling.document_converter import DocumentConverter

source = "./input_data/company_overview.md.pdf"  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(f"Convert PDF {source} to Markdown")  # output: DocumentConversionResult(document=Document(...), metadata=DocumentMetadata(...))
print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"

destination = "./input_data/Acompany_overview.md.md"
with open(destination, 'w', encoding='utf-8') as f:
    f.write(result.document.export_to_markdown())

print(f"Markdown file saved to {destination}")
