<script setup lang="ts">
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <el-card>
    <h2>{{ title }}</h2>
    <p>此页面将在对应业务阶段实现。</p>
  </el-card>
</template>
