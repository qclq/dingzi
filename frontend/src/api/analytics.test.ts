// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { analyticsApi } from '@/api/analytics'
import { http } from '@/api/http'

const originalAdapter = http.defaults.adapter

function response(config: InternalAxiosRequestConfig, data: unknown): AxiosResponse {
  return { data, status: 200, statusText: 'OK', headers: {}, config }
}

afterEach(() => { http.defaults.adapter = originalAdapter })

describe('analytics API client', () => {
  it('sends the selected period and line filter to trends', async () => {
    let request: InternalAxiosRequestConfig | undefined
    const adapter: AxiosAdapter = async (config) => {
      request = config
      return response(config, { granularity: 'day', start: '2026-01-01T00:00:00Z', end: '2026-01-01T23:59:59Z', items: [] })
    }
    http.defaults.adapter = adapter

    await analyticsApi.trends({ period: '30d', line_id: 'line-2' })

    expect(request?.url).toBe('/analytics/trends')
    expect(request?.params).toEqual({ period: '30d', line_id: 'line-2' })
  })

  it('uses the dedicated distribution endpoint for the type-level pie chart', async () => {
    let request: InternalAxiosRequestConfig | undefined
    const adapter: AxiosAdapter = async (config) => {
      request = config
      return response(config, { start: '2026-01-01T00:00:00Z', end: '2026-01-01T23:59:59Z', total_defects: 0, items: [] })
    }
    http.defaults.adapter = adapter

    await analyticsApi.distribution({ period: 'custom', start_time: '2026-01-01T00:00:00Z', end_time: '2026-01-02T00:00:00Z' })

    expect(request?.url).toBe('/analytics/defect-distribution')
    expect(request?.params?.period).toBe('custom')
  })
})
