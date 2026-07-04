from pathlib import Path

import cv2


def extract_frame(video_path: str, frame_number: int, output_dir: str) -> str:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")

    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret or frame is None:
            raise ValueError(f"Failed to read frame {frame_number} from {video_path}")
    finally:
        cap.release()

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stem = Path(video_path).stem
    output_path = str(Path(output_dir) / f"{stem}_frame_{frame_number}.jpg")
    cv2.imwrite(output_path, frame)
    return output_path
