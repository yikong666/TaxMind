<script setup lang="ts">
import { Download, Link } from '@element-plus/icons-vue'
import type { Citation } from '@/api/conversations'

defineProps<{ citation: Citation; index: number }>()
defineEmits<{ download: [citation: Citation] }>()

// Milvus 使用 YYYYMMDD 数字过滤，展示时恢复为易读日期。
function formatDate(value?: string | number): string {
  if (!value || value === 0) return '长期有效/未注明'
  const text = String(value)
  return /^\d{8}$/.test(text) ? `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6)}` : text
}
</script>

<template>
  <article class="citation-card">
    <header><span class="citation-index">{{ index }}</span><div>
      <strong>{{ citation.policy_title || citation.question || citation.original_name || '政策依据' }}</strong>
      <p>{{ citation.doc_no || '未标注文号' }}</p>
    </div></header>
    <div class="citation-meta">
      <span>{{ citation.region || '全国/未注明' }}</span>
      <span>{{ formatDate(citation.effective_start) }} 至 {{ formatDate(citation.effective_end) }}</span>
    </div>
    <el-collapse class="citation-collapse">
      <el-collapse-item title="查看原始文档块">
        <p class="citation-content">{{ citation.parent_content || citation.content || '暂无文档块内容' }}</p>
      </el-collapse-item>
    </el-collapse>
    <footer>
      <el-button v-if="citation.source_url" text type="primary" :icon="Link" tag="a" :href="citation.source_url" target="_blank">官方来源</el-button>
      <el-button v-if="citation.document_id" text :icon="Download" @click="$emit('download', citation)">下载原文</el-button>
    </footer>
  </article>
</template>
