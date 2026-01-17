from fasthtml.common import *
from fastsql import Database
import os

# --- Database Setup ---
def get_db_url():
    # Priority 1: DATABASE_URL (set in compose.yaml or Vercel)
    url = os.getenv("DATABASE_URL")
    if url: 
        return url.replace("postgres://", "postgresql://")
    
    # Priority 2: Supabase Non-Pooling (Best for SQLAlchemy/FastSQL)
    non_pooling_url = os.getenv("POSTGRES_URL_NON_POOLING")
    if non_pooling_url: 
        return non_pooling_url.replace("postgres://", "postgresql://")

    # Priority 3: Supabase / Postgres env vars
    pg_url = os.getenv("POSTGRES_URL")
    if pg_url: 
        return pg_url.replace("postgres://", "postgresql://")
    
    # Fallback/Default
    return "postgresql://postgres:postgres@localhost:5432/postgres"

db_url = get_db_url()
db = Database(db_url)

# --- App Setup ---
app, rt = fast_app(hdrs=(Link(rel='stylesheet', href='index.css'),), 
                    pico=False)

@rt('/')
def get():
    return Main(
        Div(
            H1("Hello World"),
            P(f"FastHTML Template Running."),
            P(f"Database URL detected: {db_url.split('@')[-1] if '@' in db_url else 'Local/Unknown'}"),
            cls="container"
        )
    )

if __name__ == "__main__":
    serve()