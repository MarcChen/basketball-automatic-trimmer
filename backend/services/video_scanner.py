import logging
import os
from pathlib import Path

import cv2

from models.schemas import VideoMeta

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def get_video_metadata(video_path: str) -> dict | None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if fps <= 0 or frame_count <= 0:
        return None

    return {
        "fps": fps,
        "frame_count": int(frame_count),
        "duration_seconds": frame_count / fps,
        "resolution": f"{width}x{height}",
    }


def generate_thumbnail(video_path: str, thumbnail_path: str) -> bool:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return False

    target_frame = max(0, int(total_frames * 0.1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return False

    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
    return cv2.imwrite(thumbnail_path, frame)


def scan_videos(data_dir: str, thumbnails_dir: str) -> list[VideoMeta]:
    data_path = Path(data_dir)
    if not data_path.exists():
        return []

    os.makedirs(thumbnails_dir, exist_ok=True)

    videos = []
    for file_path in sorted(data_path.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        metadata = get_video_metadata(str(file_path))
        if metadata is None:
            logger.warning("Could not read video: %s", file_path)
            continue

        filename = file_path.name
        thumbnail_filename = f"{file_path.stem}.jpg"
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)

        if not os.path.exists(thumbnail_path):
            generate_thumbnail(str(file_path), thumbnail_path)

        size_bytes = file_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        videos.append(
            VideoMeta(
                filename=filename,
                path=str(file_path),
                size_mb=size_mb,
                duration_seconds=round(metadata["duration_seconds"], 2),
                fps=round(metadata["fps"], 2),
                resolution=metadata["resolution"],
                thumbnail_url=f"/thumbnails/{thumbnail_filename}",
            )
        )

    return videos
