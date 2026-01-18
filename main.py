from fasthtml.common import *
from starlette.websockets import WebSocket, WebSocketDisconnect
from game import GameManager
import os
import asyncio
import json
import time

# Init GameManager
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
gm = GameManager(redis_url)

app, rt = fast_app(
    hdrs=(
        Link(rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css'),
        Script(src='https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js'),
        Link(rel='stylesheet', href='index.css'),
    ), 
    pico=False
)

@rt('/')
def get():
    return Title("Typing Duel 3D"), Div(
        H1("Typing Duel 3D", cls="center-align teal-text text-lighten-2"),
        Div(
            # Create Game Card
            Div(
                Div(
                    Div(
                        Span("Create Game", cls="card-title"),
                        Form(
                            Div(
                                Label("Player Name", cls="active"),
                                Input(name="name", placeholder="Enter your name", required=True),
                                cls="input-field"
                            ),
                            Div(
                                Label("Difficulty", style="font-size: 1rem; color: #9e9e9e; display: block; margin-bottom: 5px;"),
                                Select(
                                    Option("Easy", value="easy"),
                                    Option("Hard", value="hard"),
                                    name="difficulty",
                                    cls="browser-default"
                                ),
                                style="margin-bottom: 25px;"
                            ),
                             Div(
                                Label("Power-ups", style="font-size: 1rem; color: #9e9e9e; display: block; margin-bottom: 10px;"),
                                P(
                                    Label(
                                        Input(type="checkbox", name="powers", value="shake", checked=True),
                                        Span("Screen Shake")
                                    )
                                ),
                                P(
                                    Label(
                                        Input(type="checkbox", name="powers", value="barrage", checked=True),
                                        Span("Word Barrage")
                                    )
                                ),
                                 P(
                                    Label(
                                        Input(type="checkbox", name="powers", value="blindness"),
                                        Span("Blindness")
                                    )
                                ),
                                style="margin-bottom: 25px;"
                            ),
                            Button("Create", type="submit", cls="btn waves-effect waves-light teal lighten-1"),
                            action="/create", method="post"
                        ),
                        cls="card-content"
                    ),
                    cls="card grey lighten-4"
                ),
                cls="col s12 m4"
            ),
            # Join Game Card
            Div(
                Div(
                    Div(
                        Span("Join Game", cls="card-title"),
                        Form(
                            Div(
                                Label("Player Name", cls="active"),
                                Input(name="name", placeholder="Enter your name", required=True),
                                cls="input-field"
                            ),
                            Div(
                                Label("Game Code", cls="active"),
                                Input(name="code", placeholder="ABCD", required=True, style="text-transform:uppercase"),
                                cls="input-field"
                            ),
                            Button("Join", type="submit", cls="btn waves-effect waves-light orange lighten-1"),
                            action="/join", method="post"
                        ),
                        cls="card-content"
                    ),
                    cls="card grey lighten-4"
                ),
                cls="col s12 m4"
            ),
            # Practice Mode Card
            Div(
                Div(
                    Div(
                        Span("Practice Mode", cls="card-title"),
                        P("Solo play. Power: Clear Screen.", cls="grey-text"),
                        Form(
                            Div(
                                Label("Player Name", cls="active"),
                                Input(name="name", placeholder="Enter your name", required=True),
                                cls="input-field"
                            ),
                            Button("Start Solo", type="submit", cls="btn waves-effect waves-light purple lighten-1"),
                            action="/practice", method="post"
                        ),
                        cls="card-content"
                    ),
                    cls="card grey lighten-4"
                ),
                cls="col s12 m4"
            ),
            cls="row"
        ),
        cls="container", style="margin-top: 5vh;"
    )



@rt('/create')
async def post(name: str, difficulty: str, powers: list[str] = None):
    # powers might be None if no checkboxes are checked, or a list, or a single value? 
    # FastHTML/Starlette form parsing usually gives a list for multiple values with same key.
    if powers is None: powers = []
    # If it's a single string (not likely with list[str] type hint but possible in raw form data), wrap it
    if isinstance(powers, str): powers = [powers]
    
    code, pid = await gm.create_game(name, difficulty, powers)
    return RedirectResponse(f"/lobby/{code}?pid={pid}", status_code=303)

@rt('/practice')
async def post(name: str):
    code, pid = await gm.create_practice_game(name)
    return RedirectResponse(f"/lobby/{code}?pid={pid}", status_code=303)



@rt('/join')
async def post(name: str, code: str):
    code = code.upper()
    pid = await gm.join_game(code, name)
    if not pid:
        return Title("Error"), Div(H4("Could not join game"), P("Invalid code or game full."), A("Back", href="/join", cls="btn"), cls="container")
    return RedirectResponse(f"/lobby/{code}?pid={pid}", status_code=303)

@rt('/lobby/{code}')
async def get(code: str, pid: str):
    game = await gm.get_game_state(code)
    if not game:
        return RedirectResponse("/", status_code=303)
    
    is_host = (game["host_id"] == pid)
    
    return Title(f"Lobby {code}"), Div(
        H2(f"Lobby: {code}", cls="center-align"),
        Div(id="lobby-status", cls="center-align flow-text"),
        Div(
             P("Waiting for opponent...", cls="grey-text"),
             # Hidden inputs to pass data to JS
             Input(type="hidden", id="game-code", value=code),
             Input(type="hidden", id="player-id", value=pid),
             Input(type="hidden", id="is-host", value="true" if is_host else "false"),
             
             Button("Start Game", id="start-btn", cls="btn-large pulse", style="display: none;" if not is_host else "", disabled=True),
             
             cls="center-align"
        ),
        # Placeholder for 3D Game Canvas
        Div(id="game-container", style="width: 100%; height: 600px; display: none;"),
        
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"),
        Script(src=f"/game_client.js?v={int(time.time())}"), 
        cls="container"
    )

# Serve static files
@rt("/{fname:path}.{ext:static}")
async def get(fname: str, ext: str): 
    return FileResponse(f'{fname}.{ext}')

@rt("/{fname:path}.m4a")
async def get(fname: str): 
    return FileResponse(f'{fname}.m4a')

async def ws_game(ws: WebSocket):
    code = ws.path_params['code']
    pid = ws.path_params['pid']
    
    await ws.accept()
    
    # Subscribe to Redis channel
    pubsub = gm.redis.pubsub()
    await pubsub.subscribe(f"game:{code}:events")
    
    # Send current state
    game = await gm.get_game_state(code)
    if game:
         await ws.send_text(json.dumps({"type": "game_state", "game": game}))
    
    async def redis_reader():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await ws.send_text(message["data"])
        except Exception as e:
            print(f"Redis reader error: {e}")

    # Start reader task
    reader_task = asyncio.create_task(redis_reader())
    
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "start_game":
                    # Verify host
                    game = await gm.get_game_state(code)
                    if game and game["host_id"] == pid:
                         await gm.set_game_status(code, "playing")
                         asyncio.create_task(gm.start_game_loop(code))
                
                elif msg.get("type") == "submit_word":
                    word = msg.get("word")
                    if word:
                        await gm.submit_word(code, pid, word)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        print(f"Player {pid} disconnected")
        reader_task.cancel()
        await pubsub.unsubscribe()

app.add_websocket_route("/ws/game/{code}/{pid}", ws_game)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    serve(host="0.0.0.0", port=port)
