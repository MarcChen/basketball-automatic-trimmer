import math
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

from models.schemas import TrimParams

# Path to the pose landmarker model file
MODEL_PATH = str(Path(__file__).resolve().parent.parent / "pose_landmarker_lite.task")


def compute_activity_score(current_landmarks, previous_landmarks) -> float:
    total_distance = 0.0
    count = 0
    for curr, prev in zip(current_landmarks, previous_landmarks):
        dx = curr.x - prev.x
        dy = curr.y - prev.y
        total_distance += math.sqrt(dx * dx + dy * dy)
        count += 1
    return total_distance / count if count > 0 else 0.0


def merge_segments(active_frames: list[int], fps: float) -> list[tuple[float, float]]:
    if not active_frames:
        return []

    segments = []
    start = active_frames[0]
    prev = active_frames[0]

    for frame in active_frames[1:]:
        if frame != prev + 1:
            segments.append((start / fps, prev / fps))
            start = frame
        prev = frame

    segments.append((start / fps, prev / fps))
    return segments


def apply_buffer_and_filter(
    segments: list[tuple[float, float]],
    buffer_seconds: float,
    min_segment_duration: float,
    video_duration: float,
) -> list[tuple[float, float]]:
    buffered = []
    for start, end in segments:
        buffered_start = max(0.0, start - buffer_seconds)
        buffered_end = min(video_duration, end + buffer_seconds)
        buffered.append((buffered_start, buffered_end))

    buffered.sort(key=lambda s: s[0])

    merged = []
    for seg in buffered:
        if merged and seg[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], seg[1]))
        else:
            merged.append(seg)

    return [(s, e) for s, e in merged if (e - s) >= min_segment_duration]


def split_long_segments(
    segments: list[tuple[float, float]], max_duration: float
) -> list[tuple[float, float]]:
    """Split any segment longer than max_duration into sequential chunks."""
    result = []
    for start, end in segments:
        duration = end - start
        if duration <= max_duration:
            result.append((start, end))
        else:
            curr = start
            while curr < end:
                chunk_end = min(curr + max_duration, end)
                result.append((round(curr, 2), round(chunk_end, 2)))
                curr = chunk_end
    return result


def analyze_video(
    video_path: str,
    params: TrimParams,
    progress_callback: callable,
) -> list[tuple[float, float]]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 0.0

    # Configure PoseLandmarker with the new Tasks API
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        min_pose_detection_confidence=params.min_detection_confidence,
        min_tracking_confidence=params.min_tracking_confidence,
        num_poses=1,
    )

    landmarker = PoseLandmarker.create_from_options(options)

    active_frames: list[int] = []
    previous_landmarks = None
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create a MediaPipe Image from the numpy array
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Calculate timestamp in milliseconds for VIDEO mode
        timestamp_ms = int(frame_index * 1000 / fps) if fps > 0 else frame_index

        results = landmarker.detect_for_video(mp_image, timestamp_ms)

        activity_score = 0.0
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            current_landmarks = results.pose_landmarks[0]  # First detected pose
            if previous_landmarks is not None:
                activity_score = compute_activity_score(current_landmarks, previous_landmarks)
            previous_landmarks = current_landmarks
        else:
            previous_landmarks = None

        if activity_score > params.activity_threshold:
            active_frames.append(frame_index)

        if frame_index % 30 == 0 and total_frames > 0:
            progress_callback(int(frame_index / total_frames * 100))

        frame_index += 1

    cap.release()
    landmarker.close()
    progress_callback(100)

    raw_segments = merge_segments(active_frames, fps)
    filtered = apply_buffer_and_filter(raw_segments, params.buffer_seconds, params.min_segment_duration, video_duration)
    return split_long_segments(filtered, params.max_clip_duration)
