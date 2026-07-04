from dataclasses import dataclass

import cv2
import numpy as np
from scipy.signal import savgol_filter
from ultralytics import YOLO

SPORTS_BALL_CLASS = 32


@dataclass
class BallDetection:
    frame_index: int
    centroid: tuple[float, float] | None
    confidence: float
    bbox: tuple[float, float, float, float] | None


class BallDetector:
    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.4,
        device: str | None = None,
    ):
        self.model = YOLO(model_name)
        if device:
            self.model.to(device)
        self.confidence_threshold = confidence_threshold

    def detect_in_video(
        self,
        video_path: str,
        progress_callback: callable = lambda pct: None,
    ) -> list[BallDetection]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            detections: list[BallDetection] = []
            frame_index = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                detection = self._detect_in_frame(frame, frame_index)
                detections.append(detection)

                if frame_index % 30 == 0 and total_frames > 0:
                    progress_callback(int(frame_index / total_frames * 100))

                frame_index += 1

            progress_callback(100)
            return detections
        finally:
            cap.release()

    def _detect_in_frame(self, frame: np.ndarray, frame_index: int) -> BallDetection:
        results = self.model(
            frame,
            conf=self.confidence_threshold,
            classes=[SPORTS_BALL_CLASS],
            verbose=False,
        )

        best_conf = 0.0
        best_bbox = None
        best_centroid = None

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            mask = boxes.cls == SPORTS_BALL_CLASS
            if not mask.any():
                continue

            xyxy = boxes.xyxy[mask].cpu().numpy()
            conf = boxes.conf[mask].cpu().numpy()

            for i in range(len(xyxy)):
                if conf[i] > best_conf:
                    best_conf = float(conf[i])
                    x1, y1, x2, y2 = xyxy[i].tolist()
                    best_bbox = (x1, y1, x2, y2)
                    best_centroid = ((x1 + x2) / 2, (y1 + y2) / 2)

        return BallDetection(
            frame_index=frame_index,
            centroid=best_centroid,
            confidence=best_conf,
            bbox=best_bbox,
        )


def fill_gaps(detections: list[BallDetection], max_gap: int = 5) -> list[BallDetection]:
    if not detections:
        return []

    result = [BallDetection(d.frame_index, d.centroid, d.confidence, d.bbox) for d in detections]

    valid_indices = [i for i, d in enumerate(result) if d.centroid is not None]
    if len(valid_indices) < 2:
        return result

    for i in range(len(valid_indices) - 1):
        prev_idx = valid_indices[i]
        next_idx = valid_indices[i + 1]
        gap = next_idx - prev_idx - 1

        if 0 < gap <= max_gap:
            prev_c = result[prev_idx].centroid
            next_c = result[next_idx].centroid
            for j in range(prev_idx + 1, next_idx):
                t = (j - prev_idx) / (next_idx - prev_idx)
                interpolated = (
                    prev_c[0] + t * (next_c[0] - prev_c[0]),
                    prev_c[1] + t * (next_c[1] - prev_c[1]),
                )
                result[j] = BallDetection(j, interpolated, 0.0, None)

    return result


def smooth_trajectory(
    detections: list[BallDetection],
    window: int = 11,
    polyorder: int = 3,
) -> list[BallDetection]:
    valid_indices = [i for i, d in enumerate(detections) if d.centroid is not None]
    if len(valid_indices) < window:
        return [BallDetection(d.frame_index, d.centroid, d.confidence, d.bbox) for d in detections]

    xs = np.array([detections[i].centroid[0] for i in valid_indices])
    ys = np.array([detections[i].centroid[1] for i in valid_indices])

    if len(xs) % 2 == 0 and window % 2 == 0:
        window = window + 1
    if window > len(xs):
        window = len(xs) if len(xs) % 2 == 1 else len(xs) - 1
    if window < polyorder + 2:
        return [BallDetection(d.frame_index, d.centroid, d.confidence, d.bbox) for d in detections]

    xs_smooth = savgol_filter(xs, window, polyorder)
    ys_smooth = savgol_filter(ys, window, polyorder)

    result = [BallDetection(d.frame_index, d.centroid, d.confidence, d.bbox) for d in detections]
    for k, idx in enumerate(valid_indices):
        result[idx] = BallDetection(
            detections[idx].frame_index,
            (float(xs_smooth[k]), float(ys_smooth[k])),
            detections[idx].confidence,
            detections[idx].bbox,
        )

    return result


def extract_centroids(detections: list[BallDetection]) -> list[tuple[float, float] | None]:
    return [d.centroid for d in detections]
