import { defineStore } from 'pinia'
import { getVideos, startTrim, getJob, getOutput, deleteClip, getCalibration } from '../api/client'

const PRESETS = {
  tight: {
    yolo_confidence: 0.4,
    near_miss_multiplier: 1.3,
    pre_roll_seconds: 2.0,
    post_roll_seconds: 1.0,
    min_segment_duration: 1.0,
    max_clip_duration: 20.0,
    include_near_misses: true,
  },
  standard: {
    yolo_confidence: 0.4,
    near_miss_multiplier: 1.3,
    pre_roll_seconds: 3.0,
    post_roll_seconds: 2.0,
    min_segment_duration: 1.5,
    max_clip_duration: 30.0,
    include_near_misses: true,
  },
  wide: {
    yolo_confidence: 0.3,
    near_miss_multiplier: 1.5,
    pre_roll_seconds: 5.0,
    post_roll_seconds: 3.0,
    min_segment_duration: 2.0,
    max_clip_duration: 60.0,
    include_near_misses: true,
  },
  scores_only: {
    yolo_confidence: 0.5,
    near_miss_multiplier: 1.2,
    pre_roll_seconds: 3.0,
    post_roll_seconds: 2.0,
    min_segment_duration: 1.5,
    max_clip_duration: 30.0,
    include_near_misses: false,
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
    calibration: null,
    params: { ...PRESETS.standard },
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

    scoreCount: (state) => {
      return state.outputClips.filter((c) => c.event_type === 'score').length
    },

    nearMissCount: (state) => {
      return state.outputClips.filter((c) => c.event_type === 'near_miss').length
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
      this.calibration = null
      this.fetchCalibration(video.filename)
    },

    async fetchCalibration(filename) {
      try {
        const { data } = await getCalibration(filename)
        if (data) {
          this.calibration = data
          this.params.hoop_x = data.hoop_x
          this.params.hoop_y = data.hoop_y
          this.params.hoop_radius = data.hoop_radius
        }
      } catch (err) {
        this.calibration = null
      }
    },

    setCalibration(cal) {
      this.calibration = cal
      this.params.hoop_x = cal.hoop_x
      this.params.hoop_y = cal.hoop_y
      this.params.hoop_radius = cal.hoop_radius
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
            const total = data.clips_exported.length
            const scores = data.scores_found || 0
            const nearMisses = data.near_misses_found || 0
            this.addToast(
              `Done! ${total} clip${total !== 1 ? 's' : ''} (${scores} scores, ${nearMisses} near-misses)`,
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
