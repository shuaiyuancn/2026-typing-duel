# How to Start a New Web App from This Template

This template provides a production-ready "Hybrid" environment (Windows Host + Podman Linux Runtime) with FastHTML, FastSQL, and Postgres.

Follow these steps to create a fresh project:

### 1. Clone the Template Branch
Run this command to clone *only* the `template` branch into a new directory. Replace `my-new-app` with your desired project name.

```powershell
git clone -b template --single-branch https://github.com/shuaiyuancn/2026-todo.git my-new-app
```

### 2. Detach from the Old Repository
Navigate into your new folder and remove the `.git` directory. This creates a "clean slate" so your new app has its own history.

```powershell
cd my-new-app
Remove-Item -Recurse -Force .git  # PowerShell command to remove the hidden .git folder
git init                          # Initialize a brand new git repository
```

### 3. Personalize the Project
Update the project identity:

1.  **`pyproject.toml`:** Change `name = "todo"` to `name = "my-new-app"`.
2.  **`README.md`:** Update the title and description.
3.  **`.env`:** Create a `.env` file if it's missing (refer to `.env.example` or just create one with `DATABASE_URL` commented out for local dev).

### 4. Launch the Environment
Initialize the workflow:

```powershell
uv sync                 # Installs dependencies on Windows (for Intellisense)
podman-compose up -d    # Builds and starts the Linux containers
```

### 5. Verify
Open `http://localhost:5001`. You should see the "Hello World" message.

---

**Ready to Build?**
Refer to `GEMINI.md` for the complete Agentic Development Workflow.
