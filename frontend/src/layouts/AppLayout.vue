<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
onMounted(() => { void auth.loadMenus() })
async function logout() { await auth.logout(); await router.replace('/login') }
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px"><div class="brand">定子冲片质检平台</div><el-menu router :default-active="$route.path"><el-menu-item v-for="item in auth.menus" :key="item.name" :index="item.path">{{ item.label }}</el-menu-item></el-menu></el-aside>
    <el-container><el-header class="header"><span>{{ auth.user?.display_name || auth.user?.username }}</span><el-tag>{{ auth.user?.role }}</el-tag><el-button text @click="logout">退出</el-button></el-header><el-main><RouterView /></el-main></el-container>
  </el-container>
</template>

<style scoped>
.layout { min-height: 100vh; }.brand { height: 60px; display: grid; place-items: center; font-weight: 700; }.header { display: flex; align-items: center; justify-content: flex-end; gap: 12px; border-bottom: 1px solid #ebeef5; }
</style>

