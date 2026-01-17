import pytest
from httpx import AsyncClient, ASGITransport
from main import app, gm
import json
import asyncio
import time

# Use the app for testing
transport = ASGITransport(app=app)

@pytest.mark.asyncio
async def test_game_flow():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create Game
        response = await ac.post("/create", data={
            "name": "Host",
            "difficulty": "easy",
            "powers": ["shake", "blindness"]
        })
        assert response.status_code == 303
        redirect_url = response.headers["location"]
        path, query = redirect_url.split('?')
        code = path.split('/')[-1]
        host_pid = query.split('=')[-1]
        
        # 2. Join Game
        response = await ac.post("/join", data={
            "name": "Joiner",
            "code": code
        })
        assert response.status_code == 303
        joiner_pid = response.headers["location"].split('=')[-1]

        # 3. Simulate Start Game
        await gm.set_game_status(code, "playing")
        
        # 4. Test Gameplay Logic (Submit Word)
        # Manually seed a word for Host
        word_id = "test_word_1"
        word_data = {
            "text": "TEST",
            "id": word_id,
            "x": 0,
            "spawn_time": time.time(),
            "duration": 10
        }
        await gm.redis.hset(f"game:{code}:{host_pid}:words", word_id, json.dumps(word_data))
        
        # Submit correct word
        result = await gm.submit_word(code, host_pid, "TEST")
        assert result == True
        
        # Verify word removed
        exists = await gm.redis.hexists(f"game:{code}:{host_pid}:words", word_id)
        assert not exists
        
        # Verify Score
        state = await gm.get_game_state(code)
        players = state["players"]
        assert players[host_pid]["words_cleared"] == 1
        assert players[host_pid]["power"] == 10
        
        # 5. Test Power Up Trigger
        # Set power to 90
        players[host_pid]["power"] = 90
        await gm.redis.hset(f"game:{code}", "players", json.dumps(players))
        
        # Seed another word
        word_id_2 = "power_word"
        word_data_2 = {"text": "POWER", "id": word_id_2, "x": 0, "spawn_time": time.time(), "duration": 10}
        await gm.redis.hset(f"game:{code}:{host_pid}:words", word_id_2, json.dumps(word_data_2))
        
        # Submit to trigger power
        await gm.submit_word(code, host_pid, "POWER")
        
        # Verify Power Reset (means trigger happened)
        state = await gm.get_game_state(code)
        assert state["players"][host_pid]["power"] == 0
        
        # Clean up
        await gm.redis.delete(f"game:{code}")
