import asyncio
import websockets
import json
import httpx

async def test_repro():
    async with httpx.AsyncClient() as client:
        # 1. Create Game
        res = await client.post("http://localhost:5001/create", data={"name": "BonusBot", "difficulty": "easy"})
        if res.status_code != 303:
            print(f"Failed to create game: {res.status_code}")
            return
        loc = res.headers["location"]
        if "://" in loc: loc = loc.split("5001")[-1]
        
        parts = loc.split('?')
        code = parts[0].split('/')[-1]
        pid = parts[1].split('=')[-1]
        
        print(f"Game Created: {code} for Player {pid}")
        
        # 2. Connect WS
        uri = f"ws://localhost:5001/ws/game/{code}/{pid}"
        async with websockets.connect(uri) as ws:
            print("WS Connected")
            
            # 3. Start Game
            await ws.send(json.dumps({"type": "start_game"}))
            print("Sent start_game")
            
            # 4. Loop to find a word
            target_word = None
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    
                    if data.get("type") == "word_spawn" and data.get("target_pid") == pid:
                        word_obj = data["word"]
                        target_word = word_obj["text"]
                        print(f"Spawned Word: {target_word}")
                        
                        # 5. Submit Word
                        await ws.send(json.dumps({"type": "submit_word", "word": target_word}))
                        print(f"Submitted: {target_word}")
                        
                    elif data.get("type") == "word_cleared":
                        if data.get("player_id") == pid:
                            print("SUCCESS: Word Cleared confirmed!")
                            return
                            
                except asyncio.TimeoutError:
                    print("Timeout waiting for events")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break

if __name__ == "__main__":
    asyncio.run(test_repro())