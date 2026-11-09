<template>
  <canvas
    ref="canvasRef"
    class="pointer-events-none absolute inset-0 h-full w-full"
    aria-hidden="true"
  />
</template>

<script lang="ts" setup>
const canvasRef = ref<HTMLCanvasElement | null>(null)

const GAP = 26
const RADIUS = 170
const BASE_RADIUS = 1.3
const BRAND = '253, 208, 10'

let ctx: CanvasRenderingContext2D | null = null
let raf = 0
let w = 0
let h = 0
let rgb = '0, 0, 0'
let baseAlpha = 0.2
let dirty = true
let reduceMotion = false

const target = { x: -9999, y: -9999 }
const smooth = { x: -9999, y: -9999 }

let resizeObserver: ResizeObserver | null = null
let themeObserver: MutationObserver | null = null

function readTheme() {
  const root = document.documentElement
  const dark = root.classList.contains('dark') || root.getAttribute('data-theme') === 'dark'
  rgb = dark ? '255, 255, 255' : '0, 0, 0'
  baseAlpha = dark ? 0.18 : 0.2
  dirty = true
}

function resize() {
  const el = canvasRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = rect.width
  h = rect.height
  el.width = Math.round(w * dpr)
  el.height = Math.round(h * dpr)
  ctx = el.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
  dirty = true
}

function draw() {
  if (!ctx) return
  ctx.clearRect(0, 0, w, h)

  const offsetX = (w % GAP) / 2 || GAP / 2
  const offsetY = (h % GAP) / 2 || GAP / 2

  for (let y = offsetY; y < h; y += GAP) {
    for (let x = offsetX; x < w; x += GAP) {
      const dx = x - smooth.x
      const dy = y - smooth.y
      const dist = Math.hypot(dx, dy)

      let px = x
      let py = y
      let r = BASE_RADIUS

      if (dist < RADIUS) {
        const t = 1 - dist / RADIUS
        const push = t * t * 18
        const safe = dist || 1
        px += (dx / safe) * push
        py += (dy / safe) * push
        r = BASE_RADIUS + t * 2.8
        ctx.fillStyle = `rgba(${BRAND}, ${0.35 + t * 0.65})`
      }
      else {
        ctx.fillStyle = `rgba(${rgb}, ${baseAlpha})`
      }

      ctx.beginPath()
      ctx.arc(px, py, r, 0, Math.PI * 2)
      ctx.fill()
    }
  }
}

function tick() {
  const diffX = target.x - smooth.x
  const diffY = target.y - smooth.y

  if (Math.abs(diffX) > 0.1 || Math.abs(diffY) > 0.1) {
    smooth.x += diffX * 0.18
    smooth.y += diffY * 0.18
    dirty = true
  }

  if (dirty) {
    draw()
    dirty = false
  }
  raf = requestAnimationFrame(tick)
}

function onPointerMove(e: PointerEvent) {
  const el = canvasRef.value
  if (!el || reduceMotion) return
  const rect = el.getBoundingClientRect()
  target.x = e.clientX - rect.left
  target.y = e.clientY - rect.top
  if (smooth.x === -9999) {
    smooth.x = target.x
    smooth.y = target.y
  }
}

function onLeave() {
  target.x = target.y = smooth.x = smooth.y = -9999
  dirty = true
}

onMounted(() => {
  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resize()
  readTheme()

  window.addEventListener('pointermove', onPointerMove, { passive: true })
  document.documentElement.addEventListener('mouseleave', onLeave)

  resizeObserver = new ResizeObserver(resize)
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)

  themeObserver = new MutationObserver(readTheme)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class', 'data-theme'],
  })

  raf = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('pointermove', onPointerMove)
  document.documentElement.removeEventListener('mouseleave', onLeave)
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
})
</script>