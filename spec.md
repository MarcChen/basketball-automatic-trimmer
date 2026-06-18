# Basketball Video Trimmer — Agent Build Spec

> **Stack:** Vue 3 (Vite) frontend · FastAPI backend · MediaPipe + OpenCV pose detection · FFmpeg cutting  
> **Purpose:** System prompt for an AI coding agent to build this app end-to-end.

***

## 1. Project Overview

Build a full-stack web application that scans a local `data/` folder for video files, displays them to the user, and lets the user trigger automatic intelligent trimming based on MediaPipe pose-activity detection. Trimmed clips are saved to an `output/` folder. The user controls all detection parameters from the frontend.

***

## 2. Repository Structure

```
basketball-trimmer/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── services/
│   │   ├── video_scanner.py     # Scans data/ folder for video files
│   │   ├── pose_detector.py     # MediaPipe pose activity scoring
│   │   └── clip_exporter.py     # FFmpeg clip cutting logic
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── data/                    # Input videos (user places files here)
│   ├── output/                  # Auto-created; trimmed clips saved here
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── VideoLibrary.vue     # Grid of available videos
│   │   │   ├── VideoCard.vue        # Single video card with thumbnail + metadata
│   │   │   ├── TrimPanel.vue        # Parameters form + trim button
│   │   │   ├── JobStatus.vue        # Real-time progress of active trim job
│   │   │   └── OutputGallery.vue    # List of exported clips
│   │   ├── stores/
│   │   │   └── trimStore.js         # Pinia store for job state
│   │   └── api/
│   │       └── client.js            # Axios API wrapper
│   ├── vite.config.js
│   └── package.json
├── docker-compose.yml           # Optional: containerized setup
└── README.md
```

***

## 3. Backend — FastAPI

### 3.1 Dependencies (`requirements.txt`)

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
mediapipe>=0.10.14
opencv-python-headless>=4.9.0
ffmpeg-python>=0.2.0
python-multipart>=0.0.9
pydantic>=2.0.0
aiofiles>=23.0.0
```

### 3.2 Pydantic Schemas (`models/schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional

class VideoMeta(BaseModel):
    filename: str
    path: str
    size_mb: float
    duration_seconds: float
    fps: float
    resolution: str           # e.g. "1920x1080"
    thumbnail_url: str        # served as /thumbnails/{filename}.jpg

class TrimParams(BaseModel):
    video_filename: str
    activity_threshold: float = Field(default=0.015, ge=0.001, le=0.5,
        description="Landmark velocity delta to classify frame as active")
    min_segment_duration: float = Field(default=2.0, ge=0.5, le=30.0,
        description="Minimum clip length in seconds to keep")
    buffer_seconds: float = Field(default=1.5, ge=0.0, le=10.0,
        description="Seconds of context to add before/after each active segment")
    min_detection_confidence: float = Field(default=0.5, ge=0.1, le=1.0)
    min_tracking_confidence: float = Field(default=0.5, ge=0.1, le=1.0)

class TrimJob(BaseModel):
    job_id: str
    video_filename: str
    status: str               # "queued" | "processing" | "done" | "error"
    progress_pct: int = 0     # 0–100
    segments_found: int = 0
    clips_exported: list[str] = []
    error_message: Optional[str] = None

class OutputClip(BaseModel):
    filename: str
    source_video: str
    start_time: float
    end_time: float
    duration: float
    size_mb: float
    url: str                  # served as /output/{filename}
```

### 3.3 API Endpoints (`main.py`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/videos` | Scan `data/` and return list of `VideoMeta` |
| `GET` | `/thumbnails/{filename}` | Serve auto-generated JPEG thumbnail |
| `POST` | `/trim` | Start async trim job, return `job_id` |
| `GET` | `/jobs/{job_id}` | Poll job status and progress |
| `GET` | `/output` | List all clips in `output/` folder |
| `GET` | `/output/{filename}` | Stream/download a trimmed clip |
| `DELETE` | `/output/{filename}` | Delete a specific output clip |

**CORS:** Enable for `http://localhost:5173` (Vite dev server).

**Static file serving:** Mount `output/` as `/output` and auto-generate thumbnails on `/videos` call if they don't exist (save to `backend/.thumbnails/`).

### 3.4 Video Scanner (`services/video_scanner.py`)

- Scan `data/` recursively for files with extensions: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- For each file, extract metadata using OpenCV: duration, fps, resolution
- Auto-generate thumbnail: seek to 10% of duration, grab frame, save as JPEG to `.thumbnails/`
- Return list of `VideoMeta`

### 3.5 Pose Detector (`services/pose_detector.py`)

```python
# Core logic — agent must implement this function
def analyze_video(
    video_path: str,
    params: TrimParams,
    progress_callback: callable   # called with int 0-100 as frames are processed
) -> list[tuple[float, float]]:   # returns list of (start_sec, end_sec) segments
```

**Algorithm:**
1. Open video with OpenCV, read frame by frame
2. For each frame, run `mp.solutions.pose.Pose.process(rgb_frame)`
3. If pose landmarks detected AND previous landmarks exist: compute mean Euclidean distance of all 33 landmark (x, y) pairs between current and previous frame → this is the `activity_score`
4. If no landmarks detected: `activity_score = 0`
5. Classify frame as `active` if `activity_score > params.activity_threshold`
6. After all frames: merge consecutive `active` frames into segments
7. Apply `buffer_seconds` padding before/after each segment (clamped to video bounds)
8. Filter out segments shorter than `params.min_segment_duration`
9. Merge overlapping segments after padding
10. Call `progress_callback(int(frame_index / total_frames * 100))` every 30 frames

### 3.6 Clip Exporter (`services/clip_exporter.py`)

```python
def export_clips(
    input_path: str,
    segments: list[tuple[float, float]],
    output_dir: str,
    source_filename: str
) -> list[OutputClip]:
```

- For each segment `(start, end)`: run `ffmpeg -ss {start} -to {end} -i {input} -c copy {output}`
- Output filename pattern: `{source_basename}_clip_{idx:03d}_{start:.1f}s-{end:.1f}s.mp4`
- Use `ffmpeg-python` library (not subprocess)
- Return list of `OutputClip` with metadata

### 3.7 Async Job Management

- Use a simple in-memory dict `jobs: dict[str, TrimJob]` (keyed by UUID)
- On `POST /trim`: create job entry, launch `asyncio.create_task` wrapping the sync detector in `loop.run_in_executor` (ThreadPoolExecutor)
- Progress updates write directly to the in-memory dict
- `GET /jobs/{job_id}` returns current state; frontend polls every 1 second

***

## 4. Frontend — Vue 3 + Vite

### 4.1 Dependencies (`package.json`)

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "vue-router": "^4.3.0"
  },
  "devDependencies": {
    "vite": "^5.2.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

**Styling:** Tailwind CSS. Dark theme by default (dark background `#0f0f0f`, accent orange `#f97316` — fits the basketball theme).

### 4.2 App Layout (`App.vue`)

Three-column layout on desktop, stacked on mobile:
- **Left panel (30%):** `VideoLibrary` — scrollable list of available videos
- **Center panel (40%):** `TrimPanel` — parameters form + active job progress
- **Right panel (30%):** `OutputGallery` — list of exported clips

### 4.3 VideoLibrary Component (`VideoLibrary.vue`)

- On mount: call `GET /videos`, display grid of `VideoCard`
- Each card shows: thumbnail image, filename, duration badge, resolution badge, file size
- Clicking a card selects it (highlighted border) and populates the `TrimPanel`
- "Refresh" button re-fetches the video list
- Empty state: "Drop .mp4 files into the `data/` folder"

### 4.4 TrimPanel Component (`TrimPanel.vue`)

Displays when a video is selected. Contains:

**Selected video info:**
- Thumbnail preview (larger)
- Filename, duration, resolution

**Parameters form (all with labels, default values, and range indicators):**

| Parameter | UI Control | Default | Range |
|-----------|-----------|---------|-------|
| Activity Threshold | Range slider + number input | 0.015 | 0.001 – 0.5 |
| Min Segment Duration | Range slider + number input | 2.0s | 0.5 – 30s |
| Buffer Seconds | Range slider + number input | 1.5s | 0 – 10s |
| Min Detection Confidence | Range slider | 0.5 | 0.1 – 1.0 |
| Min Tracking Confidence | Range slider | 0.5 | 0.1 – 1.0 |

- **Parameter helper text** below each slider explaining what it does in plain language
- **"Preset" buttons**: "Conservative" (threshold 0.01, buffer 2s), "Balanced" (defaults), "Aggressive" (threshold 0.03, buffer 1s) — clicking fills all fields
- **"Start Trimming" button**: orange, full-width, disabled while a job is running

### 4.5 JobStatus Component (`JobStatus.vue`)

Shown inside TrimPanel when a job is active or just completed:

- Animated progress bar (0–100%)
- Status label: "Analyzing frames…" / "Exporting clips…" / "Done ✓" / "Error ✗"
- Segments found count (updates live)
- On completion: display list of clip filenames with durations
- On error: display error message in red

**Polling logic:** every 1000ms call `GET /jobs/{job_id}`, stop when status is `done` or `error`.

### 4.6 OutputGallery Component (`OutputGallery.vue`)

- On mount and after each completed job: call `GET /output`
- Group clips by source video (collapsible sections)
- Each clip shows: filename, duration, size, start–end timestamps
- **Download button**: direct link to `/output/{filename}`
- **Delete button**: calls `DELETE /output/{filename}`, removes from list with fade animation
- Empty state: "No clips yet. Select a video and start trimming."

### 4.7 Pinia Store (`stores/trimStore.js`)

```javascript
export const useTrimStore = defineStore('trim', {
  state: () => ({
    videos: [],           // VideoMeta[]
    selectedVideo: null,  // VideoMeta | null
    activeJob: null,      // TrimJob | null
    pollInterval: null,   // setInterval handle
    outputClips: [],      // OutputClip[]
    params: {
      activity_threshold: 0.015,
      min_segment_duration: 2.0,
      buffer_seconds: 1.5,
      min_detection_confidence: 0.5,
      min_tracking_confidence: 0.5,
    }
  }),
  actions: {
    async fetchVideos() { ... },
    selectVideo(video) { ... },
    async startTrim() { ... },
    startPolling(jobId) { ... },
    stopPolling() { ... },
    async fetchOutput() { ... },
    async deleteClip(filename) { ... },
    applyPreset(name) { ... }  // 'conservative' | 'balanced' | 'aggressive'
  }
})
```

### 4.8 API Client (`api/client.js`)

```javascript
import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export const getVideos = () => api.get('/videos')
export const startTrim = (params) => api.post('/trim', params)
export const getJob = (jobId) => api.get(`/jobs/${jobId}`)
export const getOutput = () => api.get('/output')
export const deleteClip = (filename) => api.delete(`/output/${filename}`)
```

***

## 5. UX Details

- **Responsive breakpoints:** single-column on mobile (<768px), three-column on desktop
- **Slider + number input sync:** editing the number input updates the slider and vice versa
- **Visual feedback:** slider track fills with orange up to current value
- **Tooltips on hover** for each parameter label explaining the technical meaning
- **Activity Threshold guidance:** show a small legend: "Low (0.005) = capture all movement · High (0.05) = action plays only"
- **Disabled state:** all form controls disabled while a job is running on the selected video
- **Toast notifications:** on job complete ("X clips extracted"), on error, on clip deleted

***

## 6. Running the App

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev        # runs on http://localhost:5173
```

**Place `.mp4` files in `backend/data/` before starting.**

***

## 7. Agent Instructions

Build this app file by file, in this order:

1. `backend/models/schemas.py`
2. `backend/services/video_scanner.py`
3. `backend/services/pose_detector.py`
4. `backend/services/clip_exporter.py`
5. `backend/main.py`
6. `frontend/` scaffold (Vite + Vue + Pinia + Tailwind)
7. `frontend/src/api/client.js`
8. `frontend/src/stores/trimStore.js`
9. `frontend/src/components/VideoCard.vue`
10. `frontend/src/components/VideoLibrary.vue`
11. `frontend/src/components/JobStatus.vue`
12. `frontend/src/components/TrimPanel.vue`
13. `frontend/src/components/OutputGallery.vue`
14. `frontend/src/App.vue`

After each file: verify imports resolve, types match schemas, and API paths are consistent between frontend `client.js` and backend route definitions.

**Do not use localStorage.** Job state lives in the Pinia store (in-memory). Backend job state lives in the in-memory dict.

**Error handling:** all API calls must have try/catch. Backend endpoints must return structured `{"detail": "..."}` on 4xx/5xx. Frontend must display errors inline (not just console.log).