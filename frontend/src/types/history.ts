import type { Defect } from './realtime'

export type DetectionResult = 'PASS' | 'NG'
export type ExportFormat = 'xlsx' | 'pdf'
export type ExportStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface DetectionListItem {
  id: number
  image_id: string
  captured_at: string
  operator: string
  defect_count: number
  result: DetectionResult
}

export interface DetectionPage {
  items: DetectionListItem[]
  total: number
  page: number
  page_size: number
}

export interface DetectionDetail extends DetectionListItem {
  line_id: string
  defects: Defect[]
  image_path: string
  thumbnail_path: string | null
  model_version: string
  config_version: string
  config_snapshot: Record<string, unknown> | null
  inference_ms: number
  mes_status: string
  mes_work_order: string | null
  raw_output: Record<string, unknown> | null
}

export interface SignedFile {
  kind: 'image' | 'thumbnail' | 'json'
  url: string
  expires_at: string
}

export interface ExportJob {
  id: string
  format: ExportFormat
  status: ExportStatus
  record_count: number
  created_at: string
  completed_at: string | null
  expires_at: string | null
  download_url: string | null
  error_message: string | null
}

export interface DetectionQuery {
  start_time?: string
  end_time?: string
  result?: DetectionResult
  operator?: string
  image_id?: string
  line_id?: string
  page: number
  page_size: 20 | 50 | 100
}
