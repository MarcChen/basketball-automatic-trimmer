<template>
  <div class="min-h-screen bg-surface-400 flex flex-col">
    <!-- Header -->
    <header class="sticky top-0 z-50 bg-surface-400/80 backdrop-blur-xl border-b border-white/5">
      <div class="max-w-[1800px] mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <!-- Logo -->
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-orange-600 flex items-center justify-center shadow-glow">
            <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="none" stroke="currentColor" stroke-width="0.5"/>
              <path d="M2 12h20M12 2c2.5 2.5 4 6 4 10s-1.5 7.5-4 10M12 2c-2.5 2.5-4 6-4 10s1.5 7.5 4 10" fill="none" stroke="currentColor" stroke-width="0.8"/>
            </svg>
          </div>
          <div>
            <h1 class="text-base font-bold text-white tracking-tight">
              Basketball <span class="text-gradient">Trimmer</span>
            </h1>
            <p class="text-[10px] text-muted-dark leading-none">AI-powered highlight extraction</p>
          </div>
        </div>

        <!-- Status Indicator -->
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-100/50 border border-white/5">
            <div class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span class="text-[11px] text-muted">Backend connected</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 max-w-[1800px] w-full mx-auto px-4 sm:px-6 py-6">
      <div class="grid grid-cols-1 md:grid-cols-12 gap-6 h-[calc(100vh-5.5rem)]">
        <!-- Left Panel — Video Library -->
        <div class="md:col-span-4 lg:col-span-3 glass-panel p-4 overflow-hidden flex flex-col">
          <VideoLibrary />
        </div>

        <!-- Center Panel — Trim Settings -->
        <div class="md:col-span-4 lg:col-span-5 glass-panel p-4 overflow-hidden flex flex-col">
          <TrimPanel />
        </div>

        <!-- Right Panel — Output Gallery -->
        <div class="md:col-span-4 lg:col-span-4 glass-panel p-4 overflow-hidden flex flex-col">
          <OutputGallery />
        </div>
      </div>
    </main>

    <!-- Toast Notifications -->
    <div class="fixed bottom-6 right-6 z-[100] space-y-2 pointer-events-none">
      <transition-group name="toast">
        <div
          v-for="toast in store.toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-card-hover backdrop-blur-xl
                 border animate-slide-up max-w-sm"
          :class="{
            'bg-emerald-500/15 border-emerald-500/20 text-emerald-300': toast.type === 'success',
            'bg-red-500/15 border-red-500/20 text-red-300': toast.type === 'error',
            'bg-surface-50/90 border-white/10 text-muted-light': toast.type === 'info',
          }"
        >
          <!-- Icon -->
          <svg v-if="toast.type === 'success'" class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else-if="toast.type === 'error'" class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>

          <span class="text-sm font-medium">{{ toast.message }}</span>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { useTrimStore } from './stores/trimStore'
import VideoLibrary from './components/VideoLibrary.vue'
import TrimPanel from './components/TrimPanel.vue'
import OutputGallery from './components/OutputGallery.vue'

const store = useTrimStore()
</script>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
</style>
