# Product Requirements Document (PRD): Typing Duel 3D

## 1. Introduction
**Typing Duel 3D** is a real-time, multiplayer, browser-based typing competition game. Two players compete to type falling words, charging a power bar to unleash special attacks on their opponent. The game features a modern, sci-fi 3D aesthetic.

## 2. Goals & Scope
*   **Core Loop:** Type words -> Charge Power -> Unleash Attack -> Deplete Opponent Health -> Win.
*   **Platform:** Web Browsers (Desktop/Mobile).
*   **Target Audience:** Casual gamers, typing enthusiasts.
*   **Key Constraint:** No user accounts/login required. Ephemeral game sessions.

## 3. Functional Requirements

### 3.1 Game Session Management
*   **Create Game:** A user can create a new game room by providing:
    *   Player Name.
    *   Difficulty Level (Easy: Simple words, Hard: Complex words + symbols).
    *   Allowed Power-ups (Selection from available list).
*   **Join Game:** A user can join an existing game using a unique **Game Code**.
*   **Lobby:** A waiting area where players see each other's readiness before starting.

### 3.2 Gameplay Mechanics (Client-Side)
*   **View:** Stable 3D view (no dizziness-inducing rotation). Words fall from "top" to "bottom" in 3D space.
*   **Typing Engine:**
    *   Words spawn at a rate determined by difficulty.
    *   Typing a word correctly clears it and adds to the **Power Bar**.
    *   Typing errors provide visual feedback (shake/red flash) but do not penalize health directly.
*   **Health System:**
    *   If a word reaches the bottom of the screen, the player loses **Health**.
    *   Health reaches 0 -> Player Loses.
*   **Power System:**
    *   Filling the Power Bar triggers a "Special Event" countdown.
    *   During countdown, **Special Words** appear.
    *   Clearing Special Words triggers the selected offensive ability on the opponent.
*   **Abilities (Power-ups):**
    *   *Screen Shake:* Opponent's screen shakes violently for 3 seconds.
    *   *Word Barrage:* Instantly spawns 5 extra words on opponent's screen.
    *   *Blindness:* Opponent's view is obscured by "fog" or "glitch" effects for 5 seconds.

### 3.3 End of Game
*   **Win/Loss Screen:** Displays the winner and game statistics (WPM, Accuracy).
*   **Audit Log:** The system records the game start, join, and result (Winner, Duration) for server-side auditing.

## 4. Non-Functional Requirements
*   **Latency:** Real-time state synchronization (WebSockets) < 100ms.
*   **Performance:** 60 FPS rendering on average consumer hardware (via Three.js).
*   **Scalability:** Stateless application logic; game state stored in Redis.
*   **Security:** Input sanitization for names/codes. No sensitive PII stored.

## 5. Technical Architecture

### 5.1 Tech Stack
*   **Backend:** Python 3.12+ (FastHTML/Starlette) for HTTP/WebSockets.
*   **Frontend:**
    *   **UI Shell:** FastHTML (HTMX) for menus, lobby, and forms.
    *   **Game Rendering:** Three.js (WebGL) for the 3D typing experience.
    *   **Game Logic:** Vanilla JavaScript (Client-side prediction, Server reconciliation).
*   **Data Store:**
    *   **Game State:** Redis (Ephemeral data: lobbies, scores, active words).
    *   **Audit:** Simple Append-Only Log (Text file or DB).

### 5.2 Data Flow
1.  **Lobby:** FastHTML serves HTML forms. POST /create -> Returns Game Code.
2.  **Connection:** Players connect via WebSocket to `/ws/game/{game_code}`.
3.  **Sync:** Server broadcasts "Game Start".
4.  **Loop:**
    *   Server sends "Word Spawn" events.
    *   Client sends "Word Cleared" events.
    *   Server validates and broadcasts "Score Update" / "Attack Triggered".