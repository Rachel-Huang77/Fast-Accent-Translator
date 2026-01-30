# Fast Accent Translator – Installation & Run Guide

## 1. Overview

Fast Accent Translator is a full-stack system for:

- **Real-time accent conversion** (e.g. American ↔ Indian English, etc.)
- **Live subtitles** powered by speech recognition and LLMs
- **License key–based access control** (free vs paid model)
- **Admin dashboard** for user management and bulk key generation

The project consists of:

- **Backend**: FastAPI + PostgreSQL + Tortoise ORM + ASR/TTS/diarization
- **Frontend**: React + Vite, served via Nginx in Docker
- **Database**: PostgreSQL (`fat`)

This document explains how to:

1. Prepare environment and models
2. Run with **Docker (CPU-only, recommended for demo)**
3. Run **locally without Docker** (for development or GPU usage)

## 2. Repository Structure (simplified)

```
capstone-project-25t3-9900-h13c_donut/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/routers/        # FastAPI route handlers
│  │  ├─ core/                  # DB, security, bootstrap, etc.
│  │  ├─ models/                # ORM models + TTS models folder
│  │  │  ├─ tts_models/
│  │  │  │  ├─ EN/              # English TTS model (not in repo)
│  │  │  │  └─ ZH/              # Chinese TTS model (not in repo)
│  │  ├─ schemas/               # Pydantic schemas
│  │  └─ services/              # ASR, diarization, MeloTTS, etc.
│  ├─ Dockerfile                # Backend Dockerfile (CPU, CUDA-enabled base)
│  ├─ .dockerignore
│  ├─ requirements.txt
│  └─ ...
├─ frontend/
│  ├─ src/                      # React code
│  ├─ Dockerfile                # Frontend Dockerfile (Nginx)
│  └─ ...
├─ docker-compose.yml           # Multi-container orchestration
└─ ...
```

## 3. Prerequisites

### 3.1 Common

- **Git**
- **Docker Desktop** (Windows / macOS) or Docker Engine (Linux)
- **OneDrive access** to download the TTS models
- A machine with sufficient disk space (17-20 GB)

### 3.2 For Local Development (If you are using Docker, please ignore this)

- **Python 3.11** (conda or venv)
- **PostgreSQL** (we use a database named `fat`)
- Optional for GPU experiments:
  - **NVIDIA GPU + CUDA 11.8** compatible drivers

## 4. Running with Docker (CPU-Only)

> In our final submission, **Docker is configured to run purely on CPU**.
>  The backend image uses a CUDA-enabled base image, but by default it will fall back to CPU when no GPU is available / passed through.

### 4.1 Environment files for Docker

There are two typical ways the evaluator may obtain the code:

1. **From GitHub clone**
2. **From the submitted ZIP archive**

We treat them slightly differently for `.env.docker`:

#### Case A – Clone from GitHub

1. Clone the repo:

   ```
   git clone https://github.com/unsw-cse-comp99-3900/capstone-project-25t3-9900-h13c_donut.git
   cd capstone-project-25t3-9900-h13c_donut
   ```

2. In the **backend directory****, create a file named **.env.docker**.

3. Fill in required environment variables (database URL, JWT secret, OpenAI key, ElevenLabs key, etc.).

   - For security reasons, **we do not commit .env.docker to GitHub**.
   - A **sample .env.docker** is included in the **submitted ZIP** and can be copied here.For detailed information, please refer to the installation manual.
   

> In the **ZIP submission**, `.env.docker` is already included.
>  When running from the ZIP, you can directly use that file (or tweak values if needed).

### 4.2 TTS Models (Docker + Local)

The TTS models (for EN / ZH) are  not stored in the repository due to size.
 We provide a **OneDrive link** separately; after downloading, please place them as:

OneDrive link：

```
https://unsw-my.sharepoint.com/:u:/g/personal/z5611460_ad_unsw_edu_au/EXAAZKr4HJhMvN5XR4EypUwBSyvrPaiCgblShWi8PAWJZw?e=j2EjpH
```

```
backend/app/models/tts_models/
├─ EN/
│  ├─ checkpoint.pth
│  └─ config.json
└─ ZH/
   ├─ checkpoint.pth
   ├─ config.json
```

For Docker, this folder is mounted into the backend container as a **read-only volume**, so the image itself stays smaller and decoupled from the large model files.

## 5. Docker Compose – CPU Demo (One-Command Run)

From the **project root**:

```
docker compose up --build
```

What this does:

- **Build & run postgres (DB)**
- **Build & run backend (FastAPI, CPU)**
- **Build & run frontend (React static build served by Nginx)**

Services and ports (default):

- **Backend**: `http://localhost:8000` (FastAPI, OpenAPI docs at `/docs`)
- **Frontend**: `http://localhost:5173` (user interface)

> Note:
>
> - Compose uses **.env.docker** from the repo root.
> - No GPU flags are configured in `docker-compose.yml` — the backend always runs in CPU mode when using Docker.

To stop everything:

```
docker compose down
```

If you also want to remove named volumes (including DB data):

```
docker compose down -v
```

## 6. First Run Notes (Important)

The very first time you build and run the system, it usually takes **25–30 minutes** to complete,Please wait patiently:

1. **During startup**
    Wait until the backend outputs the message:

   ```
   fat-backend   | Application startup complete.
   ```

   Once you see this line, the system is ready.

2. **First use of the Free (CPU) Speech Model**
    The very first invocation of speech recording (microphone icon) will trigger the loading of the free ASR/TTS models.
    This loading step can take **a few seconds up to a few minutes**, depending on your CPU performance,Please wait patiently.

   **Recommended usage for the first time:**

   - Click the **microphone button**
   - Speak **one short sentence**
   - Wait until you hear the voice finish playing
   - Click the microphone button again to stop recording

3. After the first successful inference, the models are cached and subsequent interactions will be fast and smooth.

## 7. Running Without Docker (Local Dev & GPU Option)

This section is for **developers** or evaluators who prefer running everything locally, e.g. to debug, or to use GPU directly in Python (without Docker overhead).

### 7.1 Backend + Database (Local)

#### 7.1.1 Create PostgreSQL database `fat`

1. Start your local PostgreSQL server.

2. Connect as `postgres` (or another superuser), then:

   ```
   CREATE DATABASE fat;
   ```

#### 7.1.2 Setup backend virtual environment

From `backend/`:

```
cd backend
conda create -n fat-backend python=3.11 -y    # or use venv
conda activate fat-backend
pip install -r requirements.txt
```

#### 7.1.3 Environment file `.env` (local only)

In `backend/`, create a **.env** file with your local configuration (DB URL, JWT secret, API keys, etc.).

> Important:
>
> - **.env is not included in the ZIP or GitHub repo**.
>
> - For security reasons, you must manually create it.
>
> - The content is similar in structure to `.env.docker`, but with local DB host/port.
>
>   ```
>   Only need to modify 
>   DATABASE_URL=postgres://postgres:postgre@fat-db:5432/fat
>   to
>   DATABASE_URL=postgres://postgres:postgre@127.0.0.1:5432/fat
>   ```

#### 7.1.4 Initial database migration (no `migrations/` folder)

In the final submission, we **remove the migrations/ folder** to keep the project clean, so the **first run** must:

1. Initialize DB schema with `aerich init-db`
2. Then just start the backend; no manual `aerich upgrade` is needed (tables will be created according to current models)

Commands:

```
cd backend
aerich init-db
```

This will:

- Create required tables (including `users`, `license_keys`, etc.) in database `fat`
- Initialize Aerich internal tables

After that, start the backend:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On first startup:

- The backend runs DB bootstrap (e.g. create default admin if not present)
- MeloTTS / ASR components are lazily loaded as needed

If you later change models and want to manage migrations manually, you can reintroduce the `migrations/` folder and use `aerich migrate / upgrade`, but for the **submitted version** the simple `aerich init-db` is sufficient.

### 7.2 Frontend (Local)

From `frontend/`:

```
cd frontend
npm install
npm run dev
```

By default this runs on `http://localhost:5173`.

### 7.3 Optional: Use GPU for Backend (Local Only)

For the **submitted Docker setup**, we **do not recommend** enabling GPU inside containers:

- GPU Docker images are very large (Uses more than 25 GB of disk space)
- Image builds are much slower (More than two hours)
- Configuration is more fragile (driver versions, `--gpus` flags, CUDA compatibility, etc.)

Instead, if you have an NVIDIA GPU and want to speed up TTS / diarization locally, we suggest:

1. Use the **local backend** (Section 7.1).

2. In your **local Python environment**, install CUDA-enabled PyTorch wheels:

   ```
   pip install "torch==2.1.2+cu118" "torchaudio==2.1.2+cu118" \
     --index-url https://download.pytorch.org/whl/cu118
   ```

3. Make sure your NVIDIA drivers + CUDA runtime support **CUDA 11.8**.

4. Start the backend as usual:

   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

Runtime behaviour:

- At startup, the backend will check whether CUDA is available (`torch.cuda.is_available()`).
- If **GPU is available**, heavy components (e.g. TTS models, diarization) will log that they are using **CUDA**.
- If no GPU is available, the same code path automatically falls back to **CPU**, so the system still runs (just slower).

**Why we recommend GPU only for local dev, not Docker:**

- For evaluators, a **CPU-only Docker setup is simpler and more reliable**:
  - `docker compose up --build` is enough to run everything.
  - No need to worry about GPU drivers, CUDA versions, or Docker’s GPU configuration.
- For power users, **local Python + GPU** is easy to tune:
  - You control the exact PyTorch wheel and CUDA version.
  - You can quickly iterate without rebuilding large Docker images.

# Testing

> **For detailed testing instructions, see [TESTING.md](TESTING.md)**

The [TESTING.md](TESTING.md) guide provides comprehensive instructions on:

- How to run frontend and backend tests
- How to view coverage reports
- Test structure and organization
- Manual system testing scenarios
- Troubleshooting common issues

------

## Summary of What is Tested

Overall, automated tests cover roughly 50–60% of the frontend and backend codebase, with core
routers and service modules typically above 70–90% coverage. Heavily I/O-bound and
browser-specific parts are covered via manual system tests instead of full automation.

**Backend – what is covered**

- Authentication flows  
  - Register, login, and `whoami` endpoints  
  - Password hashing and token verification logic
- Conversation management  
  - Create, list, get details, and delete conversations  
  - Per-user data isolation (users cannot access others’ conversations)
- Admin features  
  - Admin-only endpoints with role-based access control
- Service layer logic  
  - ASR service factory and OpenAI ASR adapter (mocked external API)  
  - Hallucination detection rules (repetition, low confidence, noise)  
  - GPT formatter fallback and sentence splitting  
  - Basic diarization matching between timestamps and speaker IDs
- Infrastructure  
  - Pub/sub channel used by WebSocket text/TTS  
  - Database initialisation using a dedicated test SQLite database
- Race conditions and concurrency  
  - Concurrent conversation creation, updates, and deletions  
  - Concurrent segment appends to the same conversation  
  - Concurrent mixed operations (read, update, append)  
  - Concurrent user isolation and access control  
  - Race condition detection (e.g., sequence number calculation in segment appends)

**Backend – partial / manual coverage**

- Full streaming audio pipeline in `ws_upload.py`  
  - Control messages (`start` / `stop`) and basic error paths are tested via lightweight WebSocket tests  
  - End-to-end audio → ASR → diarization → database → transcript refresh is validated via manual system tests
- `tts_elevenlabs.py`  
  - Core logic is exercised indirectly through the `/api/v1/tts/synthesize` endpoint with TTS backends mocked  
  - Real external calls to ElevenLabs are verified manually (see System / End-to-end Testing)

> **For detailed feature-to-test mapping and other testing information, see [TESTING_BE.md](tests/backend/TESTING_BE.MD)**

------

**Frontend – what is covered**

- Auth pages and flows  
  - Login / register / forgot password components and user interactions  
  - Form validation and error messaging
- Shared components and utilities  
  - Reusable UI components (buttons, forms, layout)  
  - Utility functions (text helpers, config handling)
- Admin page  
  - Rendering and basic management interactions
- Dashboard (accent translator) – core behaviour  
  - Start/stop streaming button behaviour  
  - Conversation selection and title display  
  - Model/accent selector behaviour (state changes)

**Frontend – partial / manual coverage**

- Real-time audio capture, Web Speech API, and raw WebSocket streaming  
  - These are not fully automated in tests  
  - In automated tests, browser APIs and WebSocket clients are mocked; we only verify component state and UI responses  
  - Full real-time flows are covered via manual scenarios described below

> **For detailed feature-to-test mapping and other testing information, see [TESTING_FE.md](tests/frontend/TESTING_FE.md)**

------

## System / End-to-end Testing (Manual)

Some parts of the system (microphone access, the browser Web Speech API, real-time audio
streaming over WebSockets, and live calls to external ASR/TTS providers) are difficult to
fully automate in CI. For these components, we complement automated tests with manual
end-to-end scenarios.

#### Test environment

- Browser: Chrome (latest stable version)
- Backend: FastAPI dev server (`uvicorn app.main:app --reload`)
- Frontend: React dev server (`npm run dev`)
- External services:
  - OpenAI Whisper / GPT (valid API key)
  - ElevenLabs TTS (for paid model tests)
  - Local MeloTTS (for free model tests)

#### E2E Test Scenarios

#### 1. Basic login + Dashboard access

- **Steps**
  1. Start backend and frontend dev servers.
  2. Open the app in Chrome and navigate to the login page.
  3. Log in with a valid user.
  4. Navigate to the Dashboard.
- **Expected**
  - Login succeeds and a JWT is stored.
  - Dashboard loads the conversation list (empty for a new user).
  - No backend errors appear in the logs.

#### 2. Free model: real-time accent translation

- **Steps**
  1. On the Dashboard, select model = `free` and choose an accent.
  2. Click `Start` to begin streaming.
  3. Allow microphone access when prompted.
  4. Speak a short English sentence (5–10 seconds).
  5. Click `Stop`.
- **Expected**
  - Web Speech preview shows interim and final text while speaking.
  - Short TTS segments are played back in the selected accent.
  - A new conversation appears in the list.
  - Opening the conversation shows final transcripts saved in the database.

#### 3. Paid model: TTS via ElevenLabs

- **Steps**
  1. On the Dashboard, select model = `paid` and choose another accent.
  2. Repeat the same speaking steps as in Scenario 2.
- **Expected**
  - TTS uses the configured ElevenLabs voice.
  - No unhandled server-side errors occur when calling the external API.
  - Transcripts are still stored correctly.

#### 4. Admin: role-based access control

- **Steps**
  1. Log in as a normal user and attempt to access the Admin page or `/api/v1/admin/...` routes.
  2. Log in as an admin user and access the same routes.
- **Expected**
  - Normal user receives 403 / “not authorised”.
  - Admin user can view the user list / license keys as expected.

#### 5. Error handling (network / API failures)

- **Steps**
  1. Temporarily invalidate the OpenAI/ElevenLabs API key or block network access.
  2. Start a translation session and trigger TTS / ASR.
  3. Restore the correct configuration afterwards.
- **Expected**
  - The frontend shows an error message or at least does not crash.
  - Backend logs contain a clear error for the external API failure.
  - The system recovers once the API key / network is fixed.