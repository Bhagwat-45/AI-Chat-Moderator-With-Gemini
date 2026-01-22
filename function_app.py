import json
import uuid
from datetime import datetime, timezone
import azure.functions as func

app = func.FunctionApp()

MESSAGES = []

@app.route(route="message",methods=["POST"])
def create_messages(req: func.HttpRequest)->func.HttpResponse:
    try:
        body = req.get_json()

    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid json body"}),
            status_code=400,
            mimetype='application/json'
        )
    
    content = body.get("content")
    username = body.get("username","anonymous")

    if not content or not isinstance(content,str):
        return func.HttpResponse(
            json.dumps({"error" : "The field content should be present "}),
            status_code=400,
            mimetype='application/json'
        )
    
    message = {
        "id" : str(uuid.uuid4()),
        "content" : content,
        "username" : username,
        "timestamp" : datetime.now(timezone.utc).isoformat()
    }

    MESSAGES.append(message)

    return func.HttpResponse(
        json.dumps(message),
        status_code=201,
        mimetype="application/json"
    )

@app.route(route="messages",methods=['GET'])
def get_messages(req: func.HttpRequest)->func.HttpResponse:
    return func.HttpResponse(
        json.dumps(MESSAGES),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="health",methods=["GET"])
def health_check(req: func.HttpRequest)->func.HttpResponse:
    return func.HttpResponse(
        "Healthy",
        status_code=200
    )