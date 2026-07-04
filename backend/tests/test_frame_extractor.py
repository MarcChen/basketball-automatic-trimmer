from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.frame_extractor import extract_frame


class TestExtractFrame:
    @patch("services.frame_extractor.cv2.imwrite")
    @patch("services.frame_extractor.cv2.VideoCapture")
    def test_success(self, mock_cap_cls, mock_imwrite, tmp_path):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock())
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap
        mock_imwrite.return_value = True

        result = extract_frame("/fake/video.mp4", 100, str(tmp_path))

        mock_imwrite.assert_called_once()
        assert "frame_100" in result

    @patch("services.frame_extractor.cv2.imwrite")
    @patch("services.frame_extractor.cv2.VideoCapture")
    def test_returns_correct_path(self, mock_cap_cls, mock_imwrite, tmp_path):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock())
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap
        mock_imwrite.return_value = True

        result = extract_frame("/fake/game.mp4", 50, str(tmp_path))

        expected = str(Path(tmp_path) / "game_frame_50.jpg")
        assert result == expected

    @patch("services.frame_extractor.cv2.imwrite")
    @patch("services.frame_extractor.cv2.VideoCapture")
    def test_creates_output_dir(self, mock_cap_cls, mock_imwrite, tmp_path):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock())
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap
        mock_imwrite.return_value = True

        nested = str(tmp_path / "nested" / "frames")
        extract_frame("/fake/video.mp4", 0, nested)

        assert Path(nested).is_dir()

    @patch("services.frame_extractor.cv2.VideoCapture")
    def test_read_fails_raises(self, mock_cap_cls, tmp_path):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_cap.set.return_value = True
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(ValueError, match="Failed to read frame"):
            extract_frame("/fake/video.mp4", 100, str(tmp_path))

    @patch("services.frame_extractor.cv2.VideoCapture")
    def test_video_not_opened(self, mock_cap_cls, tmp_path):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(ValueError, match="Failed to open video"):
            extract_frame("/fake/bad.mp4", 0, str(tmp_path))
