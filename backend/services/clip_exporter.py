import os
from pathlib import Path

import ffmpeg

from models.schemas import OutputClip


def build_clip_filename(source_filename: str, idx: int, start: float, end: float) -> str:
    basename = Path(source_filename).stem
    return f"{basename}_clip_{idx:03d}_{start:.1f}s-{end:.1f}s.mp4"


def export_clips(
    input_path: str,
    segments: list[tuple[float, float]],
    output_dir: str,
    source_filename: str,
) -> list[OutputClip]:
    os.makedirs(output_dir, exist_ok=True)

    clips = []
    for i, (start, end) in enumerate(segments, start=1):
        clip_filename = build_clip_filename(source_filename, i, start, end)
        clip_path = os.path.join(output_dir, clip_filename)

        try:
            (ffmpeg.input(input_path, ss=start, to=end).output(clip_path, c="copy").run(quiet=True))
        except ffmpeg.Error as e:
            raise RuntimeError(
                f"ffmpeg failed cutting {source_filename} segment {start:.1f}-{end:.1f}: {e.stderr}"
            ) from e

        file_size = os.path.getsize(clip_path)
        size_mb = round(file_size / (1024 * 1024), 2)

        clips.append(
            OutputClip(
                filename=clip_filename,
                source_video=source_filename,
                start_time=start,
                end_time=end,
                duration=round(end - start, 2),
                size_mb=size_mb,
                url=f"/output/{clip_filename}",
            )
        )

    return clips
