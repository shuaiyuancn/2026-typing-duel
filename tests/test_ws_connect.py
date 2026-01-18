import pytest
import httpx
import websockets
import json

@pytest.mark.asyncio
async def test_ws_connection_e2e():
    # 1. Create Game
    async with httpx.AsyncClient() as client:
        # Note: We hit the container's localhost:5001 because this test runs INSIDE the container
        res = await client.post("http://localhost:5001/create", data={"name": "Test", "difficulty": "easy"})
        assert res.status_code == 303
        loc = res.headers["location"]
        
        # Parse location, handling potential absolute URLs if they ever appear, 
        # though usually it's relative path /lobby/...
        if "://" in loc:
            loc = loc.split("5001")[-1]

        parts = loc.split('?')
        path = parts[0]
        query = parts[1]
        code = path.split('/')[-1]
        pid = query.split('=')[-1]
        
        # 2. Connect WS
        uri = f"ws://localhost:5001/ws/game/{code}/{pid}"
        
        async with websockets.connect(uri) as ws:
            # Expect game state
            msg = await ws.recv()
            data = json.loads(msg)
            assert data["type"] == "game_state"
            assert data["game"]["code"] == code
            assert "players" in data["game"]