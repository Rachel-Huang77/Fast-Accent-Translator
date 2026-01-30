# app/main.py
import torch
import os
import shutil
import logging
from pathlib import Path
from glob import glob

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Your configuration and DB
from app.config import settings
from app.core.db import init_db, close_db

from app.api.v1.routers import auth, accents, session as session_router, conversations, admin, tts


from app.api.v1.routers.ws_text import router as ws_text_router
from app.api.v1.routers.ws_upload import router as ws_upload_router
from app.api.v1.routers.ws_tts import router as ws_tts_router

from app.core.bootstrap import ensure_default_admin
logger = logging.getLogger("uvicorn.error")

def _ensure_ffmpeg_on_path() -> None:
    """
    Goal: Don't hardcode absolute paths; automatically add common installation directories to PATH at startup.
    Priority:
      1) Environment variables FFMPEG_DIR / FFPROBE_DIR (can be configured as directory, not exe)
      2) winget common installation directories (Gyan.FFmpeg)
      3) Chocolatey common installation directories
      4) Program Files common installation directories
    After finding, prepend its bin directory to os.environ['PATH'], then check which(ffmpeg).
    """
    # Skip if already available
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        logger.info("[ffmpeg] found on PATH: ffmpeg=%s ffprobe=%s",
                    shutil.which("ffmpeg"), shutil.which("ffprobe"))
        return

    candidates: list[Path] = []

    # 1) Explicit directory (team can configure FFMPEG_DIR / FFPROBE_DIR in .env)
    ffmpeg_dir = os.getenv("FFMPEG_DIR")
    ffprobe_dir = os.getenv("FFPROBE_DIR")
    if ffmpeg_dir:
        p = Path(ffmpeg_dir)
        candidates.append(p if p.name.lower() == "bin" else p / "bin")
    if ffprobe_dir:
        p = Path(ffprobe_dir)
        candidates.append(p if p.name.lower() == "bin" else p / "bin")

    # 2) winget path (typical structure for Gyan.FFmpeg)
    local = os.getenv("LOCALAPPDATA", "")
    if local:
        winget_root = Path(local) / "Microsoft" / "WinGet" / "Packages"
        # Example: .../Gyan.FFmpeg_8.0.0.0_x64__xxx/ffmpeg-8.0-full_build/bin
        for pkg_dir in winget_root.glob("Gyan.FFmpeg_*"):
            for ff_root in pkg_dir.glob("ffmpeg-*"):
                candidates.append(ff_root / "bin")

    # 3) Chocolatey
    candidates += [
        Path(r"C:\ProgramData\chocolatey\bin"),
        Path(r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin"),
    ]

    # 4) Program Files classic installation
    candidates += [
        Path(r"C:\Program Files\ffmpeg\bin"),
        Path(r"C:\Program Files (x86)\ffmpeg\bin"),
    ]

    # Add to PATH (add if directory exists and contains ffmpeg.exe)
    added = []
    for c in candidates:
        try:
            if c.is_dir() and (c / "ffmpeg.exe").exists():
                # Prepend to ensure priority
                os.environ["PATH"] = str(c) + os.pathsep + os.environ.get("PATH", "")
                added.append(str(c))
        except Exception:
            pass

    logger.info("[ffmpeg] PATH extended by: %s", added if added else "[]")
    logger.info("[ffmpeg] which(ffmpeg)=%s", shutil.which("ffmpeg"))
    logger.info("[ffmpeg] which(ffprobe)=%s", shutil.which("ffprobe"))

app = FastAPI(title=settings.APP_NAME)

# CORS (with Cookie)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # First ensure ffmpeg is in PATH (prepare for ASR transcoding)
    _ensure_ffmpeg_on_path()
    # Check if CUDA is available
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"[CUDA] GPU acceleration is enabled: {device_name}")
    else:
        logger.warning("[CUDA] Currently using CPU mode (GPU not detected)）")
    # Your DB initialization
    await init_db()
    # Ensure there's a default admin account on first run
    await ensure_default_admin()

@app.on_event("shutdown")
async def on_shutdown():
    await close_db()

# REST
app.include_router(auth.router, prefix="/api/v1")
app.include_router(accents.router, prefix="/api/v1")
app.include_router(session_router.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(tts.router, prefix="/api/v1/tts", tags=["TTS"])  # ✅ Streaming translation TTS API

# WebSocket (keep original decorator paths)
app.include_router(ws_text_router)
app.include_router(ws_upload_router)
app.include_router(ws_tts_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
