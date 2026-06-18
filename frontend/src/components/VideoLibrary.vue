<template>
  <div id="video-library" class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
          <svg class="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </div>
        <h2 class="text-lg font-bold text-white">Videos</h2>
        <span v-if="store.videos.length" class="badge text-[11px]">{{ store.videos.length }}</span>
      </div>
      <button
        id="refresh-videos-btn"
        class="btn-ghost text-xs flex items-center gap-1.5"
        :class="{ 'animate-spin': store.loading }"
        :disabled="store.loading"
        @click="store.fetchVideos()"
      >
        <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': store.loading }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto pr-1 space-y-3 min-h-0">
      <!-- Loading Skeletons -->
      <template v-if="store.loading && !store.videos.length">
        <div v-for="i in 3" :key="i" class="glass-card overflow-hidden">
          <div class="aspect-video skeleton" />
          <div class="p-3 space-y-2">
            <div class="h-4 w-3/4 skeleton" />
            <div class="flex gap-2">
              <div class="h-5 w-16 skeleton" />
              <div class="h-5 w-12 skeleton" />
            </div>
          </div>
        </div>
      </template>

      <!-- Empty State -->
      <div
        v-else-if="!store.videos.length && !store.loading"
        class="flex flex-col items-center justify-center py-12 text-center"
      >
        <div class="w-16 h-16 rounded-2xl bg-surface-50 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-muted-dark" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
          </svg>
        </div>
        <p class="text-muted text-sm mb-1">No videos found</p>
        <p class="text-muted-dark text-xs">
          Drop <code class="text-accent/80 font-mono">.mp4</code> files into the
          <code class="text-accent/80 font-mono">data/</code> folder
        </p>
      </div>

      <!-- Video Cards -->
      <VideoCard
        v-for="video in store.videos"
        :key="video.filename"
        :video="video"
        :selected="store.selectedVideo?.filename === video.filename"
        class="animate-fade-in"
        @select="store.selectVideo(video)"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useTrimStore } from '../stores/trimStore'
import VideoCard from './VideoCard.vue'

const store = useTrimStore()

onMounted(() => {
  store.fetchVideos()
})
</script>
