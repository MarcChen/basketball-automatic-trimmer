import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from models.schemas import OutputClip, TrimJob, TrimParams, VideoMeta
from services.clip_exporter import export_clips
from services.pose_detector import analyze_video
from services.video_scanner import scan_videos

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
THUMBNAILS_DIR = BASE_DIR / ".thumbnails"

app = FastAPI(title="Basketball Video Trimmer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

jobs: dict[str, TrimJob] = {}
executor = ThreadPoolExecutor(max_workers=2)


def _safe_filename(filename: str) -> str:
    """Sanitise a filename to prevent path-traversal attacks."""
    sanitized = PurePosixPath(filename).name
    if not sanitized or sanitized in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return sanitized


@app.get("/videos", response_model=list[VideoMeta])
async def get_videos():
    try:
        return scan_videos(str(DATA_DIR), str(THUMBNAILS_DIR))
    except Exception as e:
        logger.exception("Failed to scan videos")
        raise HTTPException(status_code=500, detail=f"Failed to scan videos: {e}")


@app.get("/thumbnails/{filename}")
async def get_thumbnail(filename: str):
    filename = _safe_filename(filename)
    thumbnail_path = THUMBNAILS_DIR / filename
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(str(thumbnail_path), media_type="image/jpeg")


@app.get("/videos/stream/{filename}")
async def stream_video(filename: str):
    """Serve a video file from data/ for frontend preview."""
    filename = _safe_filename(filename)
    video_path = DATA_DIR / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(str(video_path), media_type="video/mp4")


@app.post("/trim", response_model=TrimJob)
async def start_trim(params: TrimParams):
    safe_name = _safe_filename(params.video_filename)
    video_path = DATA_DIR / safe_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {safe_name}")

    job_id = str(uuid.uuid4())
    job = TrimJob(
        job_id=job_id,
        video_filename=safe_name,
        status="queued",
    )
    jobs[job_id] = job

    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_trim_job, job_id, str(video_path), params)

    return job


def _run_trim_job(job_id: str, video_path: str, params: TrimParams):
    job = jobs[job_id]
    job.status = "processing"

    try:

        def progress_callback(pct: int):
            job.progress_pct = pct

        segments = analyze_video(video_path, params, progress_callback)
        job.segments_found = len(segments)

        if segments:
            clips = export_clips(
                video_path,
                segments,
                str(OUTPUT_DIR),
                params.video_filename,
            )
            job.clips_exported = [c.filename for c in clips]

        job.status = "done"
        job.progress_pct = 100
    except Exception as e:
        logger.exception("Trim job failed: %s", job_id)
        job.status = "error"
        job.error_message = str(e)


@app.get("/jobs/{job_id}", response_model=TrimJob)
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/output", response_model=list[OutputClip])
async def get_output():
    clips = []
    for file_path in sorted(OUTPUT_DIR.glob("*.mp4")):
        size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

        source_video = "unknown"
        start_time = 0.0
        end_time = 0.0
        duration = 0.0

        parts = file_path.stem.split("_clip_")
        if len(parts) == 2:
            source_video = parts[0] + ".mp4"
            time_part = parts[1].split("_", 1)[-1] if "_" in parts[1] else parts[1]
            time_part = time_part.replace("s", "")
            if "-" in time_part:
                start_str, end_str = time_part.split("-")
                try:
                    start_time = float(start_str)
                    end_time = float(end_str)
                    duration = round(end_time - start_time, 2)
                except ValueError:
                    pass

        clips.append(
            OutputClip(
                filename=file_path.name,
                source_video=source_video,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                size_mb=size_mb,
                url=f"/output/{file_path.name}",
            )
        )

    return clips


@app.get("/output/{filename}")
async def get_output_file(filename: str):
    filename = _safe_filename(filename)
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(str(file_path), media_type="video/mp4")


@app.delete("/output/{filename}")
async def delete_output_file(filename: str):
    filename = _safe_filename(filename)
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    file_path.unlink()
    return {"detail": f"Deleted {filename}"}


@app.get("/socket.io/")
@app.post("/socket.io/")
async def socket_io_stub():
    """Silently handle socket.io polling from browser extensions (Vue DevTools, etc.)."""
    return {"error": "socket.io not supported"}

