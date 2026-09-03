export type AnalyticsPeriod = 'today' | '7d' | '30d' | '90d' | 'custom'

export interface AnalyticsOverview {
  total_detections: number
  ng_detections: number
  defect_rate: number
  rate_definition: string
  start: string
  end: string
}

export interface AnalyticsTrendItem {
  bucket_start: string
  total_detections: number
  ng_detections: number
  defect_rate: number
  scratch_count: number
  pitted_surface_count: number
}

export interface AnalyticsTrends {
  granularity: string
  start: string
  end: string
  items: AnalyticsTrendItem[]
}

export interface AnalyticsDistributionItem {
  type: 'scratch' | 'pitted_surface'
  level: 'minor' | 'severe'
  count: number
  percentage: number
}

export interface AnalyticsDistribution {
  start: string
  end: string
  total_defects: number
  items: AnalyticsDistributionItem[]
}

export interface AnalyticsHeatmapCell {
  angle_bucket: number
  axial_bucket: number
  count: number
}

export interface AnalyticsHeatmap {
  start: string
  end: string
  angle_bin_degrees: number
  axial_bin_count: number
  coordinate_basis: string
  items: AnalyticsHeatmapCell[]
}
