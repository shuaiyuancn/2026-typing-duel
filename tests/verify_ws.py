import asyncio
import websockets
import json
import httpx

async def test():
    # 1. Create Game
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:5001/create", data={"name": "Test", "difficulty": "easy"})
        if res.status_code != 303:
            print(f"Failed to create game: {res.status_code}")
            return
        loc = res.headers["location"]
        print(f"Redirect to: {loc}")
        
        # Parse /lobby/CODE?pid=PID
        # If absolute URL returned, handle it, but usually relative in starlette unless specified.
        # It seems FastHTML/Starlette returns relative path usually.
        if "http" in loc:
            # Handle full url if needed, but for now assume logic
            pass
            
        parts = loc.split('?')
        path = parts[0]
        query = parts[1]
        code = path.split('/')[-1]
        pid = query.split('=')[-1]
        
        print(f"Code: {code}, PID: {pid}")

        # 2. Connect WS
        uri = f"ws://localhost:5001/ws/game/{code}/{pid}"
        print(f"Connecting to {uri}")
        
        try:
            async with websockets.connect(uri) as ws:
                # Expect game state
                msg = await ws.recv()
                print(f"Received: {msg}")
                data = json.loads(msg)
                if data["type"] == "game_state":
                    print("SUCCESS: Game State Received")
                else:
                    print("FAILURE: Unexpected message")
                    
        except Exception as e:
            print(f"WS Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
