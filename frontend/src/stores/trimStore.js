import { defineStore } from 'pinia'
import { getVideos, startTrim, getJob, getOutput, deleteClip } from '../api/client'

const PRESETS = {
  conservative: {
    activity_threshold: 0.01,
    min_segment_duration: 1.5,
    buffer_seconds: 2.0,
    min_detection_confidence: 0.5,
    min_tracking_confidence: 0.5,
    max_clip_duration: 300,
  },
  balanced: {
    activity_threshold: 0.015,
    min_segment_duration: 2.0,
    buffer_seconds: 1.5,
    min_detection_confidence: 0.5,
    min_tracking_confidence: 0.5,
    max_clip_duration: 300,
  },
  aggressive: {
    activity_threshold: 0.03,
    min_segment_duration: 3.0,
    buffer_seconds: 1.0,
    min_detection_confidence: 0.5,
    min_tracking_confidence: 0.5,
    max_clip_duration: 300,
  },
}

export const useTrimStore = defineStore('trim', {
  state: () => ({
    videos: [],
    selectedVideo: null,
    activeJob: null,
    pollInterval: null,
    outputClips: [],
    loading: false,
    error: null,
    toasts: [],
    params: { ...PRESETS.balanced },
  }),

  getters: {
    isJobRunning: (state) => {
      return state.activeJob && !['done', 'error'].includes(state.activeJob.status)
    },

    clipsBySource: (state) => {
      const groups = {}
      for (const clip of state.outputClips) {
        if (!groups[clip.source_video]) {
          groups[clip.source_video] = []
        }
        groups[clip.source_video].push(clip)
      }
      return groups
    },
  },

  actions: {
    async fetchVideos() {
      this.loading = true
      this.error = null
      try {
        const { data } = await getVideos()
        this.videos = data
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to load videos'
        this.addToast(this.error, 'error')
      } finally {
        this.loading = false
      }
    },

    selectVideo(video) {
      this.selectedVideo = video
    },

    async startTrim() {
      if (!this.selectedVideo || this.isJobRunning) return

      this.error = null
      try {
        const { data } = await startTrim({
          video_filename: this.selectedVideo.filename,
          ...this.params,
        })
        this.activeJob = data
        this.startPolling(data.job_id)
      } catch (err) {
        const msg = err.response?.data?.detail || 'Failed to start trim job'
        this.error = msg
        this.addToast(msg, 'error')
      }
    },

    startPolling(jobId) {
      this.stopPolling()
      this.pollInterval = setInterval(async () => {
        try {
          const { data } = await getJob(jobId)
          this.activeJob = data

          if (data.status === 'done') {
            this.stopPolling()
            this.addToast(
              `Done! ${data.clips_exported.length} clip${data.clips_exported.length !== 1 ? 's' : ''} extracted`,
              'success'
            )
            await this.fetchOutput()
          } else if (data.status === 'error') {
            this.stopPolling()
            this.addToast(data.error_message || 'Trim job failed', 'error')
          }
        } catch (err) {
          this.stopPolling()
          this.addToast('Lost connection to job', 'error')
        }
      }, 1000)
    },

    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    async fetchOutput() {
      try {
        const { data } = await getOutput()
        this.outputClips = data
      } catch (err) {
        this.addToast('Failed to load output clips', 'error')
      }
    },

    async deleteClip(filename) {
      try {
        await deleteClip(filename)
        this.outputClips = this.outputClips.filter((c) => c.filename !== filename)
        this.addToast(`Deleted ${filename}`, 'info')
      } catch (err) {
        this.addToast(err.response?.data?.detail || 'Failed to delete clip', 'error')
      }
    },

    applyPreset(name) {
      const preset = PRESETS[name]
      if (preset) {
        Object.assign(this.params, preset)
      }
    },

    addToast(message, type = 'info') {
      const id = Date.now() + Math.random()
      this.toasts.push({ id, message, type })
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id)
      }, 4000)
    },
  },
})
