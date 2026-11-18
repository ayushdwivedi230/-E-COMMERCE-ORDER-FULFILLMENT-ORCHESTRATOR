# E-Commerce Order Fulfillment Orchestrator
## Comprehensive Deployment Guide

This guide provides step-by-step instructions for deploying the complete application (FastAPI Backend with WebSockets, PostgreSQL Database, and React + TypeScript Frontend) across cloud platforms.

---

## Architecture Requirements for Deployment

1. **Persistent WebSockets:** The orchestrator streams real-time agent execution telemetry to the frontend via `/ws/orders`. The backend host must support persistent long-lived WebSocket connections (Serverless functions like AWS Lambda or Vercel Serverless timeout on persistent WebSockets).
2. **PostgreSQL Database:** Managed PostgreSQL database (version 14+) with auto-migration / schema initialization on startup.
3. **SPA Frontend Hosting:** Single Page Application (React + Vite) with rewrite rules routing all paths to `index.html`.

---

## Option 1: Railway (Recommended — Best All-in-One)

[Railway](https://railway.app) supports FastAPI, native WebSockets, PostgreSQL, and React in a single project with automatic GitHub synchronization.

### Step 1: Deploy PostgreSQL Database
1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** $\rightarrow$ **Provision PostgreSQL**.
3. Railway automatically generates your `DATABASE_URL`.

### Step 2: Deploy Backend Service (FastAPI)
1. In the same Railway project, click **New** $\rightarrow$ **GitHub Repo**.
2. Select `ayushdwivedi230/-E-COMMERCE-ORDER-FULFILLMENT-ORCHESTRATOR`.
3. In the service settings:
   - **Root Directory:** `/` (or `backend`)
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. In **Variables**, add:
   - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}` (Railway references the database automatically)
   - `APP_ENV`: `production`
   - `CORS_ORIGINS`: `*` (or your frontend domain)
5. Generate a public domain (e.g., `https://ecommerce-backend-production.up.railway.app`).

### Step 3: Deploy Frontend (React)
1. In the same Railway project, click **New** $\rightarrow$ **GitHub Repo**.
2. Select the same repository.
3. In the service settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npx serve -s dist -l $PORT`
4. In **Variables**, add:
   - `VITE_API_URL`: `https://ecommerce-backend-production.up.railway.app`
   - `VITE_WS_URL`: `wss://ecommerce-backend-production.up.railway.app/ws/orders`
5. Generate a public domain (e.g., `https://ecommerce-dashboard-production.up.railway.app`).

---

## Option 2: Render.com (Popular Free / Low-Cost Tier)

Render provides free static site hosting and low-cost Web Services with PostgreSQL.

### 1. PostgreSQL Database
- Go to [render.com](https://render.com) $\rightarrow$ **New** $\rightarrow$ **PostgreSQL**.
- Copy the **Internal Database URL** (for backend communication).

### 2. Backend Web Service
- Click **New** $\rightarrow$ **Web Service** $\rightarrow$ Connect GitHub repository.
- **Runtime:** Python
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables:**
  - `DATABASE_URL`: Paste Render PostgreSQL URL.
  - `CORS_ORIGINS`: `*`
- Render supports WebSockets on standard Web Services out of the box.

### 3. Frontend Static Site
- Click **New** $\rightarrow$ **Static Site** $\rightarrow$ Connect GitHub repository.
- **Root Directory:** `frontend`
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Environment Variables:**
  - `VITE_API_URL`: Your Render backend URL (`https://...onrender.com`)
  - `VITE_WS_URL`: Your Render backend WebSocket URL (`wss://...onrender.com/ws/orders`)
- **Redirects/Rewrites:** Add Rewrite rule `/*` $\rightarrow$ `/index.html` (Status: 200).

---

## Option 3: Hybrid (Vercel / Netlify for Frontend + Railway for Backend)

Deploying the React frontend to Vercel/Netlify leverages their global edge CDN, while Railway handles backend agents and database.

### Frontend on Vercel:
1. Import GitHub repository into [Vercel](https://vercel.com).
2. Framework Preset: **Vite**.
3. Root Directory: `frontend`.
4. Environment Variables:
   - `VITE_API_URL`: `https://your-backend.railway.app`
   - `VITE_WS_URL`: `wss://your-backend.railway.app/ws/orders`
5. Deploy.

---

## Option 4: Self-Hosted / Single VPS with Docker Compose

For deploying on any virtual private server (DigitalOcean Droplet, AWS EC2, Linode, Hetzner, or local server):

```bash
# 1. Clone repository on server
git clone https://github.com/ayushdwivedi230/-E-COMMERCE-ORDER-FULFILLMENT-ORCHESTRATOR.git
cd -E-COMMERCE-ORDER-FULFILLMENT-ORCHESTRATOR

# 2. Build and run all services in background
docker compose up -d --build

# 3. Check logs and container health
docker compose ps
docker compose logs -f
```

Services exposed:
- **Frontend Dashboard:** `http://<YOUR_SERVER_IP>:5173`
- **FastAPI Backend:** `http://<YOUR_SERVER_IP>:8000`
- **PostgreSQL Database:** Port `5432`
- **Auto-Seed:** Database tables and initial sample data seed automatically on startup.
