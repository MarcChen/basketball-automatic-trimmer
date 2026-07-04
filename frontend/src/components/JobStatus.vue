<template>
  <div id="job-status" class="glass-card p-4 space-y-3 animate-slide-up">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div
          class="w-2.5 h-2.5 rounded-full"
          :class="{
            'bg-amber-400 animate-pulse': isProcessing,
            'bg-emerald-400': job.status === 'done',
            'bg-red-400': job.status === 'error',
            'bg-muted-dark animate-pulse': job.status === 'queued',
          }"
        />
        <span class="text-sm font-semibold" :class="statusColor">
          {{ statusLabel }}
        </span>
      </div>
      <span v-if="isProcessing" class="text-xs font-mono text-muted">
        {{ job.progress_pct }}%
      </span>
    </div>

    <div v-if="isProcessing || job.status === 'queued'" class="relative h-2 rounded-full bg-surface-300 overflow-hidden">
      <div
        class="absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out"
        :class="job.status === 'queued'
          ? 'bg-gradient-to-r from-muted-dark via-muted to-muted-dark bg-[length:200%_100%] animate-progress w-full'
          : 'bg-gradient-to-r from-accent to-accent-light'"
        :style="job.status !== 'queued' ? { width: job.progress_pct + '%' } : {}"
      />
    </div>

    <div v-else-if="job.status === 'done'" class="h-2 rounded-full bg-emerald-500/30 overflow-hidden">
      <div class="h-full w-full rounded-full bg-emerald-400" />
    </div>

    <div v-else-if="job.status === 'error'" class="h-2 rounded-full bg-red-500/30 overflow-hidden">
      <div class="h-full w-full rounded-full bg-red-400" />
    </div>

    <div v-if="isProcessing || job.status === 'done'" class="flex items-center gap-4 text-xs text-muted">
      <span v-if="job.segments_found > 0" class="flex items-center gap-1">
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ job.segments_found }} segment{{ job.segments_found !== 1 ? 's' : '' }} found
      </span>
      <span v-if="job.scores_found > 0" class="flex items-center gap-1 text-emerald-400">
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        {{ job.scores_found }} score{{ job.scores_found !== 1 ? 's' : '' }}
      </span>
      <span v-if="job.near_misses_found > 0" class="flex items-center gap-1 text-amber-400">
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        {{ job.near_misses_found }} near-miss{{ job.near_misses_found !== 1 ? 'es' : '' }}
      </span>
    </div>

    <div v-if="job.status === 'error' && job.error_message" class="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
      <p class="text-xs text-red-400 font-mono break-all">{{ job.error_message }}</p>
    </div>

    <div v-if="job.status === 'done' && job.clips_exported.length" class="space-y-1.5">
      <p class="text-xs text-muted-dark font-medium uppercase tracking-wider">Exported clips</p>
      <div
        v-for="clip in job.clips_exported"
        :key="clip"
        class="flex items-center gap-2 text-xs text-muted-light bg-surface-300/30 rounded-lg px-3 py-2"
      >
        <svg v-if="clip.includes('_score_')" class="w-3 h-3 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <svg v-else class="w-3 h-3 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span class="truncate font-mono">{{ clip }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  job: { type: Object, required: true },
})

const isProcessing = computed(() => props.job.status === 'processing')

const statusLabel = computed(() => {
  switch (props.job.status) {
    case 'queued': return 'Queued…'
    case 'processing': return 'Detecting ball & analyzing trajectory…'
    case 'done': return 'Done ✓'
    case 'error': return 'Error ✗'
    default: return props.job.status
  }
})

const statusColor = computed(() => {
  switch (props.job.status) {
    case 'queued': return 'text-muted'
    case 'processing': return 'text-amber-400'
    case 'done': return 'text-emerald-400'
    case 'error': return 'text-red-400'
    default: return 'text-muted'
  }
})
</script>
