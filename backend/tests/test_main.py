from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, jobs, calibrations


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_state():
    jobs.clear()
    calibrations.clear()
    yield
    jobs.clear()
    calibrations.clear()


@pytest.mark.anyio
class TestGetVideos:
    async def test_returns_video_list(self, client):
        mock_videos = [
            MagicMock(
                filename="game.mp4",
                path="/data/game.mp4",
                size_mb=100.0,
                duration_seconds=300.0,
                fps=30.0,
                resolution="1920x1080",
                thumbnail_url="/thumbnails/game.jpg",
            )
        ]
        with patch("main.scan_videos", return_value=mock_videos):
            resp = await client.get("/videos")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["filename"] == "game.mp4"

    async def test_empty_data_dir(self, client):
        with patch("main.scan_videos", return_value=[]):
            resp = await client.get("/videos")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_scanner_error_returns_500(self, client):
        with patch("main.scan_videos", side_effect=RuntimeError("disk error")):
            resp = await client.get("/videos")

        assert resp.status_code == 500
        assert "disk error" in resp.json()["detail"]


@pytest.mark.anyio
class TestGetThumbnail:
    async def test_serves_existing_thumbnail(self, client, tmp_path):
        thumb_file = tmp_path / "game.jpg"
        thumb_file.write_bytes(b"\xff\xd8\xff\xe0")

        with patch("main.THUMBNAILS_DIR", tmp_path):
            resp = await client.get("/thumbnails/game.jpg")

        assert resp.status_code == 200

    async def test_missing_thumbnail_returns_404(self, client, tmp_path):
        with patch("main.THUMBNAILS_DIR", tmp_path):
            resp = await client.get("/thumbnails/nonexistent.jpg")

        assert resp.status_code == 404


@pytest.mark.anyio
class TestGetFrame:
    @patch("main.extract_frame")
    async def test_serves_frame(self, mock_extract, client, tmp_path):
        frame_file = tmp_path / "game_frame_100.jpg"
        frame_file.write_bytes(b"\xff\xd8\xff\xe0")

        mock_extract.return_value = str(frame_file)

        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            resp = await client.get("/frame/game.mp4?frame_number=100")

        assert resp.status_code == 200

    @patch("main.extract_frame")
    async def test_extract_fails_returns_400(self, mock_extract, client, tmp_path):
        mock_extract.side_effect = ValueError("Failed to read frame")

        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            resp = await client.get("/frame/game.mp4?frame_number=100")

        assert resp.status_code == 400

    async def test_missing_video_returns_404(self, client, tmp_path):
        with patch("main.DATA_DIR", tmp_path):
            resp = await client.get("/frame/nonexistent.mp4?frame_number=0")

        assert resp.status_code == 404


@pytest.mark.anyio
class TestCalibrateHoop:
    async def test_saves_calibration(self, client, tmp_path):
        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            resp = await client.post(
                "/calibrate-hoop",
                json={
                    "video_filename": "game.mp4",
                    "frame_number": 100,
                    "hoop_x": 960.0,
                    "hoop_y": 540.0,
                    "hoop_radius": 50.0,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["video_filename"] == "game.mp4"
        assert data["hoop_x"] == 960.0

    async def test_missing_video_returns_404(self, client, tmp_path):
        with patch("main.DATA_DIR", tmp_path):
            resp = await client.post(
                "/calibrate-hoop",
                json={
                    "video_filename": "nonexistent.mp4",
                    "frame_number": 0,
                    "hoop_x": 100,
                    "hoop_y": 100,
                    "hoop_radius": 30,
                },
            )

        assert resp.status_code == 404

    async def test_get_calibration(self, client, tmp_path):
        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            await client.post(
                "/calibrate-hoop",
                json={
                    "video_filename": "game.mp4",
                    "frame_number": 100,
                    "hoop_x": 960.0,
                    "hoop_y": 540.0,
                    "hoop_radius": 50.0,
                },
            )
            resp = await client.get("/calibrate-hoop/game.mp4")

        assert resp.status_code == 200
        data = resp.json()
        assert data["hoop_x"] == 960.0

    async def test_get_calibration_not_found(self, client):
        resp = await client.get("/calibrate-hoop/nonexistent.mp4")

        assert resp.status_code == 200
        assert resp.json() is None


@pytest.mark.anyio
class TestStartTrim:
    async def test_creates_job(self, client, tmp_path):
        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            resp = await client.post(
                "/trim",
                json={
                    "video_filename": "game.mp4",
                    "yolo_confidence": 0.4,
                    "pre_roll_seconds": 3.0,
                    "post_roll_seconds": 2.0,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["video_filename"] == "game.mp4"
        assert data["status"] in ("queued", "processing")

    async def test_missing_video_returns_404(self, client, tmp_path):
        with patch("main.DATA_DIR", tmp_path):
            resp = await client.post(
                "/trim",
                json={
                    "video_filename": "nonexistent.mp4",
                },
            )

        assert resp.status_code == 404

    async def test_invalid_params_returns_422(self, client):
        resp = await client.post(
            "/trim",
            json={
                "video_filename": "game.mp4",
                "yolo_confidence": 999.0,
            },
        )

        assert resp.status_code == 422


@pytest.mark.anyio
class TestGetJob:
    async def test_returns_existing_job(self, client, tmp_path):
        video_file = tmp_path / "game.mp4"
        video_file.touch()

        with patch("main.DATA_DIR", tmp_path):
            create_resp = await client.post(
                "/trim",
                json={
                    "video_filename": "game.mp4",
                },
            )

        job_id = create_resp.json()["job_id"]
        resp = await client.get(f"/jobs/{job_id}")

        assert resp.status_code == 200
        assert resp.json()["job_id"] == job_id

    async def test_unknown_job_returns_404(self, client):
        resp = await client.get("/jobs/nonexistent-id")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestGetOutput:
    async def test_lists_output_clips(self, client, tmp_path):
        clip_file = tmp_path / "game_clip_001_score_5.0s-15.0s.mp4"
        clip_file.write_bytes(b"\x00" * (2 * 1024 * 1024))

        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.get("/output")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["filename"] == "game_clip_001_score_5.0s-15.0s.mp4"
        assert data[0]["source_video"] == "game.mp4"
        assert data[0]["start_time"] == 5.0
        assert data[0]["end_time"] == 15.0
        assert data[0]["duration"] == 10.0
        assert data[0]["event_type"] == "score"

    async def test_lists_near_miss_clips(self, client, tmp_path):
        clip_file = tmp_path / "game_clip_001_near_miss_5.0s-15.0s.mp4"
        clip_file.write_bytes(b"\x00" * 1024)

        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.get("/output")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["event_type"] == "near_miss"

    async def test_empty_output_dir(self, client, tmp_path):
        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.get("/output")

        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.anyio
class TestGetOutputFile:
    async def test_serves_existing_clip(self, client, tmp_path):
        clip_file = tmp_path / "clip.mp4"
        clip_file.write_bytes(b"\x00\x00\x00\x1c\x66\x74\x79\x70")

        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.get("/output/clip.mp4")

        assert resp.status_code == 200

    async def test_missing_clip_returns_404(self, client, tmp_path):
        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.get("/output/nonexistent.mp4")

        assert resp.status_code == 404


@pytest.mark.anyio
class TestDeleteOutputFile:
    async def test_deletes_existing_clip(self, client, tmp_path):
        clip_file = tmp_path / "clip.mp4"
        clip_file.write_bytes(b"\x00" * 100)

        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.delete("/output/clip.mp4")

        assert resp.status_code == 200
        assert not clip_file.exists()

    async def test_delete_missing_returns_404(self, client, tmp_path):
        with patch("main.OUTPUT_DIR", tmp_path):
            resp = await client.delete("/output/nonexistent.mp4")

        assert resp.status_code == 404
