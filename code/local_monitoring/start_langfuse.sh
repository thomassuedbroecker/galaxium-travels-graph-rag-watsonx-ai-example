#!/bin/bash

# **************** Global variables
export HOME_PATH=$(pwd)
cd ../langgraph-graph-rag
source .env
cd ${HOME_PATH}/

# **********************************************************************************
# Functions definition
# **********************************************************************************

function check_docker () {
    ERROR=$(docker ps 2>&1)
    RESULT=$(echo $ERROR | grep 'Cannot' | awk '{print $1;}')
    VERIFY="Cannot"
    if [ "$RESULT" == "$VERIFY" ]; then
        echo "Docker is not running. Stop script execution."
        exit 1 
    fi
}

#**********************************************************************************
# Execution
# *********************************************************************************

echo "************************************"
echo "Start containers with Docker compose " 
echo "- 'Langfuse"
echo "************************************"

echo "**************** START ******************" 
docker compose -f ./docker-compose.yml up # --detach
