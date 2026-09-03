import { http } from './http'
import type {
  DetectionDetail,
  DetectionPage,
  DetectionQuery,
  ExportFormat,
  ExportJob,
  SignedFile,
} from '@/types/history'

export const historyApi = {
  async list(params: DetectionQuery): Promise<DetectionPage> {
    const response = await http.get<DetectionPage>('/detections', { params })
    return response.data
  },
  async detail(id: number): Promise<DetectionDetail> {
    const response = await http.get<DetectionDetail>(`/detections/${id}`)
    return response.data
  },
  async fileUrl(id: number, kind: SignedFile['kind']): Promise<SignedFile> {
    const response = await http.get<SignedFile>(`/detections/${id}/files/${kind}`)
    return response.data
  },
  async createExport(payload: {
    format: ExportFormat
    detection_ids?: number[]
    start_time?: string
    end_time?: string
    result?: 'PASS' | 'NG'
    operator?: string
    image_id?: string
    line_id?: string
  }): Promise<ExportJob> {
    const response = await http.post<ExportJob>('/exports', payload)
    return response.data
  },
  async exportStatus(id: string): Promise<ExportJob> {
    const response = await http.get<ExportJob>(`/exports/${id}`)
    return response.data
  },
  async linkMesWorkOrder(id: number, mesWorkOrder: string): Promise<DetectionDetail> {
    const response = await http.patch<DetectionDetail>(`/detections/${id}/mes-work-order`, {
      mes_work_order: mesWorkOrder,
    })
    return response.data
  },
}
