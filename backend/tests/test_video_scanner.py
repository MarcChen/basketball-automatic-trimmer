from unittest.mock import MagicMock, patch

import pytest

from services.video_scanner import generate_thumbnail, get_video_metadata, scan_videos


def _make_mock_cap(fps=30.0, frame_count=900.0, width=1920, height=1080, opened=True):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = opened
    mock_cap.get.side_effect = lambda prop: {
        5: fps,  # CAP_PROP_FPS
        7: frame_count,  # CAP_PROP_FRAME_COUNT
        3: width,  # CAP_PROP_FRAME_WIDTH
        4: height,  # CAP_PROP_FRAME_HEIGHT
    }.get(prop, 0.0)
    mock_cap.read.return_value = (True, MagicMock())
    mock_cap.set.return_value = True
    return mock_cap


class TestGetVideoMetadata:
    @patch("services.video_scanner.cv2.VideoCapture")
    def test_success(self, mock_capture_cls):
        mock_capture_cls.return_value = _make_mock_cap(fps=30.0, frame_count=900.0, width=1920, height=1080)

        result = get_video_metadata("/fake/video.mp4")

        assert result is not None
        assert result["fps"] == 30.0
        assert result["frame_count"] == 900
        assert result["duration_seconds"] == pytest.approx(30.0)
        assert result["resolution"] == "1920x1080"

    @patch("services.video_scanner.cv2.VideoCapture")
    def test_invalid_video(self, mock_capture_cls):
        mock_capture_cls.return_value = _make_mock_cap(opened=False)

        result = get_video_metadata("/fake/bad.mp4")
        assert result is None

    @patch("services.video_scanner.cv2.VideoCapture")
    def test_zero_fps(self, mock_capture_cls):
        mock_capture_cls.return_value = _make_mock_cap(fps=0.0, frame_count=900.0)

        result = get_video_metadata("/fake/zerofps.mp4")
        assert result is None


class TestGenerateThumbnail:
    @patch("services.video_scanner.cv2.imwrite")
    @patch("services.video_scanner.cv2.VideoCapture")
    def test_success(self, mock_capture_cls, mock_imwrite):
        mock_capture_cls.return_value = _make_mock_cap(frame_count=100.0)
        mock_imwrite.return_value = True

        result = generate_thumbnail("/fake/video.mp4", "/tmp/thumb.jpg")

        assert result is True
        mock_imwrite.assert_called_once()

    @patch("services.video_scanner.cv2.VideoCapture")
    def test_no_frames(self, mock_capture_cls):
        mock_cap = _make_mock_cap(frame_count=0.0)
        mock_capture_cls.return_value = mock_cap

        result = generate_thumbnail("/fake/empty.mp4", "/tmp/thumb.jpg")
        assert result is False

    @patch("services.video_scanner.cv2.VideoCapture")
    def test_video_not_opened(self, mock_capture_cls):
        mock_capture_cls.return_value = _make_mock_cap(opened=False)

        result = generate_thumbnail("/fake/bad.mp4", "/tmp/thumb.jpg")
        assert result is False


class TestScanVideos:
    def test_empty_directory(self, tmp_path):
        result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))
        assert result == []

    def test_nonexistent_directory(self, tmp_path):
        result = scan_videos(str(tmp_path / "nonexistent"), str(tmp_path / "thumbs"))
        assert result == []

    def test_ignores_unsupported_extensions(self, tmp_path):
        (tmp_path / "readme.txt").touch()
        (tmp_path / "photo.jpg").touch()
        (tmp_path / "doc.pdf").touch()

        result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))
        assert result == []

    def test_finds_supported_extensions(self, tmp_path):
        for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            (tmp_path / f"video{ext}").touch()
        (tmp_path / "readme.txt").touch()

        with (
            patch("services.video_scanner.get_video_metadata") as mock_meta,
            patch("services.video_scanner.generate_thumbnail") as mock_thumb,
        ):
            mock_meta.return_value = {
                "fps": 30.0,
                "frame_count": 900,
                "duration_seconds": 30.0,
                "resolution": "1920x1080",
            }
            mock_thumb.return_value = True

            result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))

        assert len(result) == 5

    @patch("services.video_scanner.generate_thumbnail")
    @patch("services.video_scanner.get_video_metadata")
    def test_computes_size_mb(self, mock_meta, mock_thumb, tmp_path):
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * (5 * 1024 * 1024))

        mock_meta.return_value = {
            "fps": 30.0,
            "frame_count": 900,
            "duration_seconds": 30.0,
            "resolution": "1920x1080",
        }
        mock_thumb.return_value = True

        result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))

        assert len(result) == 1
        assert result[0].size_mb == 5.0

    @patch("services.video_scanner.generate_thumbnail")
    @patch("services.video_scanner.get_video_metadata")
    def test_thumbnail_url_format(self, mock_meta, mock_thumb, tmp_path):
        video_file = tmp_path / "game.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        mock_meta.return_value = {
            "fps": 30.0,
            "frame_count": 900,
            "duration_seconds": 30.0,
            "resolution": "1920x1080",
        }
        mock_thumb.return_value = True

        result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))

        assert len(result) == 1
        assert result[0].thumbnail_url == "/thumbnails/game.jpg"

    @patch("services.video_scanner.generate_thumbnail")
    @patch("services.video_scanner.get_video_metadata")
    def test_skips_unreadable_videos(self, mock_meta, mock_thumb, tmp_path):
        (tmp_path / "good.mp4").write_bytes(b"\x00" * 1024)
        (tmp_path / "bad.mp4").write_bytes(b"\x00" * 1024)

        mock_meta.side_effect = [
            None,
            {"fps": 30.0, "frame_count": 900, "duration_seconds": 30.0, "resolution": "1920x1080"},
        ]
        mock_thumb.return_value = True

        result = scan_videos(str(tmp_path), str(tmp_path / "thumbs"))

        assert len(result) == 1
        assert result[0].filename == "good.mp4"
