# FastHTML Hybrid Template (Windows + Podman)

A production-ready template for building "Hybrid" web applications using **FastHTML** and **FastSQL**, designed to allow dev on a **Windows Host** with a **Podman (Linux)** runtime environment.

## 🚀 Technology Stack

*   **Runtime:** Python 3.12+ (in Podman Linux Container)
*   **Web Framework:** [FastHTML](https://fastht.ml/)
*   **Database:** PostgreSQL (Production) with `psycopg2`
*   **ORM:** [FastSQL](https://github.com/AnswerDotAI/fastsql)
*   **Package Manager:** [uv](https://github.com/astral-sh/uv)
*   **Styling:** Materialize CSS (via CDN)
*   **Deployment:** Vercel (Serverless)

## 📋 Prerequisites

*   **OS:** Windows 10/11
*   **Container Runtime:** [Podman Desktop](https://podman-desktop.io/) (machine running and accessible via `podman`)
*   **Python Tooling:** [uv](https://github.com/astral-sh/uv) installed on Windows.

## 🛠️ Getting Started

Follow these steps to initialize a new project from this template:

### 1. Clone & Detach
An obvious way to start is to "Use this template" on Github to create a new repo. 
However, manually is also fine: clone the repository and reset the git history to start fresh.

```powershell
# Clone the repository
git clone <repository-url> my-new-app
cd my-new-app

# Remove old git history and initialize new one
Remove-Item -Recurse -Force .git
git init
```

### 2. Personalize
Update the project metadata to match your new application.

1.  **`pyproject.toml`**: Update `name` and `description`.
2.  **`compose.yaml`**: Update `container_name` for `web` and `db` services.

### 3. Launch Environment
Initialize the dependencies and start the containers.

```powershell
# Install dependencies locally (for editor Intellisense)
uv sync

# Start the application and database containers
podman-compose up -d
```

### 4. Verify
Open [http://localhost:5001](http://localhost:5001) in your browser. You should see the "Hello World" message with the database connection status.

## 💻 Development Workflow

*   **Editing Code**: Edit files on your Windows host (`main.py`, etc.). Changes are reflected in the container (note: auto-reload depends on `uvicorn` configuration, currently set to manual restart or `uv sync` triggers).
*   **Adding Libraries**:
    1.  Run `uv add <package_name>` on Windows.
    2.  Restart the container: `podman-compose restart web`.
*   **Running Tests**:
    Tests **must** run inside the Linux container.
    ```powershell
    podman exec -it todo_dev uv run pytest
    ```
    *(Replace `todo_dev` with your container name if you changed it in `compose.yaml`)*

## 🌍 Deployment (Vercel)

1.  **Push** your code to a GitHub repository.
2.  **Import** the project in Vercel.
3.  **Configure Environment Variables** in Vercel Settings:
    *   `DATABASE_URL`: Connection string to your remote Postgres database (e.g., Supabase, Neon).
    *   `AUTH_SECRET`: A random string for session security.
    *   `POSTGRES_URL_NON_POOLING`: (Optional) Use if your DB provider requires a separate non-pooling URL for SQLAlchemy.
4.  **Deploy**.

Or for quick manual deployment, run
```powershell
vercel --prod
```
in the folder to initialize the config, and deploy.

## 📂 Project Structure

```
├── compose.yaml       # Podman Compose configuration
├── Dockerfile         # Python environment definition
├── GEMINI.md          # AI Agent context and instructions
├── main.py            # Application entry point
├── pyproject.toml     # Python dependencies and metadata
├── uv.lock            # Lockfile for reproducible builds
├── vercel.json        # Vercel deployment config
└── tests/             # Test suite
```
