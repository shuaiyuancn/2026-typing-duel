import asyncio
import websockets
import json
import httpx
import re

async def test_practice_insane():
    async with httpx.AsyncClient() as client:
        # 1. Create PRACTICE Game with Insane Difficulty
        # Note the endpoint is /practice
        res = await client.post("http://localhost:5001/practice", data={"name": "SoloInsane", "difficulty": "insane"})
        if res.status_code != 303:
            print(f"Failed to create game: {res.status_code}")
            return
        loc = res.headers["location"]
        if "://" in loc: loc = loc.split("5001")[-1]
        
        parts = loc.split('?')
        code = parts[0].split('/')[-1]
        pid = parts[1].split('=')[-1]
        
        print(f"Insane Practice Game Created: {code} for Player {pid}")
        
        # 2. Connect WS
        uri = f"ws://localhost:5001/ws/game/{code}/{pid}"
        async with websockets.connect(uri) as ws:
            print("WS Connected")
            
            # 3. Start Game (For practice, it might need explicit start or auto-start?)
            # Lobby logic: "if count >= 2 or msg.game.mode === 'practice' ... Ready to start."
            # So we still need to send start_game
            await ws.send(json.dumps({"type": "start_game"}))
            print("Sent start_game")
            
            # 4. Loop to find a word
            SYMBOLS = "!@#$%^&*?"
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    
                    if data.get("type") == "word_spawn" and data.get("target_pid") == pid:
                        word_obj = data["word"]
                        target_word = word_obj["text"]
                        print(f"Spawned Word: {target_word}")
                        
                        # Verify it has a symbol
                        has_symbol = any(s in target_word for s in SYMBOLS)
                        if has_symbol:
                            print(f"SUCCESS: Word '{target_word}' contains a symbol!")
                        else:
                            print(f"FAILURE: Word '{target_word}' does NOT contain a symbol (Should be insane mode).")
                            return

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
    asyncio.run(test_practice_insane())
