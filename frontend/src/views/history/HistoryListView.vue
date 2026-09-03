<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { historyApi } from '@/api/history'
import type { DetectionListItem, DetectionResult, ExportFormat, ExportJob } from '@/types/history'

const router = useRouter()
const loading = ref(false)
const records = ref<DetectionListItem[]>([])
const selected = ref<DetectionListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref<20 | 50 | 100>(20)
const result = ref<DetectionResult | ''>('')
const operator = ref('')
const imageId = ref('')
const lineId = ref('')
const timeRange = ref<Date[]>([])
const exportJob = ref<ExportJob | null>(null)
let pollTimer: ReturnType<typeof globalThis.setTimeout> | null = null

function query() {
  return {
    page: page.value,
    page_size: pageSize.value,
    result: result.value || undefined,
    operator: operator.value || undefined,
    image_id: imageId.value || undefined,
    line_id: lineId.value || undefined,
    start_time: timeRange.value[0]?.toISOString(),
    end_time: timeRange.value[1]?.toISOString(),
  }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const response = await historyApi.list(query())
    records.value = response.items
    total.value = response.total
  } finally {
    loading.value = false
  }
}

function reset(): void {
  result.value = ''
  operator.value = ''
  imageId.value = ''
  lineId.value = ''
  timeRange.value = []
  page.value = 1
  void load()
}

function pageChanged(nextPage: number): void {
  page.value = nextPage
  void load()
}

function pageSizeChanged(nextSize: number): void {
  pageSize.value = nextSize as 20 | 50 | 100
  page.value = 1
  void load()
}

function pollExport(id: string): void {
  if (pollTimer) globalThis.clearTimeout(pollTimer)
  pollTimer = globalThis.setTimeout(async () => {
    const job = await historyApi.exportStatus(id)
    exportJob.value = job
    if (job.status === 'completed' && job.download_url) {
      ElMessage.success(`导出完成，共 ${job.record_count} 条记录`)
      globalThis.open(job.download_url, '_blank', 'noopener')
    } else if (job.status === 'failed') {
      ElMessage.error(job.error_message || '导出失败')
    } else {
      pollExport(id)
    }
  }, 1_000)
}

async function createExport(format: ExportFormat): Promise<void> {
  const job = await historyApi.createExport({
    format,
    detection_ids: selected.value.map((item) => item.id),
    ...query(),
  })
  exportJob.value = job
  ElMessage.info('已创建异步导出任务')
  pollExport(job.id)
}

async function downloadImage(id: number): Promise<void> {
  const file = await historyApi.fileUrl(id, 'image')
  globalThis.open(file.url, '_blank', 'noopener')
}

onMounted(() => { void load() })
</script>

<template>
  <section class="history-page">
    <el-card>
      <template #header>历史记录</template>
      <el-form inline class="filters">
        <el-form-item label="检测时间">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
          />
        </el-form-item>
        <el-form-item label="判定结果">
          <el-select v-model="result" clearable placeholder="全部" class="result-select">
            <el-option label="PASS" value="PASS" />
            <el-option label="NG" value="NG" />
          </el-select>
        </el-form-item>
        <el-form-item label="图片编号">
          <el-input v-model="imageId" clearable placeholder="精确匹配" />
        </el-form-item>
        <el-form-item label="操作员">
          <el-input v-model="operator" clearable placeholder="操作员" />
        </el-form-item>
        <el-form-item label="产线">
          <el-input v-model="lineId" clearable placeholder="line-1" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="page = 1; load()">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="actions">
        <el-button @click="createExport('xlsx')">导出 Excel</el-button>
        <el-button @click="createExport('pdf')">导出 PDF</el-button>
        <span v-if="exportJob">导出状态：{{ exportJob.status }}</span>
      </div>
      <el-table
        v-loading="loading"
        :data="records"
        @selection-change="selected = $event"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="image_id" label="图片编号" min-width="180" />
        <el-table-column prop="captured_at" label="检测时间" min-width="180" />
        <el-table-column prop="operator" label="操作员" min-width="120" />
        <el-table-column prop="defect_count" label="缺陷数量" width="100" />
        <el-table-column label="判定结果" width="110">
          <template #default="scope">
            <el-tag :type="scope.row.result === 'NG' ? 'danger' : 'success'">
              {{ scope.row.result }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="scope">
            <el-button link type="primary" @click="router.push(`/history/${scope.row.id}`)">详情</el-button>
            <el-button link @click="downloadImage(scope.row.id)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="pagination"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        :total="total"
        @current-change="pageChanged"
        @size-change="pageSizeChanged"
      />
    </el-card>
  </section>
</template>

<style scoped>
.filters, .actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.actions { margin-bottom: 16px; }
.result-select { width: 120px; }
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
