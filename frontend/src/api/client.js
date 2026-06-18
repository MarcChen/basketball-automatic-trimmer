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
