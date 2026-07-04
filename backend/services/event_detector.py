from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from models.schemas import TrimParams
from services.ball_detector import BallDetector, BallDetection, fill_gaps, smooth_trajectory
from services.hoop_detector import auto_detect_hoop


@dataclass
class BallEvent:
    frame_index: int
    timestamp: float
    event_type: str
    hoop_x: float
    hoop_y: float
    hoop_radius: float


@dataclass
class ClipSegment:
    start_time: float
    end_time: float
    event_type: str
    event_frame: int


def _bbox_diagonal(bbox: tuple[float, float, float, float] | None) -> float:
    if bbox is None:
        return 0.0
    x1, y1, x2, y2 = bbox
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def clean_ball_detections(
    detections: list[BallDetection],
    max_jump_ratio: float = 4.0,
) -> list[BallDetection]:
    result = [BallDetection(d.frame_index, d.centroid, d.confidence, d.bbox) for d in detections]

    last_valid = None
    last_valid_idx = None

    for i, d in enumerate(result):
        if d.centroid is not None:
            if last_valid is not None and last_valid_idx is not None:
                gap = i - last_valid_idx
                if gap < 5:
                    dx = d.centroid[0] - last_valid[0]
                    dy = d.centroid[1] - last_valid[1]
                    dist = np.sqrt(dx ** 2 + dy ** 2)
                    diag = _bbox_diagonal(d.bbox)
                    if diag > 0 and dist > max_jump_ratio * diag:
                        result[i] = BallDetection(i, None, 0.0, None)
                        continue
            last_valid = d.centroid
            last_valid_idx = i

    return result


def detect_up_phase(
    detections: list[BallDetection],
    hoop_x: float,
    hoop_y: float,
    hoop_radius: float,
) -> int | None:
    x_min = hoop_x - 4 * hoop_radius
    x_max = hoop_x + 4 * hoop_radius
    y_min = hoop_y - 2 * hoop_radius
    y_threshold = hoop_y - 0.5 * hoop_radius

    for d in detections:
        if d.centroid is None:
            continue
        cx, cy = d.centroid
        if x_min < cx < x_max and y_min < cy < y_threshold:
            return d.frame_index
    return None


def detect_down_phase(
    detections: list[BallDetection],
    hoop_x: float,
    hoop_y: float,
    hoop_radius: float,
    start_after: int = 0,
) -> int | None:
    y_threshold = hoop_y + 0.5 * hoop_radius

    for d in detections:
        if d.frame_index < start_after:
            continue
        if d.centroid is None:
            continue
        cx, cy = d.centroid
        if cy > y_threshold:
            return d.frame_index
    return None


def classify_trajectory(
    detections: list[BallDetection],
    up_frame: int,
    down_frame: int,
    hoop_x: float,
    hoop_y: float,
    hoop_radius: float,
    near_miss_multiplier: float = 1.3,
) -> str | None:
    above_rim = []
    below_rim = []

    for d in detections:
        if up_frame <= d.frame_index <= down_frame and d.centroid is not None:
            if d.centroid[1] < hoop_y:
                above_rim.append(d)
            elif d.centroid[1] > hoop_y:
                below_rim.append(d)

    if not above_rim or not below_rim:
        return None

    last_above = above_rim[-1]
    first_below = below_rim[0]

    x_points = [last_above.centroid[0], first_below.centroid[0]]
    y_points = [last_above.centroid[1], first_below.centroid[1]]

    if len(set(x_points)) < 2:
        dx = abs(first_below.centroid[0] - hoop_x)
        if dx < hoop_radius * 0.8:
            return "score"
        if dx < hoop_radius * near_miss_multiplier:
            return "near_miss"
        return None

    try:
        m, b = np.polyfit(x_points, y_points, 1)
    except (np.linalg.LinAlgError, ValueError):
        return None

    if abs(m) < 1e-10:
        return None

    predicted_x = (hoop_y - b) / m
    distance = abs(predicted_x - hoop_x)

    if distance < hoop_radius * 0.8:
        return "score"
    if distance < hoop_radius * near_miss_multiplier:
        return "near_miss"
    return None


def events_to_segments(
    events: list[BallEvent],
    fps: float,
    pre_roll: float,
    post_roll: float,
    video_duration: float,
    min_duration: float,
    include_near_misses: bool,
) -> list[ClipSegment]:
    raw_segments = []
    for event in events:
        if event.event_type == "near_miss" and not include_near_misses:
            continue
        start = max(0.0, event.timestamp - pre_roll)
        end = min(video_duration, event.timestamp + post_roll)
        if end - start >= min_duration:
            raw_segments.append(ClipSegment(start, end, event.event_type, event.frame_index))

    raw_segments.sort(key=lambda s: s.start_time)

    merged = []
    for seg in raw_segments:
        if merged and seg.start_time <= merged[-1].end_time:
            merged_end = max(merged[-1].end_time, seg.end_time)
            merged_type = "score" if "score" in (merged[-1].event_type, seg.event_type) else "near_miss"
            merged[-1] = ClipSegment(merged[-1].start_time, merged_end, merged_type, merged[-1].event_frame)
        else:
            merged.append(seg)

    return merged


def split_long_segments(
    segments: list[ClipSegment],
    max_duration: float,
) -> list[ClipSegment]:
    result = []
    for seg in segments:
        duration = seg.end_time - seg.start_time
        if duration <= max_duration:
            result.append(seg)
        else:
            curr = seg.start_time
            while curr < seg.end_time:
                chunk_end = min(curr + max_duration, seg.end_time)
                result.append(ClipSegment(round(curr, 2), round(chunk_end, 2), seg.event_type, seg.event_frame))
                curr = chunk_end
    return result


def analyze_video(
    video_path: str,
    params: TrimParams,
    progress_callback: callable,
) -> list[ClipSegment]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / fps if fps > 0 else 0.0

        hoop_x = params.hoop_x
        hoop_y = params.hoop_y
        hoop_radius = params.hoop_radius

        if hoop_x is None or hoop_y is None or hoop_radius is None:
            target_frame = max(0, int(total_frames * 0.1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if not ret or frame is None:
                return []
            hoop = auto_detect_hoop(frame)
            if hoop is None:
                return []
            hoop_x, hoop_y, hoop_radius = hoop

        detector = BallDetector(confidence_threshold=params.yolo_confidence)
        raw_detections = detector.detect_in_video(video_path, progress_callback)
        cleaned = clean_ball_detections(raw_detections)
        filled = fill_gaps(cleaned)
        smoothed = smooth_trajectory(filled)

        events: list[BallEvent] = []
        scan_start = 0

        while scan_start < len(smoothed):
            sub_detections = smoothed[scan_start:]
            up_frame = detect_up_phase(sub_detections, hoop_x, hoop_y, hoop_radius)
            if up_frame is None:
                break

            up_frame += scan_start
            down_frame = detect_down_phase(smoothed, hoop_x, hoop_y, hoop_radius, start_after=up_frame)
            if down_frame is None:
                break

            event_type = classify_trajectory(
                smoothed,
                up_frame,
                down_frame,
                hoop_x,
                hoop_y,
                hoop_radius,
                params.near_miss_multiplier,
            )

            if event_type is not None:
                timestamp = down_frame / fps if fps > 0 else 0.0
                events.append(BallEvent(down_frame, timestamp, event_type, hoop_x, hoop_y, hoop_radius))

            scan_start = down_frame + 1

        segments = events_to_segments(
            events,
            fps,
            params.pre_roll_seconds,
            params.post_roll_seconds,
            video_duration,
            params.min_segment_duration,
            params.include_near_misses,
        )

        return split_long_segments(segments, params.max_clip_duration)
    finally:
        cap.release()
