import { http } from './http'
import type {
  AnalyticsDistribution,
  AnalyticsHeatmap,
  AnalyticsOverview,
  AnalyticsPeriod,
  AnalyticsTrends,
} from '@/types/analytics'

export interface AnalyticsQuery {
  period: AnalyticsPeriod
  start_time?: string
  end_time?: string
  line_id?: string
}

export const analyticsApi = {
  async overview(params: AnalyticsQuery): Promise<AnalyticsOverview> {
    const response = await http.get<AnalyticsOverview>('/analytics/overview', { params })
    return response.data
  },
  async trends(params: AnalyticsQuery): Promise<AnalyticsTrends> {
    const response = await http.get<AnalyticsTrends>('/analytics/trends', { params })
    return response.data
  },
  async distribution(params: AnalyticsQuery): Promise<AnalyticsDistribution> {
    const response = await http.get<AnalyticsDistribution>('/analytics/defect-distribution', { params })
    return response.data
  },
  async heatmap(params: AnalyticsQuery): Promise<AnalyticsHeatmap> {
    const response = await http.get<AnalyticsHeatmap>('/analytics/heatmap', { params })
    return response.data
  },
}
