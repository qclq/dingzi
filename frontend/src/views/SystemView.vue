<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi } from '@/api/system'

const tab = ref('users'); const users = ref<any[]>([]); const audit = ref<any[]>([]); const runtime = ref<any[]>([]); const deliveries = ref<any[]>([]); const usage = ref<any>({})
const mes = reactive<any>({ mes_url: '', auth_token: '', auto_report: false, revision: 1, token_configured: false })
const policy = reactive<any>({ retention_days: 90, quota_gb: null, warning_percent: 80, revision: 1 })
const form = reactive<any>({ username: '', password: '', display_name: '', email: '', role: 'operator' })
async function loadUsers() { users.value = (await systemApi.users()).items }
async function loadLogs() { audit.value = (await systemApi.auditLogs()).items; runtime.value = (await systemApi.systemLogs()).items }
async function loadMes() { Object.assign(mes, await systemApi.mesConfig()); deliveries.value = await systemApi.deliveries() }
async function loadFiles() { Object.assign(policy, await systemApi.filePolicy()); usage.value = await systemApi.fileUsage() }
async function load() { if (tab.value === 'users') await loadUsers(); if (tab.value === 'logs') await loadLogs(); if (tab.value === 'mes') await loadMes(); if (tab.value === 'files') await loadFiles() }
async function create() { await systemApi.createUser(form); Object.assign(form, { username: '', password: '', display_name: '', email: '', role: 'operator' }); ElMessage.success('用户已新增'); await loadUsers() }
async function changeStatus(row: any) { await systemApi.status(row.id, row.status === 'active' ? 'disabled' : 'active'); await loadUsers() }
async function remove(row: any) { await ElMessageBox.confirm(`删除 ${row.username} 后将保留审计记录，是否继续？`, '确认删除', { type: 'warning' }); await systemApi.removeUser(row.id); await loadUsers() }
async function resetPassword(row: any) { await ElMessageBox.confirm(`向 ${row.email || '预留邮箱'} 发起密码重置，是否继续？`, '确认重置', { type: 'warning' }); await systemApi.passwordReset(row.id); ElMessage.success('密码重置请求已提交') }
async function downloadLogs(kind: 'audit' | 'system') { const blob = await systemApi.logCsv(kind); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${kind}-logs.csv`; anchor.click(); URL.revokeObjectURL(url) }
async function manualReport(row: any) { await systemApi.manualReport(row.detection_id); ElMessage.success('人工补报已提交'); await loadMes() }
async function saveMes() { Object.assign(mes, await systemApi.saveMesConfig(mes)); ElMessage.success('MES 配置已保存') }
async function testMes() { const result = await systemApi.testMes(mes); ElMessage.info(`HTTP ${result.http_status ?? '未连接'}，${result.response_time_ms} ms`) }
async function savePolicy() { Object.assign(policy, await systemApi.saveFilePolicy(policy)); ElMessage.success('文件策略已保存') }
async function cleanup() { await ElMessageBox.confirm('仅删除满足策略的原图，不删除检测元数据。是否继续？', '确认清理', { type: 'warning' }); const result = await systemApi.cleanup(); ElMessage.success(`已清理 ${result.deleted} 个文件`); await loadFiles() }
onMounted(load)
</script>

<template>
  <section><h2>系统管理</h2><el-tabs v-model="tab" @tab-change="load">
    <el-tab-pane label="用户管理" name="users"><el-card><el-form inline><el-input v-model="form.username" placeholder="账号"/><el-input v-model="form.display_name" placeholder="姓名"/><el-input v-model="form.email" placeholder="邮箱"/><el-input v-model="form.password" type="password" placeholder="初始密码"/><el-select v-model="form.role"><el-option label="操作员" value="operator"/><el-option label="管理员" value="admin"/></el-select><el-button type="primary" @click="create">新增</el-button></el-form><el-table :data="users"><el-table-column prop="username" label="账号"/><el-table-column prop="display_name" label="姓名"/><el-table-column prop="role" label="角色"/><el-table-column prop="status" label="状态"/><el-table-column prop="last_login" label="最后登录"/><el-table-column label="操作"><template #default="{ row }"><el-button size="small" @click="changeStatus(row)">{{ row.status === 'active' ? '停用' : '启用' }}</el-button><el-button size="small" @click="systemApi.unlock(row.id).then(loadUsers)">解锁</el-button><el-button size="small" :disabled="!row.email" @click="resetPassword(row)">重置密码</el-button><el-button size="small" type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table></el-card></el-tab-pane>
    <el-tab-pane label="日志中心" name="logs"><el-row :gutter="16"><el-col :span="12"><el-card header="操作日志"><el-button @click="downloadLogs('audit')">导出 CSV</el-button><el-table :data="audit"><el-table-column prop="created_at" label="时间"/><el-table-column prop="level" label="级别"/><el-table-column prop="action" label="操作"/><el-table-column prop="message" label="内容"/></el-table></el-card></el-col><el-col :span="12"><el-card header="系统日志"><el-button @click="downloadLogs('system')">导出 CSV</el-button><el-table :data="runtime"><el-table-column prop="created_at" label="时间"/><el-table-column prop="level" label="级别"/><el-table-column prop="source" label="来源"/><el-table-column prop="message" label="内容"/></el-table></el-card></el-col></el-row></el-tab-pane>
    <el-tab-pane label="MES 配置" name="mes"><el-card><el-form label-width="120"><el-form-item label="MES URL"><el-input v-model="mes.mes_url"/></el-form-item><el-form-item label="Token"><el-input v-model="mes.auth_token" type="password" :placeholder="mes.token_configured ? '已配置；留空则保持不变' : '请输入 Token'"/></el-form-item><el-form-item label="自动上报"><el-switch v-model="mes.auto_report"/></el-form-item><el-button type="primary" @click="saveMes">保存</el-button><el-button @click="testMes">测试连接</el-button></el-form><el-table :data="deliveries" style="margin-top:16px"><el-table-column prop="detection_id" label="检测记录"/><el-table-column prop="status" label="状态"/><el-table-column prop="attempts" label="尝试次数"/><el-table-column prop="last_error" label="错误"/><el-table-column label="操作"><template #default="{ row }"><el-button v-if="row.status !== 'succeeded'" size="small" @click="manualReport(row)">人工补报</el-button></template></el-table-column></el-table></el-card></el-tab-pane>
    <el-tab-pane label="文件策略" name="files"><el-card><el-form label-width="120"><el-form-item label="保留天数"><el-input-number v-model="policy.retention_days" :min="21"/></el-form-item><el-form-item label="磁盘配额 (GB)"><el-input-number v-model="policy.quota_gb" :min="1"/></el-form-item><el-form-item label="告警阈值"><el-input-number v-model="policy.warning_percent" :min="1" :max="99"/> %</el-form-item><el-button type="primary" @click="savePolicy">保存</el-button><el-button type="danger" @click="cleanup">立即清理</el-button></el-form><p>已管理原图：{{ usage.file_count }} 个，{{ usage.used_bytes }} bytes；使用率：{{ usage.percent ?? '未配置配额' }}</p></el-card></el-tab-pane>
  </el-tabs></section>
</template>
