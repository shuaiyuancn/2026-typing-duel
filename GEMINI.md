# Project Template: Hybrid FastHTML on Windows/Podman

This document defines the operational context and workflow for this project. It serves as the primary instruction set for the Gemini Agent.

## 1. System Architecture & Environment

*   **Host OS:** Windows 11 (NTFS Filesystem).
*   **Runtime Environment:** Podman (Linux Containers) via `podman-compose`.
*   **Networking:** Host `localhost:5001` maps to Container `5001`.
*   **Codebase:** Located on Windows Host, mounted into the container at `/app`.

**Constraint:** The application code (`main.py`) runs **exclusively** inside the Podman container. The agent must NEVER attempt to run `python main.py` or `uvicorn` directly on the Windows host.

## 2. Technology Stack

*   **Language:** Python 3.12+
*   **Web Framework:** [FastHTML](https://fastht.ml/) (Hypermedia-driven UI).
*   **Database:** PostgreSQL (Production) / `psycopg2` driver.
    *   **ORM:** [FastSQL](https://github.com/AnswerDotAI/fastsql) (SQLAlchemy wrapper).
*   **UI Framework:** Materialize CSS (via CDN).
*   **Package Manager:** [uv](https://github.com/astral-sh/uv) (Managed via `pyproject.toml` and `uv.lock`).
*   **Deployment:** Vercel (Serverless).

## 3. Development Guidelines (Lessons Learned)

### A. FastSQL & Models
*   **Dataclasses:** All models MUST be defined as `@dataclass`.
*   **Primary Keys:** If the DB schema has an `id` column, the Python model SHOULD include `id: Optional[int] = None` to allow deletion/updates by ID.
*   **Table Names:** FastSQL defaults to **singular** table names (e.g., `user`, `cost`). Use singular names in raw SQL queries.
*   **Decimal Types:** When rendering `Decimal` values in f-strings, explicit casting is required (e.g., `f"{float(amount):.2f}"`) to avoid `ValueError`.

### B. Vercel & Environment
*   **Read-Only Filesystem:** Vercel functions are read-only (except `/tmp`). `FastHTML` tries to write `.sesskey` by default.
    *   **Fix:** Always pass `secret_key` to `fast_app()`. Read it from `AUTH_SECRET` env var.
*   **Environment Variables:**
    *   `.env` files are **ignored** by Vercel deployment.
    *   **DATABASE_URL:** Must be set in Vercel Project Settings.
    *   **AUTH_SECRET:** Must be set in Vercel Project Settings.

### C. UI & Forms
*   **Materialize Select:** Hides the native `<select>` element. Standard HTML5 `required` validation will block submission without feedback.
    *   **Fix:** Do not use `required=True` on `Select` components if using Materialize. Validate on backend.

## 4. Development Workflow

### A. Dependency Management
*   The `uv.lock` file is the source of truth.
*   **To Add a Library:**
    1.  Run `uv add <package>` on the **Windows Host** (PowerShell).
    2.  Restart the container (`podman-compose restart web`) or run `uv sync` inside the container.

### B. Running the App
*   **Start:** `podman-compose up -d`
*   **Logs:** `podman logs -f palpay_dev`
*   **Access:** Open `http://localhost:5001`.

### C. Testing
*   Tests must run **inside** the Linux container.
*   **Command:** `podman exec palpay_dev uv run pytest`

## 5. Deployment Checklist (Vercel)

1.  **Push to GitHub.**
2.  **Vercel Settings:**
    *   Set `DATABASE_URL` (Remote Postgres, e.g., Supabase/Neon).
    *   Set `AUTH_SECRET` (Random string for session signing).
    *   Set `POSTGRES_URL_NON_POOLING` if applicable.
3.  **Deploy.**

## 6. Agent Instructions

When asked to implement features:
1.  **Verify First:** Check `podman ps` to ensure the environment is active.
2.  **Edit on Host:** specific file paths `C:\workspace\...`.
3.  **Run in Container:** Use `podman exec ...` for scripts/tests.
4.  **Restart on Config Change:** If `pyproject.toml` or `.env` changes, restart the container.
