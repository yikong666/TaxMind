<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <!-- 根组件只承载路由出口，避免混入具体页面布局。 -->
  <RouterView />
</template>
