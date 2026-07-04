from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services.hoop_detector import (
    auto_detect_hoop,
    detect_orange_circles,
    find_white_rectangles,
    normalize_hoop_position,
)


def _make_frame(height=1080, width=1920):
    return np.zeros((height, width, 3), dtype=np.uint8)


def _make_circles(circles_list):
    if not circles_list:
        return np.array([])
    return np.array([[circles_list]], dtype=np.float32)


class TestFindWhiteRectangles:
    def test_finds_rectangle(self):
        gray = _make_frame(height=200, width=300)
        cv2_img = gray.copy()
        cv2_img[50:150, 100:250] = 255
        result = find_white_rectangles(cv2_img, min_area=500, max_area=100000)

        assert len(result) >= 1

    def test_ignores_small_regions(self):
        gray = _make_frame(height=200, width=300)
        gray[50:55, 100:105] = 255
        result = find_white_rectangles(gray, min_area=500, max_area=100000)

        assert result == []

    def test_empty_image(self):
        gray = _make_frame(height=200, width=300)
        result = find_white_rectangles(gray, min_area=500, max_area=100000)

        assert result == []


class TestDetectOrangeCircles:
    @patch("services.hoop_detector.cv2.HoughCircles")
    def test_returns_circles(self, mock_hough):
        mock_hough.return_value = _make_circles([[100, 100, 30]])
        mask = np.zeros((200, 200), dtype=np.uint8)

        result = detect_orange_circles(mask)

        assert result.size > 0

    @patch("services.hoop_detector.cv2.HoughCircles")
    def test_no_circles_found(self, mock_hough):
        mock_hough.return_value = None
        mask = np.zeros((200, 200), dtype=np.uint8)

        result = detect_orange_circles(mask)

        assert result.size == 0

    @patch("services.hoop_detector.cv2.cvtColor")
    @patch("services.hoop_detector.cv2.HoughCircles")
    def test_converts_3channel_mask(self, mock_hough, mock_cvt):
        mock_hough.return_value = _make_circles([[100, 100, 30]])
        mock_cvt.return_value = np.zeros((200, 200), dtype=np.uint8)
        mask = np.zeros((200, 200, 3), dtype=np.uint8)

        detect_orange_circles(mask)

        mock_cvt.assert_called_once()


class TestAutoDetectHoop:
    @patch("services.hoop_detector.detect_orange_circles")
    def test_returns_best_candidate(self, mock_detect):
        frame = _make_frame(height=400, width=600)
        mock_detect.return_value = _make_circles([[300, 200, 40]])

        result = auto_detect_hoop(frame, use_backboard_constraint=False)

        assert result is not None
        assert result == (300, 200, 40)

    @patch("services.hoop_detector.detect_orange_circles")
    def test_no_circles_returns_none(self, mock_detect):
        frame = _make_frame(height=400, width=600)
        mock_detect.return_value = np.array([])

        result = auto_detect_hoop(frame, use_backboard_constraint=False)

        assert result is None

    @patch("services.hoop_detector.find_white_rectangles")
    @patch("services.hoop_detector.detect_orange_circles")
    def test_validates_against_backboard(self, mock_detect, mock_rects):
        frame = _make_frame(height=400, width=600)
        mock_rects.return_value = [(280, 150, 100, 80)]
        mock_detect.return_value = _make_circles([[500, 380, 40], [320, 180, 25]])

        result = auto_detect_hoop(frame, use_backboard_constraint=True)

        assert result is not None
        cx, cy, r = result
        assert abs(cx - 320) < 50

    @patch("services.hoop_detector.detect_orange_circles")
    def test_no_backboard_accepts_size_range(self, mock_detect):
        frame = _make_frame(height=400, width=600)
        mock_detect.return_value = _make_circles([[300, 200, 5], [300, 200, 40]])

        result = auto_detect_hoop(frame, use_backboard_constraint=False)

        assert result is not None
        assert result[2] == 40


class TestNormalizeHoopPosition:
    def test_normalizes(self):
        result = normalize_hoop_position((960, 540, 50), 1920, 1080)

        assert result[0] == pytest.approx(0.5)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(50 / 1080, abs=1e-4)

    def test_zero_origin(self):
        result = normalize_hoop_position((0, 0, 0), 1920, 1080)

        assert result == (0.0, 0.0, 0.0)
