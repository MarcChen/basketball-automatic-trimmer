<template>
  <button
    :id="`video-card-${video.filename}`"
    class="glass-card group relative overflow-hidden cursor-pointer transition-all duration-300
           hover:shadow-card-hover hover:-translate-y-1"
    :class="selected
      ? 'ring-2 ring-accent shadow-glow border-accent/30'
      : 'hover:border-white/10'"
    @click="$emit('select', video)"
  >
    <!-- Thumbnail -->
    <div class="relative aspect-video overflow-hidden rounded-t-xl bg-surface-300">
      <img
        :src="`http://localhost:8000${video.thumbnail_url}`"
        :alt="`Thumbnail for ${video.filename}`"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
        @error="handleImageError"
      />

      <!-- Duration Badge -->
      <span class="absolute bottom-2 right-2 badge-accent text-[11px] font-mono shadow-lg">
        {{ formatDuration(video.duration_seconds) }}
      </span>

      <!-- Selected Indicator -->
      <div
        v-if="selected"
        class="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent flex items-center justify-center shadow-glow"
      >
        <svg class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <!-- Hover Overlay -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent
                  opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </div>

    <!-- Info -->
    <div class="p-3 space-y-2">
      <h3 class="text-sm font-semibold text-white truncate" :title="video.filename">
        {{ video.filename }}
      </h3>
      <div class="flex items-center gap-2 flex-wrap">
        <span class="badge text-[11px]">
          <svg class="w-3 h-3 mr-1 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          {{ video.resolution }}
        </span>
        <span class="badge text-[11px]">
          {{ video.size_mb }} MB
        </span>
        <span class="badge text-[11px]">
          {{ video.fps }} fps
        </span>
      </div>
    </div>
  </button>
</template>

<script setup>
defineProps({
  video: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

defineEmits(['select'])

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function handleImageError(e) {
  e.target.style.display = 'none'
}
</script>
