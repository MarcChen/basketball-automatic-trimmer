<template>
  <div id="output-gallery" class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
          <svg class="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <h2 class="text-lg font-bold text-white">Output</h2>
        <span v-if="store.outputClips.length" class="badge text-[11px]">{{ store.outputClips.length }}</span>
      </div>
      <button
        id="refresh-output-btn"
        class="btn-ghost text-xs flex items-center gap-1.5"
        @click="store.fetchOutput()"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto pr-1 space-y-4 min-h-0">
      <!-- Empty State -->
      <div
        v-if="!store.outputClips.length"
        class="flex flex-col items-center justify-center py-16 text-center"
      >
        <div class="w-16 h-16 rounded-2xl bg-surface-50 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-muted-dark" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p class="text-muted text-sm mb-1">No clips yet</p>
        <p class="text-muted-dark text-xs">Select a video and start trimming</p>
      </div>

      <!-- Grouped by Source Video -->
      <div v-for="(clips, source) in store.clipsBySource" :key="source" class="space-y-2">
        <!-- Source Group Header -->
        <button
          class="flex items-center gap-2 w-full text-left group"
          @click="toggleGroup(source)"
        >
          <svg
            class="w-3.5 h-3.5 text-muted transition-transform duration-200"
            :class="{ 'rotate-90': expandedGroups[source] }"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span class="text-xs font-semibold text-muted-light truncate group-hover:text-white transition-colors">
            {{ source }}
          </span>
          <span class="badge text-[10px]">{{ clips.length }}</span>
        </button>

        <!-- Timeline Visualization -->
        <div v-if="expandedGroups[source]" class="ml-5 mb-2">
          <div class="glass-card p-3">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[10px] text-muted-dark uppercase tracking-wider font-medium">Timeline</span>
              <span class="text-[10px] text-muted font-mono">{{ formatTime(getSourceDuration(source, clips)) }}</span>
            </div>
            <!-- Timeline Bar -->
            <div
              class="relative h-6 rounded-md bg-surface-300/80 border border-white/5 overflow-hidden cursor-pointer"
              @click="onTimelineClick($event, source, clips)"
            >
              <!-- Segment highlights -->
              <div
                v-for="clip in clips"
                :key="'tl-' + clip.filename"
                class="absolute top-0 h-full rounded-sm transition-all duration-200"
                :class="[
                  playingClip === clip.filename
                    ? 'bg-accent shadow-[0_0_8px_rgba(249,115,22,0.5)] z-10'
                    : 'bg-accent/50 hover:bg-accent/70'
                ]"
                :style="getSegmentStyle(clip, source, clips)"
                :title="`${formatTime(clip.start_time)} – ${formatTime(clip.end_time)} (${clip.duration}s)`"
              />
            </div>
            <!-- Time markers -->
            <div class="flex items-center justify-between mt-1">
              <span class="text-[9px] text-muted-dark font-mono">0:00</span>
              <span class="text-[9px] text-muted-dark font-mono">{{ formatTime(getSourceDuration(source, clips) / 2) }}</span>
              <span class="text-[9px] text-muted-dark font-mono">{{ formatTime(getSourceDuration(source, clips)) }}</span>
            </div>
          </div>
        </div>

        <!-- Clip Items -->
        <transition-group name="clip" tag="div" class="space-y-2 pl-5">
          <div
            v-for="clip in expandedGroups[source] ? clips : []"
            :key="clip.filename"
            class="glass-card p-3 animate-slide-up transition-all duration-200"
            :class="{ 'ring-1 ring-accent/40': playingClip === clip.filename }"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <p class="text-xs font-mono text-muted-light truncate mb-1.5" :title="clip.filename">
                  {{ clip.filename }}
                </p>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="badge text-[10px]">
                    <svg class="w-2.5 h-2.5 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {{ clip.duration }}s
                  </span>
                  <span class="badge text-[10px]">{{ clip.size_mb }} MB</span>
                  <span class="badge text-[10px] font-mono">
                    {{ formatTime(clip.start_time) }}–{{ formatTime(clip.end_time) }}
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-1 shrink-0">
                <!-- Play / Pause -->
                <button
                  :id="`play-${clip.filename}`"
                  class="p-1.5 rounded-lg transition-colors"
                  :class="playingClip === clip.filename
                    ? 'bg-accent/20 text-accent hover:bg-accent/30'
                    : 'bg-white/5 hover:bg-white/10 text-muted hover:text-white'"
                  :title="playingClip === clip.filename ? 'Stop' : 'Play clip'"
                  @click="togglePlay(clip)"
                >
                  <svg v-if="playingClip !== clip.filename" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <svg v-else class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                  </svg>
                </button>

                <!-- Download -->
                <a
                  :id="`download-${clip.filename}`"
                  :href="`http://localhost:8000${clip.url}`"
                  download
                  class="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-muted hover:text-white transition-colors"
                  title="Download clip"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </a>

                <!-- Delete -->
                <button
                  :id="`delete-${clip.filename}`"
                  class="p-1.5 rounded-lg bg-red-500/5 hover:bg-red-500/15 text-muted hover:text-red-400 transition-colors"
                  title="Delete clip"
                  @click="store.deleteClip(clip.filename)"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Inline Video Player -->
            <transition name="player">
              <div v-if="playingClip === clip.filename" class="mt-3">
                <video
                  ref="videoPlayer"
                  :key="'video-' + clip.filename"
                  :src="`http://localhost:8000${clip.url}`"
                  controls
                  autoplay
                  class="w-full rounded-lg bg-black aspect-video"
                  @ended="playingClip = null"
                />
              </div>
            </transition>
          </div>
        </transition-group>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useTrimStore } from '../stores/trimStore'

const store = useTrimStore()
const expandedGroups = reactive({})
const playingClip = ref(null)

onMounted(() => {
  store.fetchOutput()
})

// When selected video changes, auto-expand its group and collapse others
watch(
  () => store.selectedVideo,
  (newVideo) => {
    if (!newVideo) return
    for (const source of Object.keys(expandedGroups)) {
      expandedGroups[source] = source === newVideo.filename
    }
  }
)

function toggleGroup(source) {
  expandedGroups[source] = !expandedGroups[source]
}

function togglePlay(clip) {
  if (playingClip.value === clip.filename) {
    playingClip.value = null
  } else {
    playingClip.value = clip.filename
  }
}

function getSourceDuration(source, clips) {
  // Try to get source video duration from the scanned videos list
  const sourceVideo = store.videos.find(v => v.filename === source)
  if (sourceVideo) return sourceVideo.duration_seconds

  // Fall back to max end_time from clips
  return Math.max(...clips.map(c => c.end_time), 0)
}

function getSegmentStyle(clip, source, clips) {
  const totalDuration = getSourceDuration(source, clips)
  if (totalDuration <= 0) return { left: '0%', width: '0%' }

  const left = (clip.start_time / totalDuration) * 100
  const width = ((clip.end_time - clip.start_time) / totalDuration) * 100
  return {
    left: `${left}%`,
    width: `${Math.max(width, 0.5)}%`, // Minimum 0.5% so tiny segments are visible
  }
}

function onTimelineClick(event, source, clips) {
  const rect = event.currentTarget.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const pct = clickX / rect.width
  const totalDuration = getSourceDuration(source, clips)
  const clickTime = pct * totalDuration

  // Find which clip this click falls into
  const hit = clips.find(c => clickTime >= c.start_time && clickTime <= c.end_time)
  if (hit) {
    playingClip.value = playingClip.value === hit.filename ? null : hit.filename
  }
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// When new clips arrive, expand the group matching the selected video (or all if none selected)
store.$subscribe((mutation, state) => {
  const groups = {}
  for (const clip of state.outputClips) {
    groups[clip.source_video] = true
  }
  const selectedFilename = store.selectedVideo?.filename
  for (const source of Object.keys(groups)) {
    if (!(source in expandedGroups)) {
      // New group: expand only if it matches the selected video, or if nothing is selected
      expandedGroups[source] = !selectedFilename || source === selectedFilename
    }
  }
})
</script>

<style scoped>
.clip-enter-active {
  transition: all 0.3s ease-out;
}
.clip-leave-active {
  transition: all 0.2s ease-in;
}
.clip-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.clip-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
.player-enter-active {
  transition: all 0.3s ease-out;
}
.player-leave-active {
  transition: all 0.2s ease-in;
}
.player-enter-from {
  opacity: 0;
  max-height: 0;
  transform: scaleY(0.9);
}
.player-leave-to {
  opacity: 0;
  max-height: 0;
  transform: scaleY(0.9);
}
</style>
