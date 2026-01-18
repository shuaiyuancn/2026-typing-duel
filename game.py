import json
import asyncio
import random
import string
import time
import os
from redis.asyncio import Redis
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional

@dataclass
class Player:
    name: str
    id: str
    health: int = 100
    power: int = 0
    words_cleared: int = 0
    combo: int = 0
    is_ready: bool = False

@dataclass
class GameConfig:
    difficulty: str
    allowed_powers: List[str]

class GameManager:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.easy_words = self._load_words("data/easy_words.txt")
        self.hard_words = self._load_words("data/hard_words.txt")
        self.default_words = ["HELLO", "WORLD", "TYPING", "DUEL", "FAST", "HTML", "CODE", "PYTHON", "REDIS", "THREEJS"]

    def _load_words(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return [line.strip().upper() for line in f if line.strip()]
        return []

    async def create_game(self, host_name: str, difficulty: str, powers: List[str]) -> tuple[str, str]:
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if not await self.redis.exists(f"game:{code}"):
                break
        
        host_id = self._generate_id()
        host_player = Player(name=host_name, id=host_id, is_ready=True)
        
        game_data = {
            "code": code,
            "host_id": host_id,
            "difficulty": difficulty,
            "status": "lobby",
            "powers": json.dumps(powers),
            "players": json.dumps({host_id: asdict(host_player)})
        }
        
        await self.redis.hset(f"game:{code}", mapping=game_data)
        await self.redis.expire(f"game:{code}", 3600)
        
        return code, host_id

    async def create_practice_game(self, host_name: str) -> tuple[str, str]:
        code, host_id = await self.create_game(host_name, "easy", ["clear_screen"])
        await self.redis.hset(f"game:{code}", "mode", "practice")
        return code, host_id

    async def join_game(self, code: str, player_name: str) -> Optional[str]:
        game_key = f"game:{code}"
        if not await self.redis.exists(game_key):
            return None
            
        status = await self.redis.hget(game_key, "status")
        if status != "lobby":
            return None 
            
        players_json = await self.redis.hget(game_key, "players")
        players = json.loads(players_json) if players_json else {}
        
        if len(players) >= 2:
            return None 
            
        player_id = self._generate_id()
        new_player = Player(name=player_name, id=player_id, is_ready=True)
        
        players[player_id] = asdict(new_player)
        await self.redis.hset(game_key, "players", json.dumps(players))
        
        await self.redis.publish(f"game:{code}:events", json.dumps({"type": "player_joined", "player": asdict(new_player)}))
        
        return player_id

    async def get_game_state(self, code: str) -> Optional[Dict]:
        game_key = f"game:{code}"
        if not await self.redis.exists(game_key):
            return None
        
        data = await self.redis.hgetall(game_key)
        if "players" in data:
            data["players"] = json.loads(data["players"])
        if "powers" in data:
            data["powers"] = json.loads(data["powers"])
        return data

    async def set_game_status(self, code: str, status: str):
        mapping = {"status": status}
        if status == "playing":
            mapping["start_time"] = time.time()
            
        await self.redis.hset(f"game:{code}", mapping=mapping)
        await self.redis.publish(f"game:{code}:events", json.dumps({"type": "status_change", "status": status}))

    async def _spawn_word(self, code, pid, word_text, x=None, duration=10.0):
        if x is None:
            x = random.uniform(-4, 4)
        word_id = self._generate_id()
        word_data = {
            "text": word_text,
            "id": word_id,
            "x": x,
            "spawn_time": time.time(),
            "duration": duration
        }
        await self.redis.hset(f"game:{code}:{pid}:words", word_id, json.dumps(word_data))
        await self.redis.publish(f"game:{code}:events", json.dumps({
            "type": "word_spawn",
            "target_pid": pid,
            "word": word_data
        }))

    async def start_game_loop(self, code: str):
        try:
            while True:
                # Fetch full game state for start_time
                game = await self.redis.hgetall(f"game:{code}")
                if game.get("status") != "playing":
                    break
                
                status = game["status"]
                
                # Determine word list based on difficulty
                difficulty = game.get("difficulty", "easy")
                if difficulty == "hard":
                    words_pool = self.hard_words or self.default_words
                else:
                    words_pool = self.easy_words or self.default_words

                players_json = game.get("players")
                players = json.loads(players_json) if players_json else {}
                
                now = time.time()
                start_time = float(game.get("start_time", now))
                elapsed = now - start_time
                
                for pid, p_data in players.items():
                    if p_data["health"] <= 0:
                        continue 
                    
                    # 1. Spawn Word
                    # Speed Scaling: 10s -> 3s over 3 mins (180s)
                    duration = max(3.0, 10.0 - (elapsed / 18.0 * 7.0)) 
                    
                    await self._spawn_word(code, pid, random.choice(words_pool), duration=duration)
                    
                    # 2. Check Expiration
                    active_words = await self.redis.hgetall(f"game:{code}:{pid}:words")
                    for wid, w_json in active_words.items():
                        w = json.loads(w_json)
                        if now > w["spawn_time"] + w["duration"]:
                            await self.damage_player(code, pid, 10)
                            await self.redis.hdel(f"game:{code}:{pid}:words", wid)
                            
                            await self.redis.publish(f"game:{code}:events", json.dumps({
                                "type": "word_expired",
                                "target_pid": pid,
                                "word_id": wid
                            }))

                await asyncio.sleep(2) 
        except Exception as e:
            print(f"Game Loop Error: {e}")

    async def submit_word(self, code: str, pid: str, word_text: str):
        active_words = await self.redis.hgetall(f"game:{code}:{pid}:words")
        for wid, w_json in active_words.items():
            w = json.loads(w_json)
            if w["text"] == word_text:
                await self.redis.hdel(f"game:{code}:{pid}:words", wid)
                
                players_json = await self.redis.hget(f"game:{code}", "players")
                players = json.loads(players_json)
                
                if pid in players:
                    players[pid]["combo"] += 1
                    multiplier = 1 + (players[pid]["combo"] // 5) * 0.5
                    
                    players[pid]["power"] += int(10 * multiplier) 
                    players[pid]["words_cleared"] += 1
                    
                    triggered_power = None
                    if players[pid]["power"] >= 100:
                        players[pid]["power"] = 0 
                        powers_json = await self.redis.hget(f"game:{code}", "powers")
                        powers = json.loads(powers_json) if powers_json else []
                        if powers:
                            triggered_power = random.choice(powers)
                            await self.trigger_power(code, pid, triggered_power)
                    
                    await self.redis.hset(f"game:{code}", "players", json.dumps(players))
                    
                    await self.redis.publish(f"game:{code}:events", json.dumps({
                        "type": "word_cleared",
                        "player_id": pid,
                        "word_id": wid,
                        "new_power": players[pid]["power"],
                        "triggered_power": triggered_power,
                        "combo": players[pid]["combo"]
                    }))
                    return True
        return False

    async def trigger_power(self, code: str, attacker_pid: str, power_type: str):
        if power_type == "clear_screen":
            await self.redis.delete(f"game:{code}:{attacker_pid}:words")
            await self.redis.publish(f"game:{code}:events", json.dumps({
                "type": "effect_clear_screen",
                "target_pid": attacker_pid
            }))
            return

        players_json = await self.redis.hget(f"game:{code}", "players")
        players = json.loads(players_json)
        
        opponent_pid = next((pid for pid in players if pid != attacker_pid), None)
        if not opponent_pid: return

        if power_type == "shake":
            await self.redis.publish(f"game:{code}:events", json.dumps({
                "type": "effect_shake",
                "target_pid": opponent_pid,
                "duration": 3000
            }))
        elif power_type == "barrage":
            words = ["BARRAGE", "ATTACK", "SWARM", "DANGER", "FAST"]
            for _ in range(5):
                await self._spawn_word(code, opponent_pid, random.choice(words))
        elif power_type == "blindness":
             await self.redis.publish(f"game:{code}:events", json.dumps({
                "type": "effect_blind",
                "target_pid": opponent_pid,
                "duration": 5000
            }))

    async def damage_player(self, code: str, pid: str, amount: int):
        players_json = await self.redis.hget(f"game:{code}", "players")
        players = json.loads(players_json)
        
        if pid in players:
            players[pid]["combo"] = 0
            players[pid]["health"] -= amount
            if players[pid]["health"] <= 0:
                players[pid]["health"] = 0
                await self.set_game_status(code, "finished")
                await self.redis.publish(f"game:{code}:events", json.dumps({
                    "type": "game_over",
                    "loser": pid
                }))
                
            await self.redis.hset(f"game:{code}", "players", json.dumps(players))
            await self.redis.publish(f"game:{code}:events", json.dumps({
                "type": "health_update",
                "player_id": pid,
                "new_health": players[pid]["health"],
                "combo": players[pid]["combo"]
            }))

    def _generate_id(self):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))