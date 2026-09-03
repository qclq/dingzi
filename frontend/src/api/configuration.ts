import { http } from './http'
import type { ConfigDraft, ConfigType, ConfigVersion } from '@/types/configuration'

const confirmed = (action: 'save' | 'reset' | 'publish' | 'hot-switch' | 'rollback') => ({ 'X-Confirm-Action': action })

export const configurationApi = {
  async get<T>(type: ConfigType): Promise<ConfigDraft<T>> { return (await http.get<ConfigDraft<T>>(`/configs/${type}`)).data },
  async save<T>(type: ConfigType, value: T, draftRevision: number): Promise<ConfigDraft<T>> {
    return (await http.put<ConfigDraft<T>>(`/configs/${type}`, { value, draft_revision: draftRevision }, { headers: confirmed('save') })).data
  },
  async reset<T>(type: ConfigType): Promise<ConfigDraft<T>> { return (await http.post<ConfigDraft<T>>(`/configs/${type}/reset`, {}, { headers: confirmed('reset') })).data },
  async validate(): Promise<{ valid: boolean; errors: string[]; draft_revision: number }> { return (await http.post('/configs/validate')).data },
  async publish(draftRevision: number): Promise<ConfigVersion> {
    return (await http.post<ConfigVersion>('/configs/publish', { draft_revision: draftRevision }, { headers: { ...confirmed('publish'), 'Idempotency-Key': crypto.randomUUID() } })).data
  },
  async hotSwitch(): Promise<{ config_version: string; model_version: string }> { return (await http.post('/configs/model/hot-switch', {}, { headers: confirmed('hot-switch') })).data },
  async rollback(version: string, draftRevision: number): Promise<ConfigVersion> {
    return (await http.post<ConfigVersion>(`/configs/versions/${version}/rollback`, { draft_revision: draftRevision }, { headers: { ...confirmed('rollback'), 'Idempotency-Key': crypto.randomUUID() } })).data
  },
  async versions(): Promise<ConfigVersion[]> { return (await http.get<ConfigVersion[]>('/configs/versions')).data },
}
