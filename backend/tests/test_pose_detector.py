import math
from unittest.mock import MagicMock, patch

import pytest

from models.schemas import TrimParams
from services.pose_detector import (
    analyze_video,
    apply_buffer_and_filter,
    compute_activity_score,
    merge_segments,
)


def _make_landmark(x: float, y: float):
    lm = MagicMock()
    lm.x = x
    lm.y = y
    return lm


def _make_landmarks(positions: list[tuple[float, float]]):
    return [_make_landmark(x, y) for x, y in positions]


def _make_params(**overrides) -> TrimParams:
    defaults = {
        "video_filename": "test.mp4",
        "activity_threshold": 0.015,
        "min_segment_duration": 2.0,
        "buffer_seconds": 1.5,
        "min_detection_confidence": 0.5,
        "min_tracking_confidence": 0.5,
    }
    defaults.update(overrides)
    return TrimParams(**defaults)


class TestComputeActivityScore:
    def test_identical_landmarks(self):
        landmarks = _make_landmarks([(0.5, 0.5)] * 33)
        score = compute_activity_score(landmarks, landmarks)
        assert score == 0.0

    def test_different_landmarks(self):
        current = _make_landmarks([(1.0, 1.0)])
        previous = _make_landmarks([(0.0, 0.0)])
        score = compute_activity_score(current, previous)
        assert score == pytest.approx(math.sqrt(2), abs=1e-6)

    def test_known_distance(self):
        current = _make_landmarks([(0.3, 0.4)])
        previous = _make_landmarks([(0.0, 0.0)])
        score = compute_activity_score(current, previous)
        assert score == pytest.approx(0.5, abs=1e-6)

    def test_multiple_landmarks_averaged(self):
        current = _make_landmarks([(0.0, 0.0), (1.0, 0.0)])
        previous = _make_landmarks([(0.0, 0.0), (0.0, 0.0)])
        score = compute_activity_score(current, previous)
        assert score == pytest.approx(0.5, abs=1e-6)

    def test_empty_landmarks(self):
        score = compute_activity_score([], [])
        assert score == 0.0


class TestMergeSegments:
    def test_consecutive_frames(self):
        result = merge_segments([10, 11, 12, 13], 30.0)
        assert len(result) == 1
        assert result[0] == pytest.approx((10 / 30.0, 13 / 30.0))

    def test_with_gaps(self):
        result = merge_segments([10, 11, 12, 20, 21, 22], 30.0)
        assert len(result) == 2
        assert result[0] == pytest.approx((10 / 30.0, 12 / 30.0))
        assert result[1] == pytest.approx((20 / 30.0, 22 / 30.0))

    def test_empty(self):
        result = merge_segments([], 30.0)
        assert result == []

    def test_single_frame(self):
        result = merge_segments([42], 30.0)
        assert len(result) == 1
        assert result[0] == pytest.approx((42 / 30.0, 42 / 30.0))

    def test_multiple_gaps(self):
        result = merge_segments([10, 11, 50, 51, 100, 101], 30.0)
        assert len(result) == 3


class TestApplyBufferAndFilter:
    def test_adds_padding(self):
        result = apply_buffer_and_filter([(5.0, 10.0)], 1.5, 0.5, 60.0)
        assert len(result) == 1
        assert result[0] == pytest.approx((3.5, 11.5))

    def test_clamps_to_zero(self):
        result = apply_buffer_and_filter([(0.5, 2.0)], 1.5, 0.5, 60.0)
        assert len(result) == 1
        assert result[0][0] == pytest.approx(0.0)

    def test_clamps_to_video_duration(self):
        result = apply_buffer_and_filter([(58.0, 59.5)], 1.5, 0.5, 60.0)
        assert len(result) == 1
        assert result[0][1] == pytest.approx(60.0)

    def test_filters_short_segments(self):
        result = apply_buffer_and_filter([(5.0, 5.5)], 0.0, 2.0, 60.0)
        assert result == []

    def test_merges_overlapping(self):
        result = apply_buffer_and_filter([(5.0, 8.0), (9.0, 12.0)], 1.5, 0.5, 60.0)
        assert len(result) == 1
        assert result[0] == pytest.approx((3.5, 13.5))

    def test_no_merge_when_not_overlapping(self):
        result = apply_buffer_and_filter([(5.0, 8.0), (20.0, 25.0)], 1.0, 0.5, 60.0)
        assert len(result) == 2

    def test_empty_segments(self):
        result = apply_buffer_and_filter([], 1.5, 2.0, 60.0)
        assert result == []


class TestAnalyzeVideo:
    @patch("services.pose_detector.mp")
    @patch("services.pose_detector.cv2.cvtColor")
    @patch("services.pose_detector.cv2.VideoCapture")
    def test_basic_detection(self, mock_cap_cls, mock_cvtcolor, mock_mp):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            5: 30.0,  # FPS
            7: 150.0,  # frame_count (5 seconds)
        }.get(prop, 0.0)

        frame = MagicMock()
        mock_cap.read.side_effect = [
            (True, frame),
            (True, frame),
            (True, frame),
            (True, frame),
            (True, frame),
            (False, None),
        ]
        mock_cap_cls.return_value = mock_cap
        mock_cvtcolor.return_value = MagicMock()

        mock_pose = MagicMock()
        mock_mp.solutions.pose.Pose.return_value = mock_pose

        lm_stationary = _make_landmarks([(0.5, 0.5)] * 33)
        lm_moved = _make_landmarks([(0.6, 0.6)] * 33)

        results_stationary = MagicMock()
        results_stationary.pose_landmarks = MagicMock()
        results_stationary.pose_landmarks.landmark = lm_stationary

        results_moved = MagicMock()
        results_moved.pose_landmarks = MagicMock()
        results_moved.pose_landmarks.landmark = lm_moved

        mock_pose.process.side_effect = [
            results_stationary,
            results_moved,
            results_moved,
            results_moved,
            results_stationary,
        ]

        params = _make_params(
            activity_threshold=0.01,
            buffer_seconds=0.0,
            min_segment_duration=0.5,
        )
        progress_values = []

        result = analyze_video("/fake/video.mp4", params, progress_values.append)

        assert isinstance(result, list)
        assert len(progress_values) > 0
        assert progress_values[-1] == 100

    @patch("services.pose_detector.mp")
    @patch("services.pose_detector.cv2.cvtColor")
    @patch("services.pose_detector.cv2.VideoCapture")
    def test_no_motion(self, mock_cap_cls, mock_cvtcolor, mock_mp):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 90.0}.get(prop, 0.0)

        frame = MagicMock()
        mock_cap.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        mock_cap_cls.return_value = mock_cap
        mock_cvtcolor.return_value = MagicMock()

        mock_pose = MagicMock()
        mock_mp.solutions.pose.Pose.return_value = mock_pose

        lm = _make_landmarks([(0.5, 0.5)] * 33)
        results = MagicMock()
        results.pose_landmarks = MagicMock()
        results.pose_landmarks.landmark = lm
        mock_pose.process.return_value = results

        params = _make_params(activity_threshold=0.01, buffer_seconds=0.0, min_segment_duration=0.5)
        result = analyze_video("/fake/video.mp4", params, lambda p: None)

        assert result == []

    @patch("services.pose_detector.mp")
    @patch("services.pose_detector.cv2.VideoCapture")
    def test_empty_video(self, mock_cap_cls, mock_mp):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 0.0}.get(prop, 0.0)
        mock_cap.read.return_value = (False, None)
        mock_cap_cls.return_value = mock_cap

        params = _make_params()
        progress_values = []
        result = analyze_video("/fake/empty.mp4", params, progress_values.append)

        assert result == []

    @patch("services.pose_detector.cv2.VideoCapture")
    def test_video_not_opened(self, mock_cap_cls):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        params = _make_params()
        result = analyze_video("/fake/bad.mp4", params, lambda p: None)

        assert result == []

    @patch("services.pose_detector.mp")
    @patch("services.pose_detector.cv2.cvtColor")
    @patch("services.pose_detector.cv2.VideoCapture")
    def test_progress_callback_called(self, mock_cap_cls, mock_cvtcolor, mock_mp):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0, 7: 90.0}.get(prop, 0.0)

        frame = MagicMock()
        mock_cap.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        mock_cap_cls.return_value = mock_cap
        mock_cvtcolor.return_value = MagicMock()

        mock_pose = MagicMock()
        mock_mp.solutions.pose.Pose.return_value = mock_pose

        no_detection = MagicMock()
        no_detection.pose_landmarks = None
        mock_pose.process.return_value = no_detection

        params = _make_params()
        progress_values = []
        analyze_video("/fake/video.mp4", params, progress_values.append)

        assert len(progress_values) > 0
        assert 100 in progress_values
