<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '', rememberMe: false })

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password, form.rememberMe)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (error) {
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    ElMessage.error(typeof detail === 'object' && detail !== null && 'message' in detail ? String(detail.message) : (String(detail ?? '登录失败，请检查账号和密码')))
  } finally { loading.value = false }
}
</script>

<template>
  <main class="login-page">
    <el-card class="login-card">
      <h1>定子冲片质检平台</h1>
      <p class="subtitle">账号登录</p>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="账号"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-checkbox v-model="form.rememberMe">记住登录状态（7 天）</el-checkbox>
        <el-button class="submit" type="primary" native-type="submit" :loading="loading">登录</el-button>
      </el-form>
    </el-card>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: #f3f6fa; }
.login-card { width: min(420px, 92vw); }
h1 { margin: 0; font-size: 24px; }
.subtitle { color: #909399; }
.submit { width: 100%; margin-top: 24px; }
</style>




