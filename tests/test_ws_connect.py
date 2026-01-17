from starlette.testclient import TestClient
from main import app
import json

def test_ws_connection():
    client = TestClient(app)
    
    # 1. Create Game to get valid code
    res = client.post("/create", data={"name": "Test", "difficulty": "easy"})
    assert res.status_code == 303
    loc = res.headers["location"]
    # /lobby/CODE?pid=PID
    code = loc.split('/')[2].split('?')[0]
    pid = loc.split('=')[1]
    
    # 2. Connect WS
    with client.websocket_connect(f"/ws/game/{code}/{pid}") as websocket:
        # Expect game state
        data = websocket.receive_json()
        assert data["type"] == "game_state"
        assert "game" in data
        assert data["game"]["code"] == code
        
        # Send text (echo check)
        websocket.send_text("Hello")
        # Depending on how fast Redis reader is, we might get other messages, but echo should come.
        # But wait, my echo logic is in the same loop.
        # Receive text
        data = websocket.receive_text()
        assert "Server received: Hello" in data
