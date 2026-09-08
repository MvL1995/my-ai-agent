import json
import threading
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from web_app import build_request_handler


received_leads = []


def fake_save_lead(payload):
    if payload.get("email") == "invalid":
        raise ValueError("Invalid lead email.")
    received_leads.append(payload)
    return "lead-web-test"


handler = build_request_handler({}, save_lead=fake_save_lead)
server = HTTPServer(("127.0.0.1", 0), handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f"http://127.0.0.1:{server.server_port}"


def post(payload):
    request = Request(
        base_url + "/api/leads",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))
    with response:
        return response.status, json.loads(response.read().decode("utf-8"))


try:
    payload = {
        "name": "Test Client",
        "email": "client@example.com",
        "intent": "project",
        "message": "Landing page enquiry",
    }
    status, result = post(payload)
    assert status == 201
    assert result == {"ok": True, "lead_id": "lead-web-test", "status": "received"}
    assert received_leads == [payload]
    assert "email" not in result

    status, rejected = post({"email": "invalid"})
    assert status == 400
    assert rejected == {"error": "Invalid lead email."}
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

print("Lead-web-api tests passed.")
