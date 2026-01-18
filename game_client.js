// Game Client
const gameCode = document.getElementById('game-code').value;
const playerId = document.getElementById('player-id').value;
const isHost = document.getElementById('is-host').value === 'true';
const gameContainer = document.getElementById('game-container');
const lobbyStatus = document.getElementById('lobby-status');
const startBtn = document.getElementById('start-btn');

// State
let activeWords = new Map(); // id -> {sprite, text, x, startY, speed}
let particles = [];
let floatingTexts = [];
let currentInput = "";
let gameRunning = false;

// WebSocket Setup
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/game/${gameCode}/${playerId}`;
const ws = new WebSocket(wsUrl);

// HUD Elements
let inputDisplay, healthDisplay, powerDisplay;

ws.onopen = () => {
    console.log("Connected to Game Server");
    lobbyStatus.innerText = "Connected! Waiting for opponent...";
};

ws.onmessage = (event) => {
    try {
        const msg = JSON.parse(event.data);
        
        if (msg.type === 'game_state') {
            const players = msg.game.players || {};
            const count = Object.keys(players).length;
            lobbyStatus.innerText = `Lobby: ${count} Player(s) connected.`;
            
            if (msg.game.status === 'playing') {
                initGame();
            } else if (count >= 2 || msg.game.mode === 'practice') {
                lobbyStatus.innerText += " Ready to start.";
                if (isHost && startBtn) startBtn.disabled = false;
            }
        }

        if (msg.type === 'player_joined') {
            lobbyStatus.innerText = `Player ${msg.player.name} joined! Ready to start.`;
            if (isHost && startBtn) startBtn.disabled = false;
        }
        
        if (msg.type === 'status_change' && msg.status === 'playing') {
            initGame();
        }
        
        if (msg.type === 'word_spawn' && gameRunning) {
            if (msg.target_pid === playerId) {
                spawnWord(msg.word);
            }
        }
        
        if (msg.type === 'word_cleared') {
            // Capture pos before remove
            const w = activeWords.get(msg.word_id);
            if (w && msg.player_id === playerId) {
                spawnFloatingText("+10", w.sprite.position.x, w.sprite.position.y, 0xffff00, scene);
            }
            
            removeWord(msg.word_id, true); // True for explosion
            if (msg.player_id === playerId) {
                updatePower(msg.new_power);
                updateCombo(msg.combo);
                if (msg.triggered_power) {
                    showNotification(`POWER ACTIVATED: ${msg.triggered_power.toUpperCase()}!`);
                }
            } else {
                updatePower(msg.new_power, true);
            }
        }
        
        if (msg.type === 'word_expired') {
            removeWord(msg.word_id, false);
        }
        
        if (msg.type === 'health_update') {
            if (msg.player_id === playerId) {
                updateHealth(msg.new_health);
                if (msg.combo !== undefined) updateCombo(msg.combo);
            } else {
                updateHealth(msg.new_health, true);
            }
        }
        
        if (msg.type === 'effect_shake') {
            if (msg.target_pid === playerId) {
                triggerShake(msg.duration);
                showNotification("INCOMING ATTACK: SHAKE!");
            }
        }
        
        if (msg.type === 'effect_blind') {
            if (msg.target_pid === playerId) {
                triggerBlindness(msg.duration);
                showNotification("INCOMING ATTACK: BLINDNESS!");
            }
        }
        
        if (msg.type === 'effect_clear_screen') {
            if (msg.target_pid === playerId) {
                activeWords.forEach((data, id) => {
                    removeWord(id, true);
                });
                showNotification("SCREEN CLEARED!");
            }
        }
        
        if (msg.type === 'game_over') {
            if (bgAudio) {
                bgAudio.pause();
                bgAudio.currentTime = 0;
            }
            const result = msg.loser === playerId ? "YOU LOSE" : "YOU WIN";
            alert(`GAME OVER: ${result}`);
            location.reload();
        }

    } catch (e) {
        console.log("Error:", e);
    }
};

ws.onerror = (error) => {
    console.error("WS Error:", error);
    lobbyStatus.innerText = "Connection Error. Check console.";
};

if (startBtn) {
    startBtn.onclick = () => {
        ws.send(JSON.stringify({type: "start_game"}));
    };
}

// Three.js & Game Logic
let bgAudio;
let audioUnlocked = false;

function startMusic() {
    if (bgAudio && !bgAudio.paused) return;
    
    if (!bgAudio) {
        bgAudio = new Audio('/bg.m4a');
        bgAudio.loop = true;
        bgAudio.volume = 1.0;
    }
    
    bgAudio.play().then(() => {
        audioUnlocked = true;
    }).catch(e => {
        console.log("Audio autoplay blocked. Waiting for interaction.");
        audioUnlocked = false;
    });
}

function initGame() {
    if (gameRunning) return;
    gameRunning = true;

    // Start Audio
    startMusic();

    document.querySelector('.container').style.display = 'none';  
    gameContainer.style.display = 'block';
    
    document.body.style.margin = 0;
    document.body.style.overflow = 'hidden';
    document.body.innerHTML = ''; 
    document.body.appendChild(gameContainer);
    gameContainer.style.width = '100vw';
    gameContainer.style.height = '100vh';

    createHUD();

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111); 

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 10;
    camera.position.y = 2;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    gameContainer.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(0, 10, 5);
    scene.add(directionalLight);

    const gridHelper = new THREE.GridHelper(40, 40, 0x00ffff, 0x222222);
    gridHelper.position.y = -5;
    scene.add(gridHelper);
    
    // Starfield
    const starGeo = new THREE.BufferGeometry();
    const starCnt = 1000;
    const starArr = new Float32Array(starCnt * 3);
    for(let i=0; i<starCnt*3; i++) {
        starArr[i] = (Math.random() - 0.5) * 200;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starArr, 3));
    const starMat = new THREE.PointsMaterial({size: 0.2, color: 0xffffff});
    const starMesh = new THREE.Points(starGeo, starMat);
    scene.add(starMesh);

    const wordGroup = new THREE.Group();
    scene.add(wordGroup);

    // Render Loop
    function animate() {
        requestAnimationFrame(animate);
        
        // Animate Background
        starMesh.rotation.y += 0.0002;
        gridHelper.position.z = (gridHelper.position.z + 0.05) % 1;
        
        // Move words
        activeWords.forEach((data, id) => {
            data.sprite.position.x += data.vx;
            // vy is falling speed (positive value), so subtract
            // Special words might have vy=0
            if (data.vy) data.sprite.position.y -= data.vy; 
        });

        // Move Particles
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.update();
            if (p.isDead()) {
                scene.remove(p.mesh);
                particles.splice(i, 1);
            }
        }
        
        // Update Floating Texts
        for (let i = floatingTexts.length - 1; i >= 0; i--) {
            const t = floatingTexts[i];
            t.update();
            if (t.isDead()) {
                scene.remove(t.mesh);
                floatingTexts.splice(i, 1);
            }
        }

        renderer.render(scene, camera);
    }
    animate();
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    window.spawnWord = (wordData) => {
        const color = wordData.is_special ? "#ffd700" : "rgba(0,255,0,1)";
        const sprite = createTextSprite(wordData.text, color);
        sprite.position.set(wordData.x, wordData.y || 10, 0);
        wordGroup.add(sprite);
        
        const duration = wordData.duration || 10.0;
        // Standard falling speed if vy not provided
        const stdSpeed = 15.0 / (duration * 60.0);
        const vy = (wordData.vy !== undefined && wordData.vy !== null) ? wordData.vy : stdSpeed;
        
        activeWords.set(wordData.id, {
            sprite: sprite,
            text: wordData.text,
            id: wordData.id,
            vx: wordData.vx || 0,
            vy: vy,
            is_special: wordData.is_special
        });
    };

    window.removeWord = (wordId, explode=false) => {
        const data = activeWords.get(wordId);
        if (data) {
            if (explode) {
                spawnExplosion(data.sprite.position.x, data.sprite.position.y, 0x00ff00, scene);
                
                // Play random explosion sound
                const explosionSound = new Audio(`/explosion-${Math.floor(Math.random() * 5) + 1}.mp3`);
                explosionSound.volume = 0.5; // Adjust volume as needed
                explosionSound.play().catch(e => console.log("Explosion audio failed:", e));
            }
            wordGroup.remove(data.sprite);
            activeWords.delete(wordId);
        }
    };
    
    document.addEventListener('keydown', handleInput);
}

function createTextSprite(message, color="rgba(0,255,0,1)", highlightLen=0) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512; // Increase resolution for better distortion
    canvas.height = 128;
    
    const fonts = ['Arial', 'Verdana', 'Courier New', 'Georgia', 'Impact', 'Trebuchet MS', 'Comic Sans MS'];
    // Deterministic font based on message length to avoid jitter on redraw
    const fontName = fonts[message.length % fonts.length]; 
    context.font = `Bold 48px "${fontName}"`;
    
    // 1. Distortion: Random Skew
    // Use fixed seed based on message to avoid jitter
    const seed = message.length; 
    const skewX = (Math.sin(seed) * 0.5) * 0.5; 
    const skewY = (Math.cos(seed) * 0.5) * 0.1; 
    context.setTransform(1, skewY, skewX, 1, 0, 0);

    // 2. Chromatic Aberration (Glitch)
    context.fillStyle = "rgba(255,0,0,0.7)";
    context.fillText(message, 10 + (Math.sin(seed)*4-2), 64);
    
    context.fillStyle = "rgba(0,0,255,0.7)";
    context.fillText(message, 10 + (Math.cos(seed)*4-2), 64);
    
    // Main Text with Highlight
    if (highlightLen > 0) {
        const matched = message.substring(0, highlightLen);
        const rest = message.substring(highlightLen);
        
        context.fillStyle = "#ffff00"; // Yellow Highlight
        context.fillText(matched, 10, 64);
        
        const matchedWidth = context.measureText(matched).width;
        context.fillStyle = color;
        context.fillText(rest, 10 + matchedWidth, 64);
    } else {
        context.fillStyle = color;
        context.fillText(message, 10, 64);
    }
    
    const texture = new THREE.Texture(canvas);
    texture.needsUpdate = true;
    
    const material = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(4, 1, 1); 
    return sprite;
}

function spawnFloatingText(text, x, y, color, scene) {
    const sprite = createTextSprite(text, "rgba(255, 255, 0, 1)");
    sprite.scale.set(2, 1, 1);
    sprite.position.set(x, y, 0);
    scene.add(sprite);
    
    floatingTexts.push({
        mesh: sprite,
        life: 1.0,
        update: function() {
            this.mesh.position.y += 0.05;
            this.life -= 0.02;
            this.mesh.material.opacity = this.life;
        },
        isDead: function() { return this.life <= 0; }
    });
}

function spawnExplosion(x, y, color, scene) {
    const particleCount = 15;
    
    for (let i = 0; i < particleCount; i++) {
        const material = new THREE.SpriteMaterial({ color: color });
        const sprite = new THREE.Sprite(material);
        sprite.scale.set(0.2, 0.2, 1);
        sprite.position.set(x, y, 0);
        
        const velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 0.3,
            (Math.random() - 0.5) * 0.3,
            (Math.random() - 0.5) * 0.3
        );
        
        scene.add(sprite);
        
        particles.push({
            mesh: sprite,
            velocity: velocity,
            life: 1.0,
            update: function() {
                this.mesh.position.add(this.velocity);
                this.life -= 0.03;
                this.mesh.material.opacity = this.life;
                this.mesh.scale.multiplyScalar(0.95); // shrink
            },
            isDead: function() { return this.life <= 0; }
        });
    }
}

function createHUD() {
    const hud = document.createElement('div');
    hud.style.position = 'absolute';
    hud.style.top = '10px';
    hud.style.left = '10px';
    hud.style.color = 'white';
    hud.style.fontFamily = 'monospace';
    hud.style.fontSize = '24px';
    hud.style.zIndex = '100';
    
    healthDisplay = document.createElement('div');
    healthDisplay.innerText = "HEALTH: 100%";
    healthDisplay.style.color = '#ff3333';
    hud.appendChild(healthDisplay);
    
    powerDisplay = document.createElement('div');
    powerDisplay.innerText = "POWER: 0%";
    powerDisplay.style.color = '#33ccff';
    powerDisplay.style.marginTop = '10px';
    hud.appendChild(powerDisplay);
    
    comboDisplay = document.createElement('div');
    comboDisplay.innerText = "COMBO: 0";
    comboDisplay.style.color = '#ffff00';
    comboDisplay.style.marginTop = '10px';
    comboDisplay.style.fontWeight = 'bold';
    hud.appendChild(comboDisplay);
    
    inputDisplay = document.createElement('div');
    inputDisplay.innerText = "INPUT: >_";
    inputDisplay.style.color = '#33ff33';
    inputDisplay.style.marginTop = '10px';
    hud.appendChild(inputDisplay);
    
    document.body.appendChild(hud);
}

function updateHealth(val, isOpponent=false) {
    if (isOpponent) {
        const el = document.getElementById('opp-health');
        if (el) el.innerText = `OPPONENT: ${val}%`;
    } else {
        if (healthDisplay) healthDisplay.innerText = `HEALTH: ${val}%`;
    }
}

function updatePower(val, isOpponent=false) {
    if (isOpponent) {
        const el = document.getElementById('opp-power');
        if (el) el.innerText = `POWER: ${val}%`;
    } else {
        if (powerDisplay) powerDisplay.innerText = `POWER: ${val}%`;
    }
}

function updateCombo(val) {
    if (comboDisplay) comboDisplay.innerText = `COMBO: ${val}`;
}

function showNotification(msg) {
    const notif = document.createElement('div');
    notif.innerText = msg;
    notif.style.position = 'absolute';
    notif.style.top = '20%';
    notif.style.left = '50%';
    notif.style.transform = 'translateX(-50%)';
    notif.style.color = 'yellow';
    notif.style.fontSize = '40px';
    notif.style.fontWeight = 'bold';
    notif.style.fontFamily = 'monospace';
    notif.style.textShadow = '2px 2px black';
    notif.style.zIndex = '200';
    document.body.appendChild(notif);
    
    setTimeout(() => document.body.removeChild(notif), 2000);
}

function handleInput(e) {
    if (!audioUnlocked) {
        startMusic();
    }

    if (!gameRunning) return;
    
    if (e.key === "Backspace") {
        currentInput = currentInput.slice(0, -1);
    } else if (e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
        currentInput += e.key.toUpperCase();
    }
    
        // Update UI
    
        inputDisplay.innerText = `INPUT: > ${currentInput}`;
    
        
    
        // Check Matches & Update Highlights
    
        let exactMatchId = null;
    
        
    
        activeWords.forEach((data, id) => {
    
            if (data.text === currentInput) {
    
                exactMatchId = id;
    
            }
    
            
    
            // Highlight Partial
    
            if (data.text.startsWith(currentInput) && currentInput.length > 0) {
    
                // Update Sprite if not already highlighted to this length
    
                // Need to store currentHighlightLen to avoid redraw?
    
                // For now just redraw, canvas is cheap enough for low word count
    
                const newSprite = createTextSprite(data.text, "rgba(0,255,0,1)", currentInput.length);
    
                newSprite.position.copy(data.sprite.position);
    
                wordGroup.remove(data.sprite);
    
                wordGroup.add(newSprite);
    
                data.sprite = newSprite;
    
            } else {
    
                // Reset if it was highlighted but now isn't (backspace or divergence)
    
                // Ideally we check if it needs reset. createTextSprite default is len=0
    
                 const newSprite = createTextSprite(data.text, "rgba(0,255,0,1)", 0);
    
                 newSprite.position.copy(data.sprite.position);
    
                 wordGroup.remove(data.sprite);
    
                 wordGroup.add(newSprite);
    
                 data.sprite = newSprite;
    
            }
    
        });
    
        
    
        if (exactMatchId) {
    
            ws.send(JSON.stringify({type: "submit_word", word: currentInput}));
    
            currentInput = "";
    
            inputDisplay.innerText = "INPUT: >_"; 
    
            
    
            const data = activeWords.get(exactMatchId);
    
            data.sprite.material.color.set(0xffff00); 
    
        }
    
    }

// Effects
function triggerShake(duration) {
    const startTime = Date.now();
    const originalTransform = gameContainer.style.transform;
    
    function shake() {
        if (Date.now() - startTime < duration) {
            const dx = (Math.random() - 0.5) * 50; 
            const dy = (Math.random() - 0.5) * 50;
            gameContainer.style.transform = `translate(${dx}px, ${dy}px)`;
            requestAnimationFrame(shake);
        } else {
            gameContainer.style.transform = originalTransform || 'none';
        }
    }
    shake();
}

function triggerBlindness(duration) {
    const blindDiv = document.createElement('div');
    blindDiv.style.position = 'absolute';
    blindDiv.style.top = '0';
    blindDiv.style.left = '0';
    blindDiv.style.width = '100vw';
    blindDiv.style.height = '100vh';
    blindDiv.style.backgroundColor = 'black';
    blindDiv.style.zIndex = '999';
    blindDiv.style.display = 'flex';
    blindDiv.style.alignItems = 'center';
    blindDiv.style.justifyContent = 'center';
    blindDiv.style.color = 'red';
    blindDiv.style.fontFamily = 'monospace';
    blindDiv.style.fontSize = '64px';
    blindDiv.style.fontWeight = 'bold';
    blindDiv.innerText = "SYSTEM MALFUNCTION";
    
    document.body.appendChild(blindDiv);
    
    setTimeout(() => {
        if (blindDiv.parentNode) document.body.removeChild(blindDiv);
    }, duration);
}
