import json
import os
import uuid
import logging
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import CosmosClient, exceptions

app = func.FunctionApp()

DATABASE_NAME = "streamingdb"
CONTAINER_NAME = "messages"


def get_container():
    """
    Returns Cosmos DB container if configured, else None.
    """
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    if not connection_string:
        return None

    try:
        client = CosmosClient.from_connection_string(connection_string)
        database = client.get_database_client(DATABASE_NAME)
        container = database.get_container_client(CONTAINER_NAME)
        return container
    except exceptions.CosmosHttpResponseError as e:
        logging.warning(f"Cosmos DB connection failed: {e}")
        return None


@app.route(route="message", methods=["POST"])
def create_message(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    content = body.get("content")
    username = body.get("username", "anonymous")

    if not content or not isinstance(content, str):
        return func.HttpResponse(
            json.dumps({"error": "Field 'content' is required and must be a string"}),
            status_code=400,
            mimetype="application/json"
        )

    message = {
        "id": str(uuid.uuid4()),  # required for Cosmos DB
        "content": content,
        "username": username,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    container = get_container()
    if not container:
        logging.warning("Cosmos DB not configured. Message not persisted.")
        return func.HttpResponse(
            json.dumps(message),
            status_code=201,
            mimetype="application/json"
        )

    try:
        container.create_item(body=message)
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Failed to write to Cosmos DB: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to store message"}),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps(message),
        status_code=201,
        mimetype="application/json"
    )


@app.route(route="messages", methods=["GET"])
def get_messages(req: func.HttpRequest) -> func.HttpResponse:
    container = get_container()
    if not container:
        logging.warning("Cosmos DB not configured. Returning empty message list.")
        return func.HttpResponse(
            json.dumps([]),
            status_code=200,
            mimetype="application/json"
        )

    messages = []
    try:
        for item in container.read_all_items():
            # Remove Cosmos metadata fields
            item.pop("_rid", None)
            item.pop("_self", None)
            item.pop("_etag", None)
            item.pop("_attachments", None)
            item.pop("_ts", None)
            messages.append(item)
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Failed to read from Cosmos DB: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to read messages"}),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps(messages),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        "Healthy",
        status_code=200
    )
