from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from models.schemas import TrimParams
from services.ball_detector import BallDetection
from services.event_detector import (
    BallEvent,
    ClipSegment,
    clean_ball_detections,
    classify_trajectory,
    detect_down_phase,
    detect_up_phase,
    events_to_segments,
    split_long_segments,
)


def _make_detection(frame_index, centroid, confidence=0.9, bbox=None):
    return BallDetection(frame_index=frame_index, centroid=centroid, confidence=confidence, bbox=bbox)


def _make_params(**overrides) -> TrimParams:
    defaults = {
        "video_filename": "test.mp4",
        "hoop_x": 500.0,
        "hoop_y": 300.0,
        "hoop_radius": 40.0,
        "yolo_confidence": 0.4,
        "near_miss_multiplier": 1.3,
        "pre_roll_seconds": 3.0,
        "post_roll_seconds": 2.0,
        "min_segment_duration": 1.5,
        "max_clip_duration": 30.0,
        "include_near_misses": True,
    }
    defaults.update(overrides)
    return TrimParams(**defaults)


class TestCleanBallDetections:
    def test_keeps_realistic_movement(self):
        detections = [
            _make_detection(0, (100.0, 100.0), bbox=(90, 90, 110, 110)),
            _make_detection(1, (105.0, 105.0), bbox=(95, 95, 115, 115)),
        ]
        result = clean_ball_detections(detections)

        assert result[0].centroid == (100.0, 100.0)
        assert result[1].centroid == (105.0, 105.0)

    def test_removes_unrealistic_jump(self):
        detections = [
            _make_detection(0, (100.0, 100.0), bbox=(90, 90, 110, 110)),
            _make_detection(1, (500.0, 500.0), bbox=(490, 490, 510, 510)),
        ]
        result = clean_ball_detections(detections)

        assert result[0].centroid == (100.0, 100.0)
        assert result[1].centroid is None

    def test_all_none_stays_none(self):
        detections = [
            _make_detection(0, None, confidence=0.0),
            _make_detection(1, None, confidence=0.0),
        ]
        result = clean_ball_detections(detections)

        assert all(d.centroid is None for d in result)


class TestDetectUpPhase:
    def test_finds_up_frame(self):
        detections = [
            _make_detection(0, (100.0, 500.0)),
            _make_detection(1, (500.0, 200.0)),
        ]
        result = detect_up_phase(detections, hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0)

        assert result == 1

    def test_no_up_frame(self):
        detections = [
            _make_detection(0, (100.0, 500.0)),
            _make_detection(1, (100.0, 400.0)),
        ]
        result = detect_up_phase(detections, hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0)

        assert result is None


class TestDetectDownPhase:
    def test_finds_down_frame(self):
        detections = [
            _make_detection(0, (500.0, 200.0)),
            _make_detection(1, (500.0, 350.0)),
        ]
        result = detect_down_phase(detections, hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0)

        assert result == 1

    def test_respects_start_after(self):
        detections = [
            _make_detection(0, (500.0, 350.0)),
            _make_detection(1, (500.0, 200.0)),
        ]
        result = detect_down_phase(detections, hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0, start_after=1)

        assert result is None

    def test_no_down_frame(self):
        detections = [
            _make_detection(0, (500.0, 200.0)),
            _make_detection(1, (500.0, 250.0)),
        ]
        result = detect_down_phase(detections, hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0)

        assert result is None


class TestClassifyTrajectory:
    def test_score(self):
        detections = [
            _make_detection(0, (500.0, 250.0)),
            _make_detection(1, (500.0, 280.0)),
            _make_detection(2, (500.0, 320.0)),
            _make_detection(3, (500.0, 350.0)),
        ]
        result = classify_trajectory(
            detections, up_frame=0, down_frame=3,
            hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0,
        )

        assert result == "score"

    def test_near_miss(self):
        detections = [
            _make_detection(0, (450.0, 250.0)),
            _make_detection(1, (460.0, 280.0)),
            _make_detection(2, (470.0, 320.0)),
            _make_detection(3, (480.0, 350.0)),
        ]
        result = classify_trajectory(
            detections, up_frame=0, down_frame=3,
            hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0,
            near_miss_multiplier=1.3,
        )

        assert result == "near_miss"

    def test_miss(self):
        detections = [
            _make_detection(0, (200.0, 250.0)),
            _make_detection(1, (200.0, 280.0)),
            _make_detection(2, (200.0, 320.0)),
            _make_detection(3, (200.0, 350.0)),
        ]
        result = classify_trajectory(
            detections, up_frame=0, down_frame=3,
            hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0,
        )

        assert result is None

    def test_vertical_trajectory(self):
        detections = [
            _make_detection(0, (500.0, 250.0)),
            _make_detection(1, (500.0, 280.0)),
            _make_detection(2, (500.0, 320.0)),
            _make_detection(3, (500.0, 350.0)),
        ]
        result = classify_trajectory(
            detections, up_frame=0, down_frame=3,
            hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0,
        )

        assert result == "score"


class TestEventsToSegments:
    def test_creates_segments(self):
        events = [
            BallEvent(frame_index=90, timestamp=3.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
            BallEvent(frame_index=180, timestamp=6.0, event_type="near_miss", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=3.0, post_roll=2.0,
            video_duration=60.0, min_duration=1.0, include_near_misses=True,
        )

        assert len(result) == 2
        assert result[0].start_time == pytest.approx(0.0)
        assert result[0].end_time == pytest.approx(5.0)
        assert result[0].event_type == "score"

    def test_merges_overlapping(self):
        events = [
            BallEvent(frame_index=90, timestamp=3.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
            BallEvent(frame_index=120, timestamp=4.0, event_type="near_miss", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=3.0, post_roll=2.0,
            video_duration=60.0, min_duration=1.0, include_near_misses=True,
        )

        assert len(result) == 1

    def test_filters_short_segments(self):
        events = [
            BallEvent(frame_index=30, timestamp=1.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=0.5, post_roll=0.5,
            video_duration=60.0, min_duration=2.0, include_near_misses=True,
        )

        assert result == []

    def test_filters_near_misses(self):
        events = [
            BallEvent(frame_index=90, timestamp=3.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
            BallEvent(frame_index=180, timestamp=6.0, event_type="near_miss", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=3.0, post_roll=2.0,
            video_duration=60.0, min_duration=1.0, include_near_misses=False,
        )

        assert len(result) == 1
        assert result[0].event_type == "score"

    def test_merge_prefers_score(self):
        events = [
            BallEvent(frame_index=90, timestamp=3.0, event_type="near_miss", hoop_x=500, hoop_y=300, hoop_radius=40),
            BallEvent(frame_index=120, timestamp=4.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=3.0, post_roll=2.0,
            video_duration=60.0, min_duration=1.0, include_near_misses=True,
        )

        assert len(result) == 1
        assert result[0].event_type == "score"

    def test_clamps_to_video_bounds(self):
        events = [
            BallEvent(frame_index=30, timestamp=1.0, event_type="score", hoop_x=500, hoop_y=300, hoop_radius=40),
        ]
        result = events_to_segments(
            events, fps=30.0, pre_roll=5.0, post_roll=5.0,
            video_duration=3.0, min_duration=1.0, include_near_misses=True,
        )

        assert len(result) == 1
        assert result[0].start_time == 0.0
        assert result[0].end_time == 3.0


class TestSplitLongSegments:
    def test_splits_long(self):
        segments = [ClipSegment(start_time=0.0, end_time=60.0, event_type="score", event_frame=0)]
        result = split_long_segments(segments, max_duration=30.0)

        assert len(result) == 2
        assert result[0].end_time == pytest.approx(30.0)

    def test_keeps_short(self):
        segments = [ClipSegment(start_time=0.0, end_time=10.0, event_type="score", event_frame=0)]
        result = split_long_segments(segments, max_duration=30.0)

        assert len(result) == 1
        assert result[0].end_time == 10.0


class TestAnalyzeVideo:
    @patch("services.event_detector.BallDetector")
    @patch("services.event_detector.auto_detect_hoop")
    @patch("services.event_detector.cv2.VideoCapture")
    def test_uses_calibration_when_provided(self, mock_cap_cls, mock_auto_hoop, mock_ball_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 90.0}.get(prop, 0.0)
        mock_cap.read.return_value = (False, None)
        mock_cap_cls.return_value = mock_cap

        mock_detector = MagicMock()
        mock_detector.detect_in_video.return_value = []
        mock_ball_cls.return_value = mock_detector

        params = _make_params(hoop_x=500.0, hoop_y=300.0, hoop_radius=40.0)
        result = __import__("services.event_detector", fromlist=["analyze_video"]).analyze_video(
            "/fake/video.mp4", params, lambda pct: None,
        )

        assert result == []
        mock_auto_hoop.assert_not_called()

    @patch("services.event_detector.BallDetector")
    @patch("services.event_detector.auto_detect_hoop")
    @patch("services.event_detector.cv2.VideoCapture")
    def test_auto_detects_when_no_calibration(self, mock_cap_cls, mock_auto_hoop, mock_ball_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 90.0}.get(prop, 0.0)
        frame = MagicMock()
        mock_cap.read.return_value = (True, frame)
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap

        mock_auto_hoop.return_value = (500, 300, 40)

        mock_detector = MagicMock()
        mock_detector.detect_in_video.return_value = []
        mock_ball_cls.return_value = mock_detector

        params = _make_params(hoop_x=None, hoop_y=None, hoop_radius=None)
        result = __import__("services.event_detector", fromlist=["analyze_video"]).analyze_video(
            "/fake/video.mp4", params, lambda pct: None,
        )

        assert result == []
        mock_auto_hoop.assert_called_once()

    @patch("services.event_detector.BallDetector")
    @patch("services.event_detector.auto_detect_hoop")
    @patch("services.event_detector.cv2.VideoCapture")
    def test_auto_detect_fails_returns_empty(self, mock_cap_cls, mock_auto_hoop, mock_ball_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 90.0}.get(prop, 0.0)
        frame = MagicMock()
        mock_cap.read.return_value = (True, frame)
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap

        mock_auto_hoop.return_value = None

        mock_detector = MagicMock()
        mock_ball_cls.return_value = mock_detector

        params = _make_params(hoop_x=None, hoop_y=None, hoop_radius=None)
        result = __import__("services.event_detector", fromlist=["analyze_video"]).analyze_video(
            "/fake/video.mp4", params, lambda pct: None,
        )

        assert result == []
