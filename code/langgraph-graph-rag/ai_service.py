def deployable_ai_service(
    context,
    url,
    model_id,
    embedding_model_id,
    knowledge_graph_description,
    service_manager_service_url,
    secret_id
):
    import urllib
    from typing import Generator

    from langgraph_graph_rag.agent import get_graph_closure
    from ibm_watsonx_ai import APIClient, Credentials
    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        AIMessage,
        SystemMessage,
    )

    #########################################
    # Langfuse only for local!
    # doesn't work in the deployment
    #########################################

    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
    from dotenv import load_dotenv
    enviornment_path="./.env"
    load_dotenv(dotenv_path= enviornment_path)
    import os

    # 1. Load configuration
    LANGFUSE_PUBLIC_KEY= os.getenv('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY= os.getenv('LANGFUSE_SECRET_KEY')
    LANGFUSE_HOST= os.getenv('LANGFUSE_HOST')
    langfuse = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST
    )
    # 2. Verify connection
    from langfuse import get_client
    langfuse = get_client()
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")

    langfuse_handler = CallbackHandler()
    
    #########################################

    hostname = urllib.parse.urlparse(url).hostname or ""
    is_cloud_url = hostname.lower().endswith("cloud.ibm.com")
    instance_id = None if is_cloud_url else "openshift"

    client = APIClient(
        credentials=Credentials(
            url=url,
            token=context.generate_token(),
            instance_id=instance_id,
        ),
        space_id=context.get_space_id(),
    )

    graph = get_graph_closure(
        client,
        model_id,
        embedding_model_id,
        knowledge_graph_description=knowledge_graph_description,
        service_manager_service_url=service_manager_service_url,
        secret_id=secret_id,
    )

    def get_formatted_message(
        resp: BaseMessage, is_assistant: bool = False
    ) -> dict | None:
        role = resp.type

        if resp.content:
            if role in {"AIMessageChunk", "ai"}:
                return {"role": "assistant", "content": resp.content}
            elif role == "tool":
                if is_assistant:
                    return {
                        "role": "assistant",
                        "step_details": {
                            "type": "tool_response",
                            "id": resp.id,
                            "tool_call_id": resp.tool_call_id,
                            "name": resp.name,
                            "content": resp.content,
                        },
                    }
                else:
                    return {
                        "role": role,
                        "id": resp.id,
                        "tool_call_id": resp.tool_call_id,
                        "name": resp.name,
                        "content": resp.content,
                    }
        elif role == "ai":  # this implies resp.additional_kwargs
            if additional_kw := resp.additional_kwargs:
                tool_call = additional_kw["tool_calls"][0]
                if is_assistant:
                    return {
                        "role": "assistant",
                        "step_details": {
                            "type": "tool_calls",
                            "tool_calls": [
                                {
                                    "id": tool_call["id"],
                                    "name": tool_call["function"]["name"],
                                    "args": tool_call["function"]["arguments"],
                                }
                            ],
                        },
                    }
                else:
                    return {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_call["function"]["name"],
                                    "arguments": tool_call["function"]["arguments"],
                                },
                            }
                        ],
                    }

    def convert_dict_to_message(_dict: dict) -> BaseMessage:
        """Convert user message in dict to langchain_core.messages.BaseMessage"""

        if _dict["role"] == "assistant":
            return AIMessage(content=_dict["content"])
        elif _dict["role"] == "system":
            return SystemMessage(content=_dict["content"])
        else:
            return HumanMessage(content=_dict["content"])

    def generate(context) -> dict:
        """
        The `generate` function handles the REST call to the inference endpoint
        POST /ml/v4/deployments/{id_or_name}/ai_service

        The generate function should return a dict

        A JSON body sent to the above endpoint should follow the format:
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that uses tools to answer questions in detail.",
                },
                {
                    "role": "user",
                    "content": "Hello!",
                },
            ]
        }
        Please note that the `system message` MUST be placed first in the list of messages!
        """

        client.set_token(context.get_token())

        payload = context.get_json()
        raw_messages = payload.get("messages", [])
        messages = [convert_dict_to_message(_dict) for _dict in raw_messages]

        if messages and messages[0].type == "system":
            agent = graph(messages[0])
            del messages[0]
        else:
            agent = graph()

        # Invoke agent
        # generated_response = agent.invoke({"messages": messages})

        ################ Langfuse ##############
        generated_response = agent.invoke({"messages": messages}, config={"callbacks": [langfuse_handler]})
        ####################################

        choices = []
        execute_response = {
            "headers": {"Content-Type": "application/json"},
            "body": {"choices": choices},
        }

        choices.append(
            {
                "index": 0,
                "message": get_formatted_message(generated_response["messages"][-1]),
            }
        )

        return execute_response

    def generate_stream(context) -> Generator[dict, ..., ...]:
        """
        The `generate_stream` function handles the REST call to the Server-Sent Events (SSE) inference endpoint
        POST /ml/v4/deployments/{id_or_name}/ai_service_stream

        The generate function should return a dict

        A JSON body sent to the above endpoint should follow the format:
        {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that uses tools to answer questions in detail.",
                },
                {
                    "role": "user",
                    "content": "Hello!",
                },
            ]
        }
        Please note that the `system message` MUST be placed first in the list of messages!
        """
        headers = context.get_headers()
        is_assistant = headers.get("X-Ai-Interface") == "assistant"

        client.set_token(context.get_token())

        payload = context.get_json()
        raw_messages = payload.get("messages", [])
        messages = [convert_dict_to_message(_dict) for _dict in raw_messages]

        if messages and messages[0].type == "system":
            agent = graph(messages[0])
            del messages[0]
        else:
            agent = graph()

        response_stream = agent.stream(
            {"messages": messages}, stream_mode=["updates", "messages"]
        )

        for chunk_type, data in response_stream:
            if chunk_type == "messages":
                msg_obj = data[0]
            elif chunk_type == "updates":
                if agent := data.get("agent"):
                    messages = agent.get("messages")
                    if messages is not None:
                        msg_obj = messages[0]
                    else:
                        continue
                    if msg_obj.response_metadata.get("finish_reason") == "stop":
                        continue
                elif tool := data.get("tools"):
                    msg_obj = tool["messages"][0]
                else:
                    continue
            else:
                continue

            if (
                message := get_formatted_message(msg_obj, is_assistant=is_assistant)
            ) is not None:
                chunk_response = {
                    "choices": [
                        {
                            "index": 0,
                            "delta": message,
                            "finish_reason": msg_obj.response_metadata.get(
                                "finish_reason"
                            ),
                        }
                    ]
                }
                yield chunk_response

    return generate, generate_stream
