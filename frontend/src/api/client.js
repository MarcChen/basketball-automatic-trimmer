import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

export const getVideos = () => api.get('/videos')
export const startTrim = (params) => api.post('/trim', params)
export const getJob = (jobId) => api.get(`/jobs/${jobId}`)
export const getOutput = () => api.get('/output')
export const deleteClip = (filename) => api.delete(`/output/${filename}`)
export const getFrameUrl = (filename, frameNumber) => `${api.defaults.baseURL}/frame/${filename}?frame_number=${frameNumber}`
export const calibrateHoop = (data) => api.post('/calibrate-hoop', data)
export const getCalibration = (filename) => api.get(`/calibrate-hoop/${filename}`)
