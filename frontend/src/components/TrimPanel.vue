<template>
  <div id="trim-panel" class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center gap-2 mb-4">
      <div class="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
        <svg class="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      </div>
      <h2 class="text-lg font-bold text-white">Trim Settings</h2>
    </div>

    <div class="flex-1 overflow-y-auto pr-1 space-y-5 min-h-0">
      <!-- No Selection State -->
      <div
        v-if="!store.selectedVideo"
        class="flex flex-col items-center justify-center py-16 text-center"
      >
        <div class="w-16 h-16 rounded-2xl bg-surface-50 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-muted-dark" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
        </div>
        <p class="text-muted text-sm mb-1">No video selected</p>
        <p class="text-muted-dark text-xs">Select a video from the library to configure trimming</p>
      </div>

      <template v-else>
        <!-- Selected Video Player -->
        <div class="glass-card overflow-hidden">
          <div class="relative aspect-video bg-surface-300">
            <video
              :key="store.selectedVideo.filename"
              :src="`http://localhost:8000/videos/stream/${store.selectedVideo.filename}`"
              controls
              preload="metadata"
              class="w-full h-full object-contain bg-black"
              :poster="`http://localhost:8000${store.selectedVideo.thumbnail_url}`"
            />
          </div>
          <div class="p-3">
            <h3 class="text-sm font-bold text-white truncate mb-1.5">{{ store.selectedVideo.filename }}</h3>
            <div class="flex items-center gap-2">
              <span class="badge-accent text-[11px]">{{ formatDuration(store.selectedVideo.duration_seconds) }}</span>
              <span class="badge text-[11px]">{{ store.selectedVideo.resolution }}</span>
              <span class="badge text-[11px]">{{ store.selectedVideo.size_mb }} MB</span>
            </div>
          </div>
        </div>

        <!-- Presets -->
        <div>
          <label class="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-2">Presets</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="preset in presets"
              :key="preset.key"
              :id="`preset-${preset.key}`"
              class="btn-ghost text-xs text-center py-2"
              :class="{ 'ring-1 ring-accent/50 bg-accent/10 text-accent-light': activePreset === preset.key }"
              :disabled="store.isJobRunning"
              @click="applyPreset(preset.key)"
            >
              {{ preset.label }}
            </button>
          </div>
        </div>

        <!-- Parameters -->
        <div class="space-y-4">
          <!-- Activity Threshold -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="activity-threshold" class="text-sm font-medium text-muted-light">Activity Threshold</label>
              <input
                id="activity-threshold-input"
                v-model.number="store.params.activity_threshold"
                type="number"
                step="0.001"
                min="0.001"
                max="0.5"
                class="input-field w-20 text-right text-xs"
                :disabled="store.isJobRunning"
              />
            </div>
            <input
              id="activity-threshold"
              v-model.number="store.params.activity_threshold"
              type="range"
              min="0.001"
              max="0.5"
              step="0.001"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">
              How much movement to detect.
              <span class="text-muted">Low (0.005) = capture all movement · High (0.05) = action plays only</span>
            </p>
          </div>

          <!-- Min Segment Duration -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="min-segment-duration" class="text-sm font-medium text-muted-light">Min Segment Duration</label>
              <div class="flex items-center gap-1">
                <input
                  id="min-segment-duration-input"
                  v-model.number="store.params.min_segment_duration"
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="30"
                  class="input-field w-16 text-right text-xs"
                  :disabled="store.isJobRunning"
                />
                <span class="text-xs text-muted-dark">s</span>
              </div>
            </div>
            <input
              id="min-segment-duration"
              v-model.number="store.params.min_segment_duration"
              type="range"
              min="0.5"
              max="30"
              step="0.5"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Clips shorter than this will be discarded</p>
          </div>

          <!-- Buffer Seconds -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="buffer-seconds" class="text-sm font-medium text-muted-light">Buffer Seconds</label>
              <div class="flex items-center gap-1">
                <input
                  id="buffer-seconds-input"
                  v-model.number="store.params.buffer_seconds"
                  type="number"
                  step="0.5"
                  min="0"
                  max="10"
                  class="input-field w-16 text-right text-xs"
                  :disabled="store.isJobRunning"
                />
                <span class="text-xs text-muted-dark">s</span>
              </div>
            </div>
            <input
              id="buffer-seconds"
              v-model.number="store.params.buffer_seconds"
              type="range"
              min="0"
              max="10"
              step="0.5"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Extra context added before and after each detected segment</p>
          </div>

          <!-- Max Clip Duration -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="max-clip-duration" class="text-sm font-medium text-muted-light">Max Clip Duration</label>
              <div class="flex items-center gap-1">
                <input
                  id="max-clip-duration-input"
                  v-model.number="store.params.max_clip_duration"
                  type="number"
                  step="10"
                  min="10"
                  max="1800"
                  class="input-field w-20 text-right text-xs"
                  :disabled="store.isJobRunning"
                />
                <span class="text-xs text-muted-dark">s</span>
              </div>
            </div>
            <input
              id="max-clip-duration"
              v-model.number="store.params.max_clip_duration"
              type="range"
              min="10"
              max="1800"
              step="10"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">
              Segments longer than this are split into multiple clips.
              <span class="text-muted">Default: 5 min (300s)</span>
            </p>
          </div>

          <!-- Detection Confidence -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="detection-confidence" class="text-sm font-medium text-muted-light">Detection Confidence</label>
              <span class="text-xs font-mono text-muted">{{ store.params.min_detection_confidence.toFixed(2) }}</span>
            </div>
            <input
              id="detection-confidence"
              v-model.number="store.params.min_detection_confidence"
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Minimum confidence for initial pose detection</p>
          </div>

          <!-- Tracking Confidence -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="tracking-confidence" class="text-sm font-medium text-muted-light">Tracking Confidence</label>
              <span class="text-xs font-mono text-muted">{{ store.params.min_tracking_confidence.toFixed(2) }}</span>
            </div>
            <input
              id="tracking-confidence"
              v-model.number="store.params.min_tracking_confidence"
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Minimum confidence for pose tracking between frames</p>
          </div>
        </div>

        <!-- Job Status -->
        <JobStatus v-if="store.activeJob" :job="store.activeJob" />

        <!-- Start Trim Button -->
        <button
          id="start-trim-btn"
          class="btn-primary w-full flex items-center justify-center gap-2 text-sm"
          :disabled="store.isJobRunning"
          @click="store.startTrim()"
        >
          <svg v-if="!store.isJobRunning" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
          </svg>
          <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ store.isJobRunning ? 'Processing…' : 'Start Trimming' }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTrimStore } from '../stores/trimStore'
import JobStatus from './JobStatus.vue'

const store = useTrimStore()

const presets = [
  { key: 'conservative', label: 'Conservative' },
  { key: 'balanced', label: 'Balanced' },
  { key: 'aggressive', label: 'Aggressive' },
]

const activePreset = computed(() => {
  const p = store.params
  const presetValues = {
    conservative: { activity_threshold: 0.01, min_segment_duration: 1.5, buffer_seconds: 2.0 },
    balanced: { activity_threshold: 0.015, min_segment_duration: 2.0, buffer_seconds: 1.5 },
    aggressive: { activity_threshold: 0.03, min_segment_duration: 3.0, buffer_seconds: 1.0 },
  }
  for (const [name, vals] of Object.entries(presetValues)) {
    if (
      p.activity_threshold === vals.activity_threshold &&
      p.min_segment_duration === vals.min_segment_duration &&
      p.buffer_seconds === vals.buffer_seconds
    ) {
      return name
    }
  }
  return null
})

function applyPreset(name) {
  store.applyPreset(name)
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>
