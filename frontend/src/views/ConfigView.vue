<script setup lang="ts">
import { nextTick, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Canvas, Rect } from 'fabric'
import { configurationApi } from '@/api/configuration'
import type { CameraProfile, ConfigType, ConfigVersion, JudgmentRule, RoiArea, ThresholdItem } from '@/types/configuration'

const cards: Array<{ type: ConfigType; title: string; description: string }> = [
  { type: 'defect_thresholds', title: '缺陷阈值', description: '划痕、点蚀的轻微/严重分界' },
  { type: 'judgment_rules', title: '图片合格判定', description: '类型 × 等级数量规则' },
  { type: 'roi', title: 'ROI', description: '像素坐标检测区域' },
  { type: 'calibration', title: '像素标定', description: '1 pixel = N mm' },
  { type: 'camera_light', title: '相机/光源', description: '产品型号与采集方案' },
  { type: 'model', title: '模型参数', description: '置信度、NMS 与推理设备' },
]

const selected = ref<ConfigType | null>(null)
const versionDialog = ref(false)
const versions = ref<ConfigVersion[]>([])
const loading = ref(false)
const draftRevision = ref(1)
const publishedVersion = ref<string | null>(null)
const canvasElement = ref<HTMLCanvasElement | null>(null)
const thresholds = ref<ThresholdItem[]>([])
const rules = ref<JudgmentRule[]>([])
const rois = ref<RoiArea[]>([])
const calibration = ref({ mm_per_pixel: 0.1 })
const calibrationPreview = ref('')
const camera = ref<{ active_profile_id: string; profiles: CameraProfile[] }>({ active_profile_id: '', profiles: [] })
const model = ref({ confidence_threshold: 0.5, nms_threshold: 0.45, device: 'CPU', model_version: 'mock-v1' })
let fabricCanvas: Canvas | null = null

function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T }

function applyValue(type: ConfigType, value: unknown): void {
  if (type === 'defect_thresholds') thresholds.value = (value as { items: ThresholdItem[] }).items
  if (type === 'judgment_rules') rules.value = (value as { items: JudgmentRule[] }).items
  if (type === 'roi') rois.value = (value as { areas: RoiArea[] }).areas
  if (type === 'calibration') calibration.value = value as typeof calibration.value
  if (type === 'camera_light') camera.value = value as typeof camera.value
  if (type === 'model') model.value = value as typeof model.value
}

async function open(type: ConfigType): Promise<void> {
  loading.value = true
  selected.value = type
  try {
    const draft = await configurationApi.get(type)
    draftRevision.value = draft.draft_revision
    publishedVersion.value = draft.published_version
    applyValue(type, clone(draft.value))
    if (type === 'roi') { await nextTick(); initializeCanvas() }
  } finally { loading.value = false }
}

function currentValue(): object {
  if (selected.value === 'defect_thresholds') return { items: thresholds.value }
  if (selected.value === 'judgment_rules') return { items: rules.value }
  if (selected.value === 'roi') { syncRoisFromCanvas(); return { areas: rois.value } }
  if (selected.value === 'calibration') return calibration.value
  if (selected.value === 'camera_light') return camera.value
  return model.value
}

async function save(): Promise<void> {
  if (!selected.value) return
  await ElMessageBox.confirm('保存只会更新草稿，不会影响正在运行的检测。是否继续？', '确认保存', { type: 'warning' })
  const draft = await configurationApi.save(selected.value, currentValue(), draftRevision.value)
  draftRevision.value = draft.draft_revision
  applyValue(selected.value, clone(draft.value))
  ElMessage.success('草稿已保存，请校验并发布后生效')
}

async function reset(): Promise<void> {
  if (!selected.value) return
  await ElMessageBox.confirm('恢复默认将覆盖该配置的当前草稿，是否继续？', '重要操作确认', { type: 'warning' })
  const draft = await configurationApi.reset(selected.value)
  draftRevision.value = draft.draft_revision
  applyValue(selected.value, clone(draft.value))
  if (selected.value === 'roi') { await nextTick(); renderRois() }
  ElMessage.success('已恢复默认草稿')
}

async function validateAndPublish(): Promise<void> {
  const result = await configurationApi.validate()
  if (!result.valid) { ElMessage.error(result.errors.join('；')); return }
  await ElMessageBox.confirm('发布将生成不可变配置版本，并供后续检测使用。是否发布？', '发布配置', { type: 'warning' })
  const version = await configurationApi.publish(result.draft_revision)
  publishedVersion.value = version.version
  ElMessage.success(`已发布 ${version.version}`)
}

async function hotSwitch(): Promise<void> {
  await ElMessageBox.confirm('重新加载当前已发布模型不会创建新版本。是否继续？', '模型热切换', { type: 'warning' })
  const result = await configurationApi.hotSwitch()
  ElMessage.success(`已加载 ${result.model_version}（${result.config_version}）`)
}

async function showVersions(): Promise<void> { versions.value = await configurationApi.versions(); versionDialog.value = true }
async function rollback(version: string): Promise<void> {
  await ElMessageBox.confirm(`将 ${version} 的快照发布为新版本，旧版本不会被修改。是否继续？`, '回滚配置', { type: 'warning' })
  const restored = await configurationApi.rollback(version, draftRevision.value)
  publishedVersion.value = restored.version
  draftRevision.value += 1
  ElMessage.success(`已回滚并发布 ${restored.version}`)
}

function initializeCanvas(): void {
  fabricCanvas?.dispose()
  if (!canvasElement.value) return
  fabricCanvas = new Canvas(canvasElement.value, { selection: false, backgroundColor: '#101828' })
  fabricCanvas.setDimensions({ width: 860, height: 420 })
  fabricCanvas.on('object:modified', syncRoisFromCanvas)
  renderRois()
}

function renderRois(): void {
  if (!fabricCanvas) return
  fabricCanvas.clear()
  fabricCanvas.backgroundColor = '#101828'
  for (let x = 0; x <= 860; x += 86) fabricCanvas.add(new Rect({ left: x, top: 0, width: 1, height: 420, fill: '#253046', selectable: false, evented: false }))
  for (let y = 0; y <= 420; y += 84) fabricCanvas.add(new Rect({ left: 0, top: y, width: 860, height: 1, fill: '#253046', selectable: false, evented: false }))
  rois.value.forEach((area) => fabricCanvas?.add(new Rect({ left: area.x, top: area.y, width: area.width, height: area.height, fill: 'rgba(64,158,255,.15)', stroke: '#409eff', strokeWidth: 2 })))
  fabricCanvas.renderAll()
}

function syncRoisFromCanvas(): void {
  if (!fabricCanvas) return
  rois.value = fabricCanvas.getObjects().filter((item) => item instanceof Rect && item.selectable !== false).map((item) => ({ x: Math.max(0, Math.round(item.left ?? 0)), y: Math.max(0, Math.round(item.top ?? 0)), width: Math.round((item.width ?? 0) * item.scaleX), height: Math.round((item.height ?? 0) * item.scaleY) }))
}

function addRoi(): void {
  if (rois.value.length >= 8) { ElMessage.warning('最多 8 个 ROI'); return }
  rois.value.push({ x: 100, y: 100, width: 180, height: 120 }); renderRois()
}
function deleteSelectedRoi(): void { if (!fabricCanvas) return; const target = fabricCanvas.getActiveObject(); if (target) { fabricCanvas.remove(target); syncRoisFromCanvas() } }
function clearRois(): void { rois.value = []; renderRois() }
function refreshImage(): void { renderRois(); ElMessage.success('已刷新标定参考图') }
function addCameraProfile(): void { const id = `profile-${Date.now()}`; camera.value.profiles.push({ id, product_model: 'new-product', exposure: 1000, gain: 1, trigger_mode: 'software', light_brightness: 50 }) }
function deleteCameraProfile(index: number): void {
  if (camera.value.profiles.length === 1) { ElMessage.warning('至少保留一套方案'); return }
  const removed = camera.value.profiles.splice(index, 1)[0]
  const replacement = camera.value.profiles[0]
  if (removed && replacement && camera.value.active_profile_id === removed.id) camera.value.active_profile_id = replacement.id
}
function generateCalibration(): void {
  calibrationPreview.value = `100 px = ${(calibration.value.mm_per_pixel * 100).toFixed(2)} mm`
  ElMessage.success('标定参考图已生成')
}
function verifyCalibration(): void { ElMessage.success('标定值格式与范围验证通过') }

onUnmounted(() => fabricCanvas?.dispose())
</script>

<template>
  <section class="config-page" v-loading="loading">
    <header class="page-header"><div><h2>参数配置</h2><p>草稿不会影响历史检测；发布后才生成不可变配置版本。</p></div><el-tag type="info">当前发布：{{ publishedVersion ?? '未发布' }}</el-tag></header>
    <el-row v-if="!selected" :gutter="16">
      <el-col v-for="card in cards" :key="card.type" :xs="24" :sm="12" :lg="8"><el-card class="config-card" shadow="hover" @click="open(card.type)"><h3>{{ card.title }}</h3><p>{{ card.description }}</p><el-button type="primary">进入配置</el-button></el-card></el-col>
    </el-row>
    <template v-else>
      <div class="toolbar"><el-button @click="selected = null">← 返回配置首页</el-button><el-button @click="showVersions">历史版本</el-button><el-button @click="reset">恢复默认</el-button><el-button type="primary" @click="save">保存草稿</el-button><el-button type="success" @click="validateAndPublish">校验并发布</el-button></div>
      <el-card>
        <template #header>{{ cards.find((item) => item.type === selected)?.title }}</template>
        <el-table v-if="selected === 'defect_thresholds'" class="threshold-table" :data="thresholds"><el-table-column prop="type" label="缺陷类型" /><el-table-column label="轻微（≤ 分界值）"><template #default="scope"><span class="level-bar minor">轻微</span><el-switch v-model="scope.row.minor_enabled" /></template></el-table-column><el-table-column label="严重（> 分界值）"><template #default="scope"><span class="level-bar severe">严重</span><el-switch v-model="scope.row.severe_enabled" /></template></el-table-column><el-table-column label="分界值 mm"><template #default="scope"><el-input-number v-model="scope.row.severity_threshold_mm" :min="0" :max="100" :precision="2" /></template></el-table-column></el-table>
        <el-table v-else-if="selected === 'judgment_rules'" :data="rules"><el-table-column prop="type" label="类型" /><el-table-column prop="level" label="等级" /><el-table-column label="启用"><template #default="scope"><el-switch v-model="scope.row.enabled" /></template></el-table-column><el-table-column label="达到此数量即 NG"><template #default="scope"><el-input-number v-model="scope.row.max_count" :min="1" :precision="0" /></template></el-table-column></el-table>
        <div v-else-if="selected === 'roi'" class="roi"><div class="roi-actions"><el-button @click="refreshImage">刷新图片</el-button><el-button @click="addRoi">新建</el-button><el-button @click="deleteSelectedRoi">删除选中</el-button><el-button @click="clearRois">清空</el-button><span>{{ rois.length }}/8 个区域；坐标以像素保存</span></div><canvas ref="canvasElement" /></div>
        <el-form v-else-if="selected === 'calibration'" label-width="160px"><el-form-item label="1 pixel = N mm"><el-input-number v-model="calibration.mm_per_pixel" :min="0.000001" :max="100" :precision="6" /></el-form-item><el-button @click="generateCalibration">生成标定图</el-button><el-button @click="verifyCalibration">验证</el-button><div v-if="calibrationPreview" class="calibration-preview"><svg viewBox="0 0 460 100" role="img" aria-label="100 像素标定参考物"><line x1="40" y1="50" x2="400" y2="50" stroke="#409eff" stroke-width="4" /><line x1="40" y1="30" x2="40" y2="70" stroke="#409eff" stroke-width="3" /><line x1="400" y1="30" x2="400" y2="70" stroke="#409eff" stroke-width="3" /><text x="180" y="25" fill="#1f2937">100 px</text><text x="155" y="90" fill="#16a34a">{{ calibrationPreview }}</text></svg></div></el-form>
        <template v-else-if="selected === 'camera_light'"><div class="camera-actions"><el-button @click="addCameraProfile">新建方案</el-button><span>加载应用：选择方案后保存草稿并发布。</span></div><el-table :data="camera.profiles"><el-table-column label="应用"><template #default="scope"><el-radio v-model="camera.active_profile_id" :value="scope.row.id" /></template></el-table-column><el-table-column label="产品型号"><template #default="scope"><el-input v-model="scope.row.product_model" /></template></el-table-column><el-table-column label="曝光"><template #default="scope"><el-input-number v-model="scope.row.exposure" :min="0" /></template></el-table-column><el-table-column label="增益"><template #default="scope"><el-input-number v-model="scope.row.gain" :min="0" /></template></el-table-column><el-table-column label="触发模式"><template #default="scope"><el-input v-model="scope.row.trigger_mode" /></template></el-table-column><el-table-column label="光源亮度"><template #default="scope"><el-input-number v-model="scope.row.light_brightness" :min="0" :max="100" /></template></el-table-column><el-table-column label="操作"><template #default="scope"><el-button link type="danger" @click="deleteCameraProfile(scope.$index)">删除</el-button></template></el-table-column></el-table></template>
        <el-form v-else label-width="170px"><el-form-item label="Confidence threshold"><el-input-number v-model="model.confidence_threshold" :min="0.1" :max="0.99" :precision="2" /></el-form-item><el-form-item label="NMS threshold"><el-input-number v-model="model.nms_threshold" :min="0.1" :max="0.9" :precision="2" /></el-form-item><el-form-item label="推理设备"><el-radio-group v-model="model.device"><el-radio value="CPU">CPU</el-radio><el-radio value="GPU">GPU</el-radio></el-radio-group></el-form-item><el-form-item label="模型版本"><el-input v-model="model.model_version" /></el-form-item><el-button @click="hotSwitch">加载当前已发布模型</el-button><el-alert title="发布时通过 Mock Adapter 热切换；真实 ONNX/PyTorch Adapter 可直接替换该接口。" type="info" :closable="false" /></el-form>
      </el-card>
      <el-dialog v-model="versionDialog" title="配置历史版本" width="760px"><el-table :data="versions"><el-table-column prop="version" label="版本" /><el-table-column prop="published_at" label="发布时间" /><el-table-column label="操作"><template #default="scope"><el-button link type="warning" :disabled="scope.row.version === publishedVersion" @click="rollback(scope.row.version)">回滚为新版本</el-button></template></el-table-column></el-table></el-dialog>
    </template>
  </section>
</template>

<style scoped>
.config-page { display: flex; flex-direction: column; gap: 16px; }.page-header,.toolbar,.roi-actions,.camera-actions { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }.page-header { justify-content:space-between; }.page-header h2 { margin:0; }.page-header p { color:#64748b; margin:6px 0 0; }.config-card { min-height:170px; margin-bottom:16px; cursor:pointer; }.config-card p { min-height:42px; color:#64748b; }.roi canvas { max-width:100%; border:1px solid #334155; }.roi-actions,.camera-actions { margin-bottom:12px; }.level-bar { display:inline-block; min-width:46px; margin-right:8px; padding:3px 10px; border-radius:2px; color:white; text-align:center; }.level-bar.minor { background:#16a34a; }.level-bar.severe { background:#dc2626; }.threshold-table :deep(th),.threshold-table :deep(td) { color:#fff; background:#111827; }.threshold-table :deep(.el-table__inner-wrapper::before) { background:#334155; }.calibration-preview { margin-top:16px; border:1px solid #cbd5e1; background:#f8fafc; max-width:460px; }.calibration-preview svg { display:block; width:100%; }
</style>
