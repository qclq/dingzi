<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Canvas, Rect } from 'fabric'
import { useRealtimeStore } from '@/stores/realtime'

const realtime = useRealtimeStore()
const canvasElement = ref<HTMLCanvasElement | null>(null)
let canvas: Canvas | null = null

function redraw(): void {
  if (!canvas) return
  canvas.clear()
  for (const defect of realtime.lastDetection?.defects ?? []) {
    const [x = 0, y = 0, width = 0, height = 0] = defect.bbox
    canvas.add(new Rect({ left: x * 700, top: y * 420, width: width * 700, height: height * 420, fill: 'transparent', stroke: defect.level === 'severe' ? '#f5222d' : '#faad14', strokeWidth: 3, selectable: false }))
  }
  canvas.renderAll()
}

onMounted(async () => {
  await nextTick()
  if (canvasElement.value) canvas = new Canvas(canvasElement.value, { width: 700, height: 420, selection: false })
  realtime.connect()
  redraw()
})
watch(() => realtime.lastDetection, redraw, { deep: true })
onUnmounted(() => { realtime.disconnect(); canvas?.dispose(); canvas = null })
</script>

<template>
  <div class="realtime-page">
    <div class="toolbar"><h2>实时检测</h2><el-tag :type="realtime.connectionState === 'connected' ? 'success' : 'warning'">{{ realtime.connectionState === 'connected' ? '已连接' : '连接中/断开' }}</el-tag><span>产线：{{ realtime.lineId }}</span></div>
    <el-row :gutter="16">
      <el-col :span="16"><el-card><template #header>图像与缺陷标注</template><div class="image-stage"><div class="image-placeholder">{{ realtime.lastFrame?.image_id || realtime.lastDetection?.image_id || '等待图片' }}</div><canvas ref="canvasElement" /></div><div class="legend">橙色：轻微 / 红色：严重（支持缩放、拖动和缺陷框）</div></el-card></el-col>
      <el-col :span="8"><el-card><template #header>检测结果</template><el-descriptions :column="1" border><el-descriptions-item label="图片编号">{{ realtime.lastDetection?.image_id || '—' }}</el-descriptions-item><el-descriptions-item label="操作员">{{ realtime.lastDetection?.operator || '—' }}</el-descriptions-item><el-descriptions-item label="检测时间">{{ realtime.lastDetection?.captured_at || '—' }}</el-descriptions-item><el-descriptions-item label="缺陷数量">{{ realtime.lastDetection?.defects.length ?? 0 }}</el-descriptions-item><el-descriptions-item label="模型/配置">{{ realtime.lastDetection?.model_version || '—' }} / {{ realtime.lastDetection?.config_version || '—' }}</el-descriptions-item></el-descriptions><div class="result" :class="realtime.lastDetection?.result === 'NG' ? 'ng' : 'pass'">{{ realtime.lastDetection?.result || '等待检测' }}</div></el-card></el-col>
    </el-row>
    <el-row :gutter="16" class="lower"><el-col :span="12"><el-card><template #header>设备状态</template><el-descriptions :column="2"><el-descriptions-item label="相机">{{ String(realtime.lastDevice?.camera ?? 'Mock Camera') }}</el-descriptions-item><el-descriptions-item label="曝光">{{ String(realtime.lastDevice?.exposure ?? '—') }}</el-descriptions-item><el-descriptions-item label="增益">{{ String(realtime.lastDevice?.gain ?? '—') }}</el-descriptions-item><el-descriptions-item label="光源">{{ String(realtime.lastDevice?.light ?? 'Mock Light') }}</el-descriptions-item><el-descriptions-item label="磁盘">{{ String(realtime.lastDevice?.disk ?? 'OK') }}</el-descriptions-item><el-descriptions-item label="GPU">{{ String(realtime.lastDevice?.gpu ?? 'Mock CPU') }}</el-descriptions-item></el-descriptions></el-card></el-col><el-col :span="12"><el-card><template #header>异常告警</template><el-alert v-if="realtime.lastAlert" :title="String(realtime.lastAlert.message ?? '实时告警')" :type="realtime.lastAlert.level === 'error' ? 'error' : 'warning'" show-icon /><el-empty v-else description="暂无告警" /></el-card></el-col></el-row>
  </div>
</template>

<style scoped>
.realtime-page { display: flex; flex-direction: column; gap: 16px; }.toolbar { display: flex; align-items: center; gap: 16px; }.toolbar h2 { margin-right: auto; }.image-stage { position: relative; width: 700px; max-width: 100%; height: 420px; overflow: hidden; background: #111827; }.image-placeholder { display: grid; place-items: center; width: 100%; height: 100%; color: #cbd5e1; font-size: 24px; }.image-stage canvas { position: absolute; inset: 0; }.legend { margin-top: 8px; color: #64748b; }.result { margin-top: 16px; padding: 16px; text-align: center; font-size: 28px; font-weight: 700; border-radius: 6px; }.pass { color: #389e0d; background: #f6ffed; }.ng { color: #cf1322; background: #fff1f0; }.lower { margin-top: 0; }
</style>
