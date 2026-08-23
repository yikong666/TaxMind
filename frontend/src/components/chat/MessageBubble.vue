<script setup lang="ts">
import { ChatDotRound, Service, Star, Warning } from '@element-plus/icons-vue'
import { computed } from 'vue'
import type { ChatMessage, Citation } from '@/api/conversations'
import CitationCard from './CitationCard.vue'

const props = defineProps<{ message: ChatMessage; busy?: boolean; feedback?: string }>()
defineEmits<{
  feedback: [type: 'like' | 'dislike']
  handoff: []
  download: [citation: Citation]
}>()

// 路由来源转换为用户可理解的中文标签，内部枚举不直接暴露在界面上。
const sourceLabel = computed(() => ({
  faq: 'FAQ 直答', rag: '知识库检索', guardrail: '风险门禁',
  clarification: '信息追问', no_context: '暂无可靠依据',
}[props.message.route_source ?? ''] ?? 'TaxMind'))
</script>

<template>
  <article class="message-row" :class="message.role">
    <div class="message-avatar"><span v-if="message.role === 'user'">我</span><span v-else>税</span></div>
    <div class="message-body">
      <header v-if="message.role === 'assistant'" class="message-header">
        <strong>TaxMind</strong><el-tag size="small" effect="plain">{{ sourceLabel }}</el-tag>
        <el-tag v-if="message.risk_level && message.risk_level !== 'LOW'" size="small" type="warning">{{ message.risk_level }}</el-tag>
      </header>
      <div class="message-content" :class="{ streaming: message.status === 'generating' }">
        {{ message.content || '正在组织回答' }}
      </div>
      <div v-if="message.retrieval_strategy" class="strategy-line">
        <ChatDotRound />检索策略：{{ message.retrieval_strategy }}
      </div>
      <section v-if="message.citations.length" class="citation-grid">
        <CitationCard v-for="(citation, index) in message.citations" :key="`${citation.document_id ?? citation.id}-${index}`" :citation="citation" :index="index + 1" @download="$emit('download', $event)" />
      </section>
      <footer v-if="message.role === 'assistant' && message.status === 'completed'" class="message-actions">
        <el-button text size="small" :disabled="!!feedback || busy" :icon="Star" @click="$emit('feedback', 'like')">有帮助</el-button>
        <el-button text size="small" :disabled="!!feedback || busy" :icon="Warning" @click="$emit('feedback', 'dislike')">需改进</el-button>
        <el-button text size="small" :disabled="busy" :icon="Service" @click="$emit('handoff')">转人工</el-button>
        <span v-if="feedback" class="feedback-state">{{ feedback }}</span>
      </footer>
    </div>
  </article>
</template>
