import os
from unittest.mock import MagicMock, patch

import pytest

from services.clip_exporter import build_clip_filename, export_clips


class TestBuildClipFilename:
    def test_format(self):
        result = build_clip_filename("game.mp4", 1, 5.0, 15.5)
        assert result == "game_clip_001_5.0s-15.5s.mp4"

    def test_strips_extension(self):
        result = build_clip_filename("video.mov", 2, 10.0, 20.0)
        assert result == "video_clip_002_10.0s-20.0s.mp4"

    def test_index_padding(self):
        result = build_clip_filename("test.mp4", 10, 0.0, 5.0)
        assert result == "test_clip_010_0.0s-5.0s.mp4"

    def test_decimal_formatting(self):
        result = build_clip_filename("clip.mp4", 1, 1.234, 9.876)
        assert result == "clip_clip_001_1.2s-9.9s.mp4"


class TestExportClips:
    @patch("services.clip_exporter.os.path.getsize", return_value=5 * 1024 * 1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_calls_ffmpeg_for_each_segment(self, mock_ffmpeg, mock_getsize, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        segments = [(0.0, 5.0), (10.0, 20.0), (30.0, 45.0)]
        result = export_clips("/fake/input.mp4", segments, str(tmp_path), "game.mp4")

        assert mock_ffmpeg.input.call_count == 3
        assert len(result) == 3

    @patch("services.clip_exporter.os.path.getsize", return_value=1024 * 1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_correct_parameters(self, mock_ffmpeg, mock_getsize, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        export_clips("/fake/input.mp4", [(5.0, 15.0)], str(tmp_path), "game.mp4")

        mock_ffmpeg.input.assert_called_once_with("/fake/input.mp4", ss=5.0, to=15.0)
        expected_path = os.path.join(str(tmp_path), "game_clip_001_5.0s-15.0s.mp4")
        mock_chain.output.assert_called_once_with(expected_path, c="copy")

    @patch("services.clip_exporter.os.path.getsize", return_value=2 * 1024 * 1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_returns_correct_metadata(self, mock_ffmpeg, mock_getsize, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        result = export_clips("/fake/input.mp4", [(5.0, 15.0)], str(tmp_path), "game.mp4")

        assert len(result) == 1
        clip = result[0]
        assert clip.filename == "game_clip_001_5.0s-15.0s.mp4"
        assert clip.source_video == "game.mp4"
        assert clip.start_time == 5.0
        assert clip.end_time == 15.0
        assert clip.duration == 10.0
        assert clip.size_mb == 2.0

    @patch("services.clip_exporter.ffmpeg")
    def test_empty_segments(self, mock_ffmpeg, tmp_path):
        result = export_clips("/fake/input.mp4", [], str(tmp_path), "game.mp4")

        assert result == []
        mock_ffmpeg.input.assert_not_called()

    @patch("services.clip_exporter.os.path.getsize", return_value=1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_url_format(self, mock_ffmpeg, mock_getsize, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        result = export_clips("/fake/input.mp4", [(0.0, 5.0)], str(tmp_path), "game.mp4")

        assert result[0].url == "/output/game_clip_001_0.0s-5.0s.mp4"

    @patch("services.clip_exporter.os.path.getsize", return_value=1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_creates_output_dir(self, mock_ffmpeg, mock_getsize, tmp_path):
        output_dir = str(tmp_path / "nested" / "output")

        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        export_clips("/fake/input.mp4", [(0.0, 5.0)], output_dir, "game.mp4")

        assert os.path.isdir(output_dir)

    @patch("services.clip_exporter.ffmpeg")
    def test_ffmpeg_error(self, mock_ffmpeg, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_ffmpeg.Error = Exception

        error = Exception("ffmpeg failed")
        error.stderr = b"error details"
        mock_chain.run.side_effect = error

        with pytest.raises(RuntimeError, match="ffmpeg failed cutting"):
            export_clips("/fake/input.mp4", [(0.0, 5.0)], str(tmp_path), "game.mp4")

    @patch("services.clip_exporter.os.path.getsize", return_value=1024)
    @patch("services.clip_exporter.ffmpeg")
    def test_size_calculation(self, mock_ffmpeg, mock_getsize, tmp_path):
        mock_chain = MagicMock()
        mock_ffmpeg.input.return_value = mock_chain
        mock_chain.output.return_value = mock_chain
        mock_chain.run.return_value = None

        mock_getsize.return_value = 10 * 1024 * 1024
        result = export_clips("/fake/input.mp4", [(0.0, 5.0)], str(tmp_path), "game.mp4")

        assert result[0].size_mb == 10.0
