export type ConfigType = 'defect_thresholds' | 'judgment_rules' | 'roi' | 'calibration' | 'camera_light' | 'model'

export interface ConfigDraft<T = Record<string, unknown>> {
  config_type: ConfigType
  value: T
  draft_revision: number
  published_version: string | null
}

export interface ThresholdItem { type: 'scratch' | 'pitted_surface'; severity_threshold_mm: number; minor_enabled: boolean; severe_enabled: boolean }
export interface JudgmentRule { type: 'scratch' | 'pitted_surface'; level: 'minor' | 'severe'; enabled: boolean; max_count: number }
export interface RoiArea { x: number; y: number; width: number; height: number }
export interface CameraProfile { id: string; product_model: string; exposure: number; gain: number; trigger_mode: string; light_brightness: number }

export interface ConfigVersion { version: string; payload: Record<string, unknown>; published_at: string; published_by: number | null }
