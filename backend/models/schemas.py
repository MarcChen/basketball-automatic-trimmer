from pydantic import BaseModel, Field


class VideoMeta(BaseModel):
    filename: str
    path: str
    size_mb: float
    duration_seconds: float
    fps: float
    resolution: str  # e.g. "1920x1080"
    thumbnail_url: str  # served as /thumbnails/{filename}.jpg


class HoopCalibration(BaseModel):
    """Hoop position calibration for a specific video frame.

    Coordinates are in original video pixel space (e.g. 1920x1080).
    The scoring zone is a circle centered at (hoop_x, hoop_y) with radius hoop_radius.
    Near-miss zone extends to radius * near_miss_multiplier.
    """
    video_filename: str
    frame_number: int = Field(ge=0, description="Frame index used for calibration")
    hoop_x: float = Field(ge=0, description="Hoop center X in video pixels")
    hoop_y: float = Field(ge=0, description="Hoop center Y in video pixels")
    hoop_radius: float = Field(gt=0, description="Scoring zone radius in video pixels")


class TrimParams(BaseModel):
    """Parameters for ball & hoop detection based video trimming.

    Replaces the old pose-activity params entirely. Detection runs YOLOv8
    on each frame to locate the basketball, then classifies score / near-miss
    events using the ball trajectory relative to the calibrated hoop position.
    Clips are anchored to events with asymmetric pre/post roll buffers.
    """
    video_filename: str
    hoop_x: float | None = Field(default=None, ge=0, description="Hoop center X in pixels (from calibration)")
    hoop_y: float | None = Field(default=None, ge=0, description="Hoop center Y in pixels (from calibration)")
    hoop_radius: float | None = Field(default=None, gt=0, description="Scoring zone radius in pixels")
    yolo_confidence: float = Field(
        default=0.4, ge=0.1, le=1.0,
        description="Minimum YOLO confidence for ball detection"
    )
    near_miss_multiplier: float = Field(
        default=1.3, ge=1.0, le=3.0,
        description="Near-miss zone = hoop_radius * this value"
    )
    pre_roll_seconds: float = Field(
        default=3.0, ge=0.0, le=15.0,
        description="Seconds of context to include before each event"
    )
    post_roll_seconds: float = Field(
        default=2.0, ge=0.0, le=15.0,
        description="Seconds of context to include after each event"
    )
    min_segment_duration: float = Field(
        default=1.5, ge=0.5, le=30.0,
        description="Clips shorter than this are discarded"
    )
    max_clip_duration: float = Field(
        default=30.0, ge=5.0, le=600.0,
        description="Clips longer than this are split into sequential chunks"
    )
    include_near_misses: bool = Field(
        default=True,
        description="If True, near-miss events produce clips; if False, only scores"
    )


class TrimJob(BaseModel):
    job_id: str
    video_filename: str
    status: str  # "queued" | "processing" | "done" | "error"
    progress_pct: int = 0  # 0-100
    segments_found: int = 0
    scores_found: int = 0
    near_misses_found: int = 0
    clips_exported: list[str] = []
    error_message: str | None = None


class OutputClip(BaseModel):
    filename: str
    source_video: str
    start_time: float
    end_time: float
    duration: float
    size_mb: float
    event_type: str = "score"  # "score" | "near_miss"
    url: str  # served as /output/{filename}
