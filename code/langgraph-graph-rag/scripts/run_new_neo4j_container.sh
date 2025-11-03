echo "Stopping and removing existing Neo4j container..."
docker container stop neo4j
docker container rm neo4j

echo "Starting a new Neo4j container..."
docker run  -it --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4JLABS_PLUGINS='["apoc"]' \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_dbms_security_procedures_unrestricted='apoc.*' \
  neo4j:latest