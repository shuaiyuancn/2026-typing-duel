FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
ENV PYTHONUNBUFFERED=1
# Install dependencies into the system python
ENV UV_SYSTEM_PYTHON=1

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

# Expose port (documentary)
EXPOSE 5001

# Command to run the application
CMD ["uv", "run", "python", "main.py"]