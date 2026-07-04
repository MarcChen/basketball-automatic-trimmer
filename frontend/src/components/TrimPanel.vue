<template>
  <div id="trim-panel" class="flex flex-col h-full">
    <div class="flex items-center gap-2 mb-4">
      <div class="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
        <svg class="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      </div>
      <h2 class="text-lg font-bold text-white">Trim Settings</h2>
    </div>

    <div class="flex-1 overflow-y-auto pr-1 space-y-5 min-h-0">
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

        <div>
          <label class="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-2">Presets</label>
          <div class="grid grid-cols-2 gap-2">
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

        <HoopCalibrator
          :video-filename="store.selectedVideo.filename"
          @calibrated="onCalibrated"
        />

        <div class="space-y-4">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="yolo-confidence" class="text-sm font-medium text-muted-light">Ball Detection Confidence</label>
              <span class="text-xs font-mono text-muted">{{ store.params.yolo_confidence.toFixed(2) }}</span>
            </div>
            <input
              id="yolo-confidence"
              v-model.number="store.params.yolo_confidence"
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Minimum YOLO confidence for basketball detection</p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="near-miss-multiplier" class="text-sm font-medium text-muted-light">Near-Miss Zone</label>
              <span class="text-xs font-mono text-muted">{{ store.params.near_miss_multiplier.toFixed(1) }}x</span>
            </div>
            <input
              id="near-miss-multiplier"
              v-model.number="store.params.near_miss_multiplier"
              type="range"
              min="1.0"
              max="3.0"
              step="0.1"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">
              Near-miss zone = hoop radius × this value.
              <span class="text-muted">1.0 = only scores · 2.0 = generous near-miss capture</span>
            </p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="pre-roll" class="text-sm font-medium text-muted-light">Pre-Roll (lead-up)</label>
              <div class="flex items-center gap-1">
                <input
                  id="pre-roll-input"
                  v-model.number="store.params.pre_roll_seconds"
                  type="number"
                  step="0.5"
                  min="0"
                  max="15"
                  class="input-field w-16 text-right text-xs"
                  :disabled="store.isJobRunning"
                />
                <span class="text-xs text-muted-dark">s</span>
              </div>
            </div>
            <input
              id="pre-roll"
              v-model.number="store.params.pre_roll_seconds"
              type="range"
              min="0"
              max="15"
              step="0.5"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Context captured before each event (pass, approach, jump)</p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="post-roll" class="text-sm font-medium text-muted-light">Post-Roll (aftermath)</label>
              <div class="flex items-center gap-1">
                <input
                  id="post-roll-input"
                  v-model.number="store.params.post_roll_seconds"
                  type="number"
                  step="0.5"
                  min="0"
                  max="15"
                  class="input-field w-16 text-right text-xs"
                  :disabled="store.isJobRunning"
                />
                <span class="text-xs text-muted-dark">s</span>
              </div>
            </div>
            <input
              id="post-roll"
              v-model.number="store.params.post_roll_seconds"
              type="range"
              min="0"
              max="15"
              step="0.5"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Context captured after each event (celebration, rebound)</p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="min-segment-duration" class="text-sm font-medium text-muted-light">Min Clip Duration</label>
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

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label for="max-clip-duration" class="text-sm font-medium text-muted-light">Max Clip Duration</label>
              <div class="flex items-center gap-1">
                <input
                  id="max-clip-duration-input"
                  v-model.number="store.params.max_clip_duration"
                  type="number"
                  step="5"
                  min="5"
                  max="600"
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
              min="5"
              max="600"
              step="5"
              class="slider-accent"
              :disabled="store.isJobRunning"
            />
            <p class="text-[11px] text-muted-dark mt-1">Segments longer than this are split into multiple clips</p>
          </div>

          <div class="flex items-center justify-between py-2">
            <div>
              <label for="include-near-misses" class="text-sm font-medium text-muted-light">Include Near-Misses</label>
              <p class="text-[11px] text-muted-dark mt-0.5">Also clip near-miss attempts, not just scores</p>
            </div>
            <button
              id="include-near-misses"
              class="relative w-10 h-5 rounded-full transition-colors duration-200"
              :class="store.params.include_near_misses ? 'bg-accent' : 'bg-surface-300'"
              :disabled="store.isJobRunning"
              @click="store.params.include_near_misses = !store.params.include_near_misses"
            >
              <span
                class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200"
                :class="store.params.include_near_misses ? 'translate-x-5' : 'translate-x-0.5'"
              />
            </button>
          </div>
        </div>

        <JobStatus v-if="store.activeJob" :job="store.activeJob" />

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
import HoopCalibrator from './HoopCalibrator.vue'

const store = useTrimStore()

const presets = [
  { key: 'tight', label: 'Tight' },
  { key: 'standard', label: 'Standard' },
  { key: 'wide', label: 'Wide' },
  { key: 'scores_only', label: 'Scores Only' },
]

const activePreset = computed(() => {
  const p = store.params
  const presetValues = {
    tight: { pre_roll_seconds: 2.0, post_roll_seconds: 1.0, min_segment_duration: 1.0, include_near_misses: true },
    standard: { pre_roll_seconds: 3.0, post_roll_seconds: 2.0, min_segment_duration: 1.5, include_near_misses: true },
    wide: { pre_roll_seconds: 5.0, post_roll_seconds: 3.0, min_segment_duration: 2.0, include_near_misses: true },
    scores_only: { pre_roll_seconds: 3.0, post_roll_seconds: 2.0, min_segment_duration: 1.5, include_near_misses: false },
  }
  for (const [name, vals] of Object.entries(presetValues)) {
    if (
      p.pre_roll_seconds === vals.pre_roll_seconds &&
      p.post_roll_seconds === vals.post_roll_seconds &&
      p.min_segment_duration === vals.min_segment_duration &&
      p.include_near_misses === vals.include_near_misses
    ) {
      return name
    }
  }
  return null
})

function applyPreset(name) {
  store.applyPreset(name)
}

function onCalibrated(cal) {
  store.setCalibration(cal)
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>
