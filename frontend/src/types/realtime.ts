export type RealtimeEventType = 'HELLO' | 'PING' | 'PONG' | 'ERROR' | 'FRAME' | 'INFER' | 'DEVICE' | 'ALERT'

export interface Defect { type: 'scratch' | 'pitted_surface'; level: 'minor' | 'severe'; confidence: number; bbox: number[]; width_mm?: number | null; height_mm?: number | null }
export interface Detection { image_id: string; line_id: string; captured_at: string; operator: string; defects: Defect[]; result: 'PASS' | 'NG'; image_path: string; thumbnail_path?: string | null; model_version: string; config_version: string; inference_ms: number; mes_status: string; defect_count?: number }
export interface RealtimeEnvelope { type: RealtimeEventType; event_id: string; sequence: number; occurred_at: string; data: Record<string, unknown> }
export interface Snapshot { line_id: string; latest: Detection | null; events: Record<string, RealtimeEnvelope> }
