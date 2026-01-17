# Project Context: Typing Duel 3D

This document defines the operational context and workflow for this project. It serves as the primary instruction set for the Gemini Agent.

## 1. System Architecture & Environment

*   **Host OS:** Windows 11 (NTFS Filesystem).
*   **Runtime Environment:** Podman (Linux Containers) via `podman-compose` or `docker-compose`.
*   **Networking:** Host `localhost:5001` maps to Container `5001`.
*   **Codebase:** Located on Windows Host, mounted into the container at `/app`.

**Constraint:** The application code (`main.py`) runs **exclusively** inside the Container. The agent must NEVER attempt to run `python main.py` or `uvicorn` directly on the Windows host.

## 2. Technology Stack

*   **Language:** Python 3.12+
*   **Web Framework:** [FastHTML](https://fastht.ml/) (Hypermedia-driven UI) + Starlette (WebSockets).
*   **Game State Store:** **Redis** (Required for real-time lobbies/state).
*   **Audit Database:** SQLite/PostgreSQL (via [FastSQL](https://github.com/AnswerDotAI/fastsql)) or simple File Logging.
*   **Frontend Game Engine:** [Three.js](https://threejs.org/) (via CDN) + Vanilla JS.
    *   *Note:* FastHTML handles the Lobby/UI. Three.js handles the active gameplay canvas.
*   **Package Manager:** [uv](https://github.com/astral-sh/uv).

## 3. Development Guidelines

### A. Hybrid Architecture (The "Mullet" Pattern)
*   **Business in the Front (FastHTML):** Use FastHTML/HTMX for:
    *   Landing Page.
    *   Game Creation Forms.
    *   Lobby/Room Management.
    *   Game Over/Stats Screens.
*   **Party in the Back (Three.js + WebSockets):**
    *   Once the game starts, FastHTML swaps the body for a `<canvas>`.
    *   A client-side JS module connects to the WebSocket.
    *   The WebSocket dictates game events (Word Spawns, Health Updates).
    *   Three.js renders the 3D scene based on these events.

### B. State Management
*   **Redis Keys:** Use a consistent naming scheme, e.g., `game:{code}:state`, `game:{code}:players`.
*   **Concurrency:** Use async/await everywhere. Ensure Redis operations are atomic where possible.

### C. Dependency Management
*   The `uv.lock` file is the source of truth.
*   **To Add a Library:**
    1.  Run `uv add <package>` on the **Windows Host** (PowerShell).
    2.  Restart the container or run `uv sync` inside.

### D. Running the App
*   **Start:** `podman-compose up -d` (Ensure Redis service is defined in compose).
*   **Logs:** `podman logs -f palpay_dev` (or appropriate container name).
*   **Access:** Open `http://localhost:5001`.

## 4. Agent Instructions

When asked to implement features:
1.  **Verify First:** Check if Redis is running and accessible.
2.  **Edit on Host:** specific file paths `C:\workspace\...`.
3.  **Run in Container:** Use `podman exec ...` for scripts/tests.
4.  **Restart on Config Change:** If `pyproject.toml` or `.env` changes, restart the container.