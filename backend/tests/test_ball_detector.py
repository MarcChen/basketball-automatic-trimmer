from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services.ball_detector import (
    BallDetection,
    BallDetector,
    extract_centroids,
    fill_gaps,
    smooth_trajectory,
)


def _make_detection(frame_index, centroid, confidence=0.9, bbox=None):
    return BallDetection(frame_index=frame_index, centroid=centroid, confidence=confidence, bbox=bbox)


def _make_yolo_result(boxes_xyxy, confs, classes):
    result = MagicMock()
    boxes = MagicMock()
    boxes_xyxy_arr = np.array(boxes_xyxy) if boxes_xyxy else np.empty((0, 4))
    confs_arr = np.array(confs) if confs else np.empty((0,))
    classes_arr = np.array(classes) if classes else np.empty((0,))

    xyxy_cpu = MagicMock()
    xyxy_cpu.numpy.return_value = boxes_xyxy_arr
    boxes.xyxy = xyxy_cpu

    conf_cpu = MagicMock()
    conf_cpu.numpy.return_value = confs_arr
    boxes.conf = conf_cpu

    cls_mock = MagicMock()
    cls_int = MagicMock()
    cls_int.cpu.return_value.numpy.return_value = classes_arr
    cls_mock.int.return_value = cls_int
    boxes.cls = cls_mock

    cls_np = np.array(classes)
    mask = cls_np == 32 if len(cls_np) > 0 else np.array([], dtype=bool)
    mask_mock = MagicMock()
    mask_mock.any.return_value = bool(mask.any()) if len(mask) > 0 else False
    mask_any = MagicMock()
    mask_any.cpu.return_value.numpy.return_value = boxes_xyxy_arr[mask] if mask.any() else np.empty((0, 4))
    boxes.xyxy[mask] = mask_any

    conf_any = MagicMock()
    conf_any.cpu.return_value.numpy.return_value = confs_arr[mask] if mask.any() else np.empty((0,))
    boxes.conf[mask] = conf_any

    result.boxes = boxes
    return result


def _make_mock_cap(fps=30.0, frame_count=90.0, opened=True):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = opened
    mock_cap.get.side_effect = lambda prop: {
        5: fps,
        7: frame_count,
    }.get(prop, 0.0)
    return mock_cap


class TestBallDetector:
    @patch("services.ball_detector.YOLO")
    @patch("services.ball_detector.cv2.VideoCapture")
    def test_detect_in_video_finds_ball(self, mock_cap_cls, mock_yolo_cls):
        mock_cap = _make_mock_cap(fps=30.0, frame_count=90.0)
        frame = MagicMock()
        mock_cap.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        mock_cap_cls.return_value = mock_cap

        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        result1 = _make_yolo_result([[100, 100, 120, 120]], [0.9], [32])
        result2 = _make_yolo_result([[110, 105, 130, 125]], [0.85], [32])
        result3 = _make_yolo_result([[115, 110, 135, 130]], [0.88], [32])
        mock_model.side_effect = [[result1], [result2], [result3]]

        detector = BallDetector(confidence_threshold=0.4)
        detections = detector.detect_in_video("/fake/video.mp4")

        assert len(detections) == 3
        assert detections[0].centroid is not None
        assert detections[0].centroid == pytest.approx((110.0, 110.0))
        assert detections[0].confidence == pytest.approx(0.9)

    @patch("services.ball_detector.YOLO")
    @patch("services.ball_detector.cv2.VideoCapture")
    def test_detect_in_video_no_ball(self, mock_cap_cls, mock_yolo_cls):
        mock_cap = _make_mock_cap(fps=30.0, frame_count=90.0)
        frame = MagicMock()
        mock_cap.read.side_effect = [(True, frame)] * 2 + [(False, None)]
        mock_cap_cls.return_value = mock_cap

        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        empty_result = _make_yolo_result([], [], [])
        mock_model.side_effect = [[empty_result], [empty_result]]

        detector = BallDetector(confidence_threshold=0.4)
        detections = detector.detect_in_video("/fake/video.mp4")

        assert len(detections) == 2
        assert detections[0].centroid is None
        assert detections[0].confidence == 0.0

    @patch("services.ball_detector.YOLO")
    @patch("services.ball_detector.cv2.VideoCapture")
    def test_detect_in_video_video_not_opened(self, mock_cap_cls, mock_yolo_cls):
        mock_cap = _make_mock_cap(opened=False)
        mock_cap_cls.return_value = mock_cap

        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model

        detector = BallDetector(confidence_threshold=0.4)
        detections = detector.detect_in_video("/fake/bad.mp4")

        assert detections == []

    @patch("services.ball_detector.YOLO")
    @patch("services.ball_detector.cv2.VideoCapture")
    def test_detect_in_video_progress_callback(self, mock_cap_cls, mock_yolo_cls):
        mock_cap = _make_mock_cap(fps=30.0, frame_count=90.0)
        frame = MagicMock()
        mock_cap.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        mock_cap_cls.return_value = mock_cap

        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        empty_result = _make_yolo_result([], [], [])
        mock_model.return_value = [empty_result]

        detector = BallDetector(confidence_threshold=0.4)
        progress_values = []
        detector.detect_in_video("/fake/video.mp4", progress_values.append)

        assert len(progress_values) > 0
        assert 100 in progress_values


class TestFillGaps:
    def test_fills_small_gap(self):
        detections = [
            _make_detection(0, (100.0, 100.0)),
            _make_detection(1, None, confidence=0.0),
            _make_detection(2, None, confidence=0.0),
            _make_detection(3, (130.0, 130.0)),
        ]
        result = fill_gaps(detections, max_gap=5)

        assert result[1].centroid is not None
        assert result[2].centroid is not None
        assert result[1].centroid[0] == pytest.approx(110.0)
        assert result[2].centroid[0] == pytest.approx(120.0)

    def test_does_not_fill_large_gap(self):
        detections = [
            _make_detection(0, (100.0, 100.0)),
            _make_detection(1, None, confidence=0.0),
            _make_detection(2, None, confidence=0.0),
            _make_detection(3, None, confidence=0.0),
            _make_detection(4, None, confidence=0.0),
            _make_detection(5, None, confidence=0.0),
            _make_detection(6, None, confidence=0.0),
            _make_detection(7, (200.0, 200.0)),
        ]
        result = fill_gaps(detections, max_gap=5)

        assert result[1].centroid is None
        assert result[6].centroid is None

    def test_no_gaps(self):
        detections = [
            _make_detection(0, (100.0, 100.0)),
            _make_detection(1, (110.0, 110.0)),
        ]
        result = fill_gaps(detections, max_gap=5)

        assert result[0].centroid == (100.0, 100.0)
        assert result[1].centroid == (110.0, 110.0)

    def test_empty_list(self):
        result = fill_gaps([], max_gap=5)
        assert result == []


class TestSmoothTrajectory:
    def test_smooths_noisy_trajectory(self):
        detections = [
            _make_detection(i, (100.0 + i * 10 + noise, 100.0 + i * 5))
            for i, noise in enumerate([0, 5, -3, 7, -2, 4, -1, 6, -4, 3, 0, 5, -3, 7, -2])
        ]
        result = smooth_trajectory(detections, window=11, polyorder=3)

        valid_indices = [i for i, d in enumerate(result) if d.centroid is not None]
        original_xs = [detections[i].centroid[0] for i in valid_indices]
        smoothed_xs = [result[i].centroid[0] for i in valid_indices]
        assert original_xs != smoothed_xs

    def test_too_few_points(self):
        detections = [_make_detection(i, (100.0 + i, 100.0)) for i in range(5)]
        result = smooth_trajectory(detections, window=11, polyorder=3)

        assert result[0].centroid == (100.0, 100.0)

    def test_all_none(self):
        detections = [_make_detection(i, None, confidence=0.0) for i in range(15)]
        result = smooth_trajectory(detections, window=11, polyorder=3)

        assert all(d.centroid is None for d in result)


class TestExtractCentroids:
    def test_returns_centroids(self):
        detections = [
            _make_detection(0, (100.0, 100.0)),
            _make_detection(1, None, confidence=0.0),
            _make_detection(2, (120.0, 110.0)),
        ]
        result = extract_centroids(detections)

        assert result == [(100.0, 100.0), None, (120.0, 110.0)]
