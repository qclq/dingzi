import { http } from './http'

export const systemApi = {
  users: () => http.get('/system/users').then(r => r.data),
  createUser: (body: object) => http.post('/system/users', body).then(r => r.data),
  updateUser: (id: number, body: object) => http.put(`/system/users/${id}`, body).then(r => r.data),
  removeUser: (id: number) => http.delete(`/system/users/${id}`),
  status: (id: number, status: string) => http.post(`/system/users/${id}/status`, { status }).then(r => r.data),
  unlock: (id: number) => http.post(`/system/users/${id}/unlock`).then(r => r.data),
  passwordReset: (id: number) => http.post(`/system/users/${id}/password-reset`).then(r => r.data),
  auditLogs: () => http.get('/system/audit-logs').then(r => r.data),
  systemLogs: () => http.get('/system/system-logs').then(r => r.data),
  logCsv: (kind: 'audit' | 'system') => http.get(`/system/logs/${kind}/csv`, { responseType: 'blob' }).then(r => r.data),
  mesConfig: () => http.get('/system/mes/config').then(r => r.data),
  saveMesConfig: (body: object) => http.put('/system/mes/config', body).then(r => r.data),
  testMes: (body: object) => http.post('/system/mes/test-connection', body).then(r => r.data),
  deliveries: () => http.get('/system/mes/deliveries').then(r => r.data),
  manualReport: (detectionId: number) => http.post('/system/mes/manual-report', null, { params: { detection_id: detectionId }, headers: { 'Idempotency-Key': crypto.randomUUID() } }).then(r => r.data),
  filePolicy: () => http.get('/system/file-policy').then(r => r.data),
  saveFilePolicy: (body: object) => http.put('/system/file-policy', body).then(r => r.data),
  fileUsage: () => http.get('/system/file-policy/usage').then(r => r.data),
  cleanup: () => http.post('/system/file-policy/cleanup').then(r => r.data),
}
