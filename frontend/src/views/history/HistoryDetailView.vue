<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { Canvas, FabricImage, Point, Rect } from 'fabric'
import { useRoute, useRouter } from 'vue-router'
import { historyApi } from '@/api/history'
import type { DetectionDetail } from '@/types/history'

const route = useRoute()
const router = useRouter()
const detail = ref<DetectionDetail | null>(null)
const imageUrl = ref('')
const mesWorkOrder = ref('')
const canvasElement = ref<HTMLCanvasElement | null>(null)
let canvas: Canvas | null = null
let panning = false

async function renderAnnotations(): Promise<void> {
  if (!canvas || !detail.value) return
  canvas.clear()
  const width = 900
  const height = 560
  canvas.setDimensions({ width, height })
  if (imageUrl.value) {
    try {
      const image = await FabricImage.fromURL(imageUrl.value, { crossOrigin: 'anonymous' })
      image.scaleToWidth(width)
      if (image.getScaledHeight() > height) image.scaleToHeight(height)
      canvas.backgroundImage = image
    } catch {
      // An unavailable object-store URL must not hide persisted defect metadata.
    }
  }
  for (const defect of detail.value.defects) {
    const [x = 0, y = 0, boxWidth = 0, boxHeight = 0] = defect.bbox
    canvas.add(new Rect({
      left: x * width,
      top: y * height,
      width: boxWidth * width,
      height: boxHeight * height,
      fill: 'transparent',
      stroke: defect.level === 'severe' ? '#f5222d' : '#faad14',
      strokeWidth: 3,
      selectable: false,
    }))
  }
  canvas.renderAll()
}

async function load(): Promise<void> {
  const id = Number(route.params.id)
  detail.value = await historyApi.detail(id)
  mesWorkOrder.value = detail.value.mes_work_order || ''
  imageUrl.value = (await historyApi.fileUrl(id, 'image')).url
  await nextTick()
  await renderAnnotations()
}

async function downloadJson(): Promise<void> {
  if (!detail.value) return
  const file = await historyApi.fileUrl(detail.value.id, 'json')
  globalThis.open(file.url, '_blank', 'noopener')
}

async function linkMesWorkOrder(): Promise<void> {
  if (!detail.value || !mesWorkOrder.value.trim()) return
  detail.value = await historyApi.linkMesWorkOrder(detail.value.id, mesWorkOrder.value.trim())
}

onMounted(async () => {
  if (canvasElement.value) {
    canvas = new Canvas(canvasElement.value, { selection: false })
    canvas.on('mouse:wheel', (event) => {
      const pointerEvent = event.e
      let zoom = canvas?.getZoom() ?? 1
      zoom *= 0.999 ** pointerEvent.deltaY
      zoom = Math.min(4, Math.max(0.5, zoom))
      canvas?.zoomToPoint(new Point(pointerEvent.offsetX, pointerEvent.offsetY), zoom)
      pointerEvent.preventDefault()
      pointerEvent.stopPropagation()
    })
    canvas.on('mouse:down', (event) => {
      const pointerEvent = event.e as { altKey: boolean; button: number }
      if (pointerEvent.altKey || pointerEvent.button === 1) panning = true
    })
    canvas.on('mouse:move', (event) => {
      if (!panning || !canvas) return
      const viewport = canvas.viewportTransform
      if (viewport) {
        const pointerEvent = event.e as { movementX: number; movementY: number }
        viewport[4] += pointerEvent.movementX
        viewport[5] += pointerEvent.movementY
        canvas.requestRenderAll()
      }
    })
    canvas.on('mouse:up', () => { panning = false })
  }
  await load()
})
onUnmounted(() => { canvas?.dispose(); canvas = null })
</script>

<template>
  <section class="detail-page">
    <div class="toolbar">
      <el-button @click="router.push('/history')">返回历史列表</el-button>
      <el-tag :type="detail?.result === 'NG' ? 'danger' : 'success'">{{ detail?.result || '—' }}</el-tag>
      <el-button v-if="detail" @click="downloadJson">下载 AI JSON</el-button>
    </div>
    <el-row v-if="detail" :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header>原图与缺陷标注（滚轮缩放，按 Alt 或中键拖动）</template>
          <div class="canvas-wrap"><canvas ref="canvasElement" /></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>检测详情</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="图片编号">{{ detail.image_id }}</el-descriptions-item>
            <el-descriptions-item label="检测时间">{{ detail.captured_at }}</el-descriptions-item>
            <el-descriptions-item label="操作员">{{ detail.operator }}</el-descriptions-item>
            <el-descriptions-item label="模型版本">{{ detail.model_version }}</el-descriptions-item>
            <el-descriptions-item label="配置版本">{{ detail.config_version }}</el-descriptions-item>
            <el-descriptions-item label="MES 状态">{{ detail.mes_status }}</el-descriptions-item>
            <el-descriptions-item label="MES 工单">
              <el-input v-model="mesWorkOrder" placeholder="输入工单编号">
                <template #append>
                  <el-button @click="linkMesWorkOrder">关联</el-button>
                </template>
              </el-input>
            </el-descriptions-item>
            <el-descriptions-item label="推理耗时">{{ detail.inference_ms }} ms</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
    <el-card v-if="detail">
      <template #header>缺陷列表</template>
      <el-table :data="detail.defects">
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="level" label="等级" />
        <el-table-column prop="confidence" label="置信度" />
        <el-table-column label="像素尺寸">
          <template #default="scope">{{ scope.row.bbox[2] }} × {{ scope.row.bbox[3] }}</template>
        </el-table-column>
        <el-table-column label="物理尺寸 mm">
          <template #default="scope">{{ scope.row.width_mm ?? '—' }} × {{ scope.row.height_mm ?? '—' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card v-if="detail">
      <template #header>检测时配置快照</template>
      <pre>{{ JSON.stringify(detail.config_snapshot, null, 2) }}</pre>
    </el-card>
    <el-card v-if="detail">
      <template #header>AI 原始 JSON</template>
      <pre>{{ JSON.stringify(detail.raw_output, null, 2) }}</pre>
    </el-card>
  </section>
</template>

<style scoped>
.detail-page { display: flex; flex-direction: column; gap: 16px; }
.toolbar { display: flex; gap: 12px; align-items: center; }
.canvas-wrap { overflow: auto; background: #111827; }
pre { max-height: 360px; overflow: auto; padding: 16px; background: #111827; color: #e5e7eb; }
</style>
