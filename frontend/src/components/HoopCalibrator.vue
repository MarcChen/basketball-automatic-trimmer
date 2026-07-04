<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <label class="text-xs font-medium text-muted-dark uppercase tracking-wider">Hoop Calibration</label>
      <span v-if="calibration" class="badge-accent text-[11px]">Calibrated</span>
    </div>

    <div class="relative glass-card overflow-hidden">
      <canvas
        ref="canvasRef"
        class="w-full block cursor-crosshair"
        :style="{ maxHeight: '300px' }"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseUp"
      />
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-surface-300/80">
        <svg class="w-6 h-6 text-accent animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    </div>

    <p class="text-[11px] text-muted-dark">
      Click on the hoop rim center in the frame, then drag to set the scoring zone radius.
    </p>

    <div v-if="calibration" class="flex items-center gap-2">
      <span class="badge text-[11px]">X: {{ calibration.hoop_x.toFixed(0) }}</span>
      <span class="badge text-[11px]">Y: {{ calibration.hoop_y.toFixed(0) }}</span>
      <span class="badge text-[11px]">R: {{ calibration.hoop_radius.toFixed(0) }}px</span>
      <button class="btn-ghost text-[11px] py-1 px-2 ml-auto" @click="reset">Reset</button>
    </div>

    <div class="flex items-center gap-2">
      <button
        class="btn-ghost text-xs flex items-center gap-1.5"
        :disabled="loading"
        @click="loadFrame"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Load Frame
      </button>
      <button
        v-if="calibration"
        class="btn-primary text-xs flex items-center gap-1.5 ml-auto"
        :disabled="saving"
        @click="saveCalibration"
      >
        <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ saving ? 'Saving...' : 'Save Calibration' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  videoFilename: { type: String, required: true },
  frameNumber: { type: Number, default: 100 },
})

const emit = defineEmits(['calibrated'])

const API_BASE = 'http://localhost:8000'

const canvasRef = ref(null)
const imageRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const isDragging = ref(false)
const startPoint = ref(null)
const currentPoint = ref(null)
const calibration = ref(null)

const naturalWidth = ref(1920)
const naturalHeight = ref(1080)

const displayScale = computed(() => {
  const canvas = canvasRef.value
  if (!canvas || !naturalWidth.value) return 1
  return naturalWidth.value / canvas.clientWidth
})

onMounted(() => {
  loadFrame()
})

async function loadFrame() {
  loading.value = true
  try {
    const url = `${API_BASE}/frame/${props.videoFilename}?frame_number=${props.frameNumber}`
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      imageRef.value = img
      naturalWidth.value = img.naturalWidth
      naturalHeight.value = img.naturalHeight
      drawCanvas()
      loading.value = false
    }
    img.onerror = () => {
      loading.value = false
    }
    img.src = url
  } catch {
    loading.value = false
  }
}

function drawCanvas() {
  const canvas = canvasRef.value
  if (!canvas || !imageRef.value) return

  canvas.width = imageRef.value.naturalWidth
  canvas.height = imageRef.value.naturalHeight

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(imageRef.value, 0, 0)

  if (startPoint.value) {
    const center = startPoint.value
    const radius = currentPoint.value
      ? distance(center, currentPoint.value)
      : 0

    ctx.beginPath()
    ctx.arc(center.x, center.y, radius, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.9)'
    ctx.lineWidth = 3
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(center.x, center.y, radius * 1.3, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.4)'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 4])
    ctx.stroke()
    ctx.setLineDash([])

    const cross = 12
    ctx.beginPath()
    ctx.moveTo(center.x - cross, center.y)
    ctx.lineTo(center.x + cross, center.y)
    ctx.moveTo(center.x, center.y - cross)
    ctx.lineTo(center.x, center.y + cross)
    ctx.strokeStyle = 'rgba(249, 115, 22, 1)'
    ctx.lineWidth = 2
    ctx.stroke()
  }
}

function distance(p1, p2) {
  return Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
}

function getCanvasCoords(event) {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  return {
    x: (event.clientX - rect.left) * scaleX,
    y: (event.clientY - rect.top) * scaleY,
  }
}

function handleMouseDown(event) {
  const pt = getCanvasCoords(event)
  startPoint.value = pt
  currentPoint.value = pt
  isDragging.value = true
  drawCanvas()
}

function handleMouseMove(event) {
  if (!isDragging.value) return
  currentPoint.value = getCanvasCoords(event)
  drawCanvas()
}

function handleMouseUp() {
  if (!isDragging.value) return
  isDragging.value = false

  if (startPoint.value && currentPoint.value) {
    const radius = distance(startPoint.value, currentPoint.value)
    calibration.value = {
      hoop_x: startPoint.value.x,
      hoop_y: startPoint.value.y,
      hoop_radius: radius,
    }
  }
}

function reset() {
  startPoint.value = null
  currentPoint.value = null
  calibration.value = null
  drawCanvas()
}

async function saveCalibration() {
  if (!calibration.value) return
  saving.value = true
  try {
    const resp = await fetch(`${API_BASE}/calibrate-hoop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_filename: props.videoFilename,
        frame_number: props.frameNumber,
        hoop_x: calibration.value.hoop_x,
        hoop_y: calibration.value.hoop_y,
        hoop_radius: calibration.value.hoop_radius,
      }),
    })
    if (resp.ok) {
      emit('calibrated', calibration.value)
    }
  } finally {
    saving.value = false
  }
}
</script>
