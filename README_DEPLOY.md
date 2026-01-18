# Deployment Guide

This application requires **WebSockets** and **Long-running Background Tasks**, which are not supported by standard Serverless functions (like Vercel).

**Recommended Deployment:**
Deploy to a container-based platform like **Railway**, **Render**, or **Fly.io**.

## Option 1: Railway (Recommended)
1.  Push this repository to GitHub.
2.  Go to [Railway.app](https://railway.app/).
3.  "New Project" -> "Deploy from GitHub repo".
4.  Add a **Redis** service in Railway.
5.  In the Web Service settings (Variables), add:
    *   `REDIS_URL`: Connect to the Railway Redis service (Railway usually injects this automatically or provides a variable like `REDIS_PUBLIC_URL`).
    *   `PORT`: `5001` (or let Railway set it, the app defaults to 5001 but respects `PORT`).

## Option 2: Render
1.  Go to [Render.com](https://render.com/).
2.  "New" -> "Web Service".
3.  Connect your GitHub repo.
4.  Runtime: **Docker**.
5.  Add Environment Variable:
    *   `REDIS_URL`: `redis://...` (You can create a Redis instance on Render or use an external one).

## Why not Vercel?
Vercel Serverless functions have a 10-second timeout (by default) and do not support the persistent connections required for:
1.  **WebSockets:** For real-time typing synchronization.
2.  **Game Loop:** The server runs a background loop to spawn words and handle timeouts.

If you deploy to Vercel, the game creation might work (HTTP POST), but the game loop and real-time interactions will fail immediately.
