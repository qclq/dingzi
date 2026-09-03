import { ref } from 'vue'
import { defineStore } from 'pinia'
import { http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { Detection, RealtimeEnvelope, Snapshot } from '@/types/realtime'

export const useRealtimeStore = defineStore('realtime', () => {
  const lineId = ref('line-1')
  const connectionState = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const lastDetection = ref<Detection | null>(null)
  const lastFrame = ref<{ image_id: string; image_path: string } | null>(null)
  const lastAlert = ref<Record<string, unknown> | null>(null)
  const lastDevice = ref<Record<string, unknown> | null>(null)
  const lastSequence = ref(0)
  const seenEvents = new Set<string>()
  let socket: WebSocket | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1_000
  let manuallyClosed = false

  function applyEvent(event: RealtimeEnvelope): void {
    if (seenEvents.has(event.event_id) || event.sequence <= lastSequence.value) return
    seenEvents.add(event.event_id)
    if (seenEvents.size > 500) seenEvents.delete(seenEvents.values().next().value as string)
    lastSequence.value = event.sequence
    if (event.type === 'FRAME') lastFrame.value = event.data as { image_id: string; image_path: string }
    if (event.type === 'INFER') lastDetection.value = event.data as unknown as Detection
    if (event.type === 'ALERT') lastAlert.value = event.data
    if (event.type === 'DEVICE') lastDevice.value = event.data
    if (event.type === 'HELLO') {
      const snapshot = (event.data.snapshot as Snapshot | undefined)
      if (snapshot?.latest) lastDetection.value = snapshot.latest
    }
  }

  async function restoreSnapshot(): Promise<void> {
    const response = await http.get<Snapshot>('/realtime/snapshot', { params: { line_id: lineId.value } })
    if (response.data.latest) lastDetection.value = response.data.latest
    Object.values(response.data.events ?? {}).forEach(applyEvent)
  }

  function stopTimers(): void {
    if (pingTimer) clearInterval(pingTimer)
    if (reconnectTimer) clearTimeout(reconnectTimer)
    pingTimer = null
    reconnectTimer = null
  }

  function scheduleReconnect(): void {
    if (manuallyClosed || reconnectTimer) return
    reconnectTimer = setTimeout(() => { reconnectTimer = null; connect(lineId.value) }, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, 30_000)
  }

  function connect(targetLineId = lineId.value): void {
    manuallyClosed = false
    lineId.value = targetLineId
    socket?.close()
    stopTimers()
    const auth = useAuthStore()
    if (!auth.accessToken) return
    connectionState.value = 'connecting'
    void restoreSnapshot().catch(() => undefined)
    const base = import.meta.env.VITE_WS_BASE_URL ?? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
    const token = encodeURIComponent(auth.accessToken)
    socket = new WebSocket(`${base.replace(/\/$/, '')}/ws/realtime?line_id=${encodeURIComponent(targetLineId)}&access_token=${token}`)
    socket.onopen = () => {
      connectionState.value = 'connected'
      reconnectDelay = 1_000
      pingTimer = setInterval(() => socket?.send(JSON.stringify({ type: 'PING' })), 20_000)
    }
    socket.onmessage = (message) => {
      try { applyEvent(JSON.parse(message.data) as RealtimeEnvelope) } catch { /* ignore malformed events */ }
    }
    socket.onerror = () => socket?.close()
    socket.onclose = () => {
      stopTimers()
      connectionState.value = 'disconnected'
      scheduleReconnect()
    }
  }

  function disconnect(): void {
    manuallyClosed = true
    stopTimers()
    socket?.close()
    socket = null
    connectionState.value = 'disconnected'
  }

  return { lineId, connectionState, lastDetection, lastFrame, lastAlert, lastDevice, lastSequence, connect, disconnect, restoreSnapshot }
})
