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
        
        # Extra words for Hard Bonus (8-10 chars)
        self.extra_hard_words = [
            "COMPUTER", "KEYBOARD", "DEVELOPER", "ENGINEER", "DATABASE", 
            "FRONTEND", "BACKEND", "PLATFORM", "VARIABLE", "FUNCTION", 
            "ITERATION", "PROTOCOL", "SECURITY", "SOFTWARE", "HARDWARE", 
            "INTERNET", "WIRELESS", "GRAPHICS", "OVERLOAD", "TERMINAL"
        ]
        
        # Create Bonus Pools
        all_words = set(self.easy_words + self.hard_words + self.default_words + self.extra_hard_words)
        self.bonus_easy = [w for w in all_words if 5 <= len(w) <= 8]
        self.bonus_hard = [w for w in all_words if 8 <= len(w) <= 10]
        
        if not self.bonus_easy: self.bonus_easy = ["BONUS"]
        if not self.bonus_hard: self.bonus_hard = ["SUPERBONUS"]

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

    async def _spawn_word(self, code, pid, word_text, x=None, y=10.0, vx=0.0, vy=None, duration=10.0, is_special=False):
        if x is None:
            x = random.uniform(-4, 4)
        word_id = self._generate_id()
        word_data = {
            "text": word_text,
            "id": word_id,
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy,
            "spawn_time": time.time(),
            "duration": duration,
            "is_special": is_special
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
                elif difficulty == "insane":
                    words_pool = self.bonus_hard # Base pool is 8-10 chars
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
                    
                    if random.random() < 0.1: # 10% Special
                        is_left = random.choice([True, False])
                        sx = -6 if is_left else 6
                        svx = 0.05 if is_left else -0.05
                        sy = random.uniform(2, 8)
                        
                        # Select Bonus Word based on difficulty
                        if difficulty == "hard" or difficulty == "insane":
                            bonus_text = random.choice(self.bonus_hard)
                        else:
                            bonus_text = random.choice(self.bonus_easy)
                        
                        if difficulty == "insane":
                             symbol = random.choice("!@#$%^&*?")
                             if random.choice([True, False]):
                                 bonus_text = symbol + bonus_text
                             else:
                                 bonus_text = bonus_text + symbol
                            
                        await self._spawn_word(code, pid, bonus_text, x=sx, y=sy, vx=svx, vy=0.0, duration=5.0, is_special=True)
                    else:
                        word_text = random.choice(words_pool)
                        if difficulty == "insane":
                             symbol = random.choice("!@#$%^&*?")
                             if random.choice([True, False]):
                                 word_text = symbol + word_text
                             else:
                                 word_text = word_text + symbol
                        
                        await self._spawn_word(code, pid, word_text, duration=duration)
                    
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
        print(f"DEBUG: submit_word called for {pid} with '{word_text}'")
        active_words = await self.redis.hgetall(f"game:{code}:{pid}:words")
        print(f"DEBUG: active_words keys: {list(active_words.keys())}")
        
        for wid, w_json in active_words.items():
            w = json.loads(w_json)
            # print(f"DEBUG: checking against '{w['text']}'")
            if w["text"] == word_text:
                print(f"DEBUG: MATCH FOUND for '{word_text}' (id: {wid})")
                await self.redis.hdel(f"game:{code}:{pid}:words", wid)
                
                players_json = await self.redis.hget(f"game:{code}", "players")
                players = json.loads(players_json)
                
                if pid in players:
                    bonus = 50 if w.get("is_special") else 0
                    players[pid]["power"] += 10 + bonus # 25 for testing
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
            difficulty = await self.redis.hget(f"game:{code}", "difficulty")
            pool = self.hard_words if difficulty == "hard" else self.easy_words
            # Fallback
            if not pool: pool = self.default_words
            
            for _ in range(5):
                await self._spawn_word(code, opponent_pid, random.choice(pool), duration=5.0) # Fast barrage
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