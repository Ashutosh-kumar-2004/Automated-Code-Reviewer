# SecureAgent — Autonomous Code Reviewer & Security Remediator 🛡️🤖

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-3.6--flash-orange?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SecureAgent** is an autonomous AI-powered security code review and remediation platform. It connects directly with GitHub repositories, detects security vulnerabilities using static analysis (Semgrep SAST), computes actionable security scores, enriches findings using **Google Gemini AI**, generates one-click Pull Requests with tested remediation patches, and alerts developers via an autonomous **Remediator Notification Agent**.

---

## 📑 Table of Contents
- [Architecture & Design](#-architecture--design)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Monorepo Structure](#-monorepo-structure)
- [Getting Started Locally](#-getting-started-locally)
  - [Prerequisites](#prerequisites)
  - [Backend Setup (FastAPI)](#1-backend-setup-fastapi)
  - [Frontend Setup (Next.js)](#2-frontend-setup-nextjs)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Deployment](#-deployment)
  - [Frontend on Vercel](#deploy-frontend-on-vercel)
  - [Backend on Render](#deploy-backend-on-render)
  - [Production Database (Turso / PostgreSQL)](#production-database-turso--postgresql)
- [Contributing & License](#-contributing--license)

---

## 🏗️ Architecture & Design

SecureAgent follows a modern **Backend-for-Frontend (BFF)** architecture:
- The browser **never** communicates directly with FastAPI.
- All frontend interactions flow through Next.js Route Handlers.
- Next.js mints short-lived server-side **HS256 JWTs** signed with a shared backend secret to securely proxy requests to FastAPI.
- Sensitive GitHub OAuth access tokens are encrypted at rest using **Fernet (AES-128-CBC)**.

```mermaid
graph TD
    User([User Browser]) <-->|Session Cookie / HTTP-only| NextApp[Next.js 16 Frontend / BFF]
    NextApp <-->|NextAuth v5| GitHubOAuth[GitHub OAuth API]
    NextApp <-->|BFF Proxy + Server-Side JWT| FastAPIServer[FastAPI Backend :8000]
    
    subgraph FastAPI Backend Core
        FastAPIServer --> AuthMiddleware[HS256 Auth & Rate Limiter]
        FastAPIServer --> ScanRunner[Scan Runner Service]
        FastAPIServer --> GeminiAI[Google Gemini 3.6-Flash API]
        FastAPIServer --> Remediator[Remediator Notification Engine]
        FastAPIServer --> DB[(Database: SQLite / Turso / Postgres)]
    end

    subgraph Autonomous Analysis Agent
        ScanRunner --> IngestNode[Ingest Node: Clone & Detect Env]
        IngestNode --> SemgrepScanner[Semgrep SAST Scanner Engine]
        SemgrepScanner --> Normalizer[Deterministic SHA-256 Fingerprinter]
        Normalizer --> ScoringNode[Security Score Formula Engine]
    end

    FastAPIServer -->|SSE Live Stream| NextApp
    FastAPIServer -->|Create Pull Request| GitHubRepo[GitHub Repositories]
```

---

## ✨ Key Features

1. **Autonomous SAST Scanner:**
   - Multi-language AST security rule detection powered by **Semgrep**.
   - Language & test framework auto-detection (Python, JavaScript, TypeScript, Go).
   - Deterministic whitespace-invariant SHA-256 finding fingerprinting.

2. **Google Gemini AI Fix Engine:**
   - On-demand AI vulnerability analysis and patch suggestions (`gemini-3.6-flash`).
   - Structured remediation advice: root cause explanation, security impact, safe replacement code snippet, and best-practice coding style.
   - Built-in heuristic fallback engine ensuring 100% reliability even under high LLM API demand.

3. **Automated GitHub Pull Requests:**
   - Directly creates remediation branches and opens comprehensive Pull Requests on GitHub.
   - Live PR status sync: automatically checks when PRs are reviewed and merged.

4. **Security Audit Reports:**
   - Full security compliance reports across all findings, CWE IDs, and OWASP Top 10 categories.
   - One-click export to formatted **Markdown** or structured **JSON**.

5. **Autonomous Remediator Notification Agent:**
   - Periodically evaluates all connected repositories for open security vulnerabilities.
   - Cadence is managed via `REMEDIATION_NOTIFICATION_INTERVAL_MINUTES` (defaults to 1 hour).
   - Interactive UI modal alert displaying severity breakdowns, affected repositories, urgent findings preview, and one-click actions ("Fix with Gemini AI", "Create PR", "Snooze").

6. **Dual Database Architecture:**
   - **Local Machine:** Zero-configuration local SQLite (`secureagent.db`).
   - **Cloud Production:** Seamless cloud integration with **Turso (libSQL)** or **PostgreSQL** (Render, Neon, Supabase) with automatic URL normalization.

---

## 💻 Tech Stack

### Frontend
- **Framework:** [Next.js 16](https://nextjs.org/) (App Router, React 19)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/), Radix UI Primitives, Lucide Icons
- **Authentication:** [NextAuth v5](https://authjs.dev/) (Auth.js) with GitHub Provider
- **State & Streaming:** Real-time Server-Sent Events (SSE) proxy streaming

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- **ORM & DB:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async Engine) + aiosqlite / asyncpg
- **Security Scanners:** Semgrep CLI + Custom SAST Rules Engine
- **LLM Integration:** Google Generative AI (Gemini 3.6 Flash)
- **Security & Rate Limiting:** Python-Jose (HS256 JWTs), Cryptography (Fernet AES), SlowAPI

---

## 📁 Monorepo Structure

```
├── secureagent/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── models/           # SQLAlchemy ORM models (User, Scan, Finding, PR, etc.)
│   │   │   ├── routers/          # FastAPI routers (auth, repos, scans, findings, prs, reports, notifications)
│   │   │   ├── schemas/          # Pydantic request & response validation schemas
│   │   │   ├── services/         # GitHub API client, Crypto, Scan Runner service
│   │   │   ├── middleware/       # JWT BFF Auth & Rate Limiting
│   │   │   ├── config.py         # Pydantic Settings & environment variables
│   │   │   ├── database.py       # Async SQLAlchemy session factory & cloud DB normalizer
│   │   │   └── main.py           # FastAPI entrypoint
│   │   ├── tests/                # Pytest unit & integration test suites
│   │   └── requirements.txt      # Python dependencies
│   │
│   ├── frontend/
│   │   ├── app/
│   │   │   ├── (auth)/login/     # GitHub OAuth Sign-In page
│   │   │   ├── dashboard/        # Security overview & metric widgets
│   │   │   ├── repos/            # Connected repository management & scans
│   │   │   ├── findings/         # Vulnerabilities triage & Gemini AI suggestions
│   │   │   ├── pull-requests/    # Autonomous PR generation & tracking
│   │   │   ├── reports/          # Audit reports & export
│   │   │   └── api/              # Next.js BFF Route Handlers (JWT minting & proxy)
│   │   ├── components/           # UI components, layout (TopBar, Sidebar), modals
│   │   └── lib/                  # NextAuth, BFF client, proxy utility
│   │
│   └── agent/                    # Autonomous SAST scanner nodes & AST normalizer
│
├── render.yaml                   # Render Blueprint for automated backend deployment
├── vercel.json                   # Vercel configuration for frontend
└── .gitignore                    # Master gitignore
```

---

## 🚀 Getting Started Locally

### Prerequisites
- **Python 3.11+** installed
- **Node.js 18+** & `npm` installed
- A **GitHub OAuth Application** (create one in [GitHub Developer Settings](https://github.com/settings/developers)):
  - **Homepage URL:** `http://localhost:3000`
  - **Authorization callback URL:** `http://localhost:3000/api/auth/callback/github`

---

### 1. Backend Setup (FastAPI)

```bash
cd secureagent/backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
copy ..\.env.example .env   # Windows
# or: cp ../.env.example .env # Linux/macOS
```

Fill in your secrets in `secureagent/backend/.env`:
```ini
DATABASE_URL=sqlite+aiosqlite:///./secureagent.db
BACKEND_SECRET=a_secure_shared_hs256_secret_key_32chars!
ENCRYPTION_KEY=<generated_fernet_key>
FRONTEND_URL=http://localhost:3000
GITHUB_CLIENT_ID=<your_github_client_id>
GITHUB_CLIENT_SECRET=<your_github_client_secret>
GOOGLE_API_KEY=<your_google_gemini_api_key>
REMEDIATION_NOTIFICATION_INTERVAL_MINUTES=60
```
> Generate Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

Run the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at: `http://localhost:8000` (API Docs at `http://localhost:8000/docs`).

---

### 2. Frontend Setup (Next.js)

```bash
cd secureagent/frontend

# Install dependencies
npm install

# Create .env.local
```

Create `secureagent/frontend/.env.local`:
```ini
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=a_secure_nextauth_jwt_super_secret_32chars!
GITHUB_CLIENT_ID=<your_github_client_id>
GITHUB_CLIENT_SECRET=<your_github_client_secret>
BACKEND_URL=http://localhost:8000
BACKEND_SECRET=a_secure_shared_hs256_secret_key_32chars!  # Must match backend
JWT_EXPIRY_SECONDS=600
```

Start the Next.js development server:
```bash
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser!

---

## ⚙️ Configuration & Environment Variables

| Variable | Scope | Default | Description |
| :--- | :--- | :--- | :--- |
| `BACKEND_SECRET` | Shared | *Required* | Shared HS256 key between Next.js BFF and FastAPI (min 32 chars) |
| `BACKEND_URL` | Frontend | `http://localhost:8000` | Target URL of the FastAPI backend service |
| `NEXTAUTH_URL` | Frontend | `http://localhost:3000` | Canonical URL of the Next.js web application |
| `NEXTAUTH_SECRET` | Frontend | *Required* | Secret used to encrypt NextAuth session cookies |
| `DATABASE_URL` | Backend | `sqlite+aiosqlite:///./secureagent.db` | Async SQLAlchemy database connection string |
| `TURSO_DATABASE_URL` | Backend | *(Optional)* | Turso database URL for cloud production deployment |
| `TURSO_AUTH_TOKEN` | Backend | *(Optional)* | Turso database authentication token |
| `ENCRYPTION_KEY` | Backend | *Required* | Fernet AES key to encrypt GitHub access tokens at rest |
| `FRONTEND_URL` | Backend | `http://localhost:3000` | Allowed frontend origin for CORS policies |
| `CORS_ORIGINS` | Backend | `https://*.vercel.app` | Comma-separated list of additional allowed CORS origins |
| `GOOGLE_API_KEY` | Backend | *(Optional)* | Google Gemini API key for AI fix generation (`gemini-3.6-flash`) |
| `REMEDIATION_NOTIFICATION_INTERVAL_MINUTES` | Backend | `60` | Frequency in minutes for the Remediator alert notification |

---

## 🚢 Deployment

### Deploy Frontend on Vercel
1. Import this repository into [Vercel](https://vercel.com/).
2. In **Project Settings > General**:
   - **Root Directory:** `secureagent/frontend`
   - **Framework Preset:** `Next.js`
3. Configure the environment variables on Vercel:
   - `NEXTAUTH_URL=https://your-frontend.vercel.app`
   - `NEXTAUTH_SECRET=<random 32+ char secret>`
   - `BACKEND_URL=https://your-backend.onrender.com`
   - `BACKEND_SECRET=<must match backend>`
   - `GITHUB_CLIENT_ID=<your github client id>`
   - `GITHUB_CLIENT_SECRET=<your github client secret>`

### Deploy Backend on Render
1. Create a **New Web Service** on [Render](https://render.com/) (or use Blueprint with `render.yaml`):
   - **Root Directory:** `secureagent/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. Configure the environment variables on Render:
   - `BACKEND_SECRET=<must match frontend>`
   - `ENCRYPTION_KEY=<your fernet key>`
   - `FRONTEND_URL=https://your-frontend.vercel.app`
   - `GITHUB_CLIENT_ID=<your github client id>`
   - `GITHUB_CLIENT_SECRET=<your github client secret>`
   - `GOOGLE_API_KEY=<your gemini api key>`
   - `REMEDIATION_NOTIFICATION_INTERVAL_MINUTES=60`

### Production Database (Turso / PostgreSQL)
- **Turso (libSQL Cloud):**
  Add to Render environment variables:
  ```ini
  TURSO_DATABASE_URL=libsql://your-database-name.turso.io
  TURSO_AUTH_TOKEN=your_turso_auth_token
  ```
- **PostgreSQL (Render / Neon):**
  Add to Render environment variables:
  ```ini
  DATABASE_URL=postgresql://user:password@host/dbname
  ```
  *(The backend automatically translates `postgresql://` to `postgresql+asyncpg://`)*.

---

## 🧪 Testing

Run backend tests:
```bash
cd secureagent/backend
pytest -v
```

Run frontend type check:
```bash
cd secureagent/frontend
npx tsc --noEmit
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
