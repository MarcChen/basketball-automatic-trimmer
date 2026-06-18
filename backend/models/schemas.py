from pydantic import BaseModel, Field


class VideoMeta(BaseModel):
    filename: str
    path: str
    size_mb: float
    duration_seconds: float
    fps: float
    resolution: str  # e.g. "1920x1080"
    thumbnail_url: str  # served as /thumbnails/{filename}.jpg


class TrimParams(BaseModel):
    video_filename: str
    activity_threshold: float = Field(
        default=0.015, ge=0.001, le=0.5, description="Landmark velocity delta to classify frame as active"
    )
    min_segment_duration: float = Field(
        default=2.0, ge=0.5, le=30.0, description="Minimum clip length in seconds to keep"
    )
    buffer_seconds: float = Field(
        default=1.5, ge=0.0, le=10.0, description="Seconds of context to add before/after each active segment"
    )
    min_detection_confidence: float = Field(default=0.5, ge=0.1, le=1.0)
    min_tracking_confidence: float = Field(default=0.5, ge=0.1, le=1.0)
    max_clip_duration: float = Field(
        default=300.0, ge=10.0, le=1800.0, description="Maximum output clip duration in seconds"
    )


class TrimJob(BaseModel):
    job_id: str
    video_filename: str
    status: str  # "queued" | "processing" | "done" | "error"
    progress_pct: int = 0  # 0-100
    segments_found: int = 0
    clips_exported: list[str] = []
    error_message: str | None = None


class OutputClip(BaseModel):
    filename: str
    source_video: str
    start_time: float
    end_time: float
    duration: float
    size_mb: float
    url: str  # served as /output/{filename}
