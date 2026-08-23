<script setup lang="ts">
import { ArrowLeft, Check, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createFaq } from '@/api/faqs'
import { getErrorMessage } from '@/api/http'
import { listTickets, updateTicket, type ReviewTicket } from '@/api/reviews'

// 工单详情和状态筛选保持单页联动，所有状态变更后重新读取服务端事实。
const router = useRouter()
const items = ref<ReviewTicket[]>([])
const active = ref<ReviewTicket | null>(null)
const loading = ref(false)
const status = ref('')
const risk = ref('')
const pendingCount = computed(() => items.value.filter((item) => item.status === 'pending').length)

async function refresh(selectId?: number) {
  loading.value = true
  try {
    items.value = await listTickets({ status: status.value || undefined, risk_level: risk.value || undefined })
    active.value = items.value.find((item) => item.id === (selectId ?? active.value?.id)) ?? items.value[0] ?? null
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { loading.value = false }
}
async function start(item: ReviewTicket) {
  try { await updateTicket(item.id, 'processing'); await refresh(item.id); ElMessage.success('工单已进入处理中') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
}
async function resolve(item: ReviewTicket) {
  try {
    const result = await ElMessageBox.prompt('请输入人工审核结论', '解决工单', { inputType: 'textarea', inputPattern: /\S+/, inputErrorMessage: '处理结果不能为空', confirmButtonText: '确认解决', cancelButtonText: '取消' })
    await updateTicket(item.id, 'resolved', result.value.trim()); await refresh(item.id); ElMessage.success('工单已解决')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error)) }
}
async function convertToFaq(item: ReviewTicket) {
  if (!item.resolution) return
  try {
    const citation = item.citations[0] ?? {}
    await createFaq({ question: item.user_question, answer: item.resolution, category: `人工审核#工单${item.id}`, region: String(citation.region ?? '全国'), doc_no: citation.doc_no ? String(citation.doc_no) : null, effective_start: null, effective_end: null, is_enabled: true })
    ElMessage.success('已生成 FAQ，并保留来源工单编号')
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
}
function statusText(value: ReviewTicket['status']) { return value === 'pending' ? '待处理' : value === 'processing' ? '处理中' : '已解决' }
onMounted(refresh)
</script>

<template>
  <main class="management-page ticket-page"><header class="management-header"><div class="management-brand"><span>税</span><div><strong>TaxMind</strong><small>人工审核中心</small></div></div><nav><el-button text @click="router.push('/faqs')">FAQ 管理</el-button><el-button text :icon="ArrowLeft" @click="router.push('/chat')">返回智能问答</el-button></nav></header>
    <section class="management-content" v-loading="loading"><div class="page-heading"><div><p>HUMAN REVIEW</p><h1>人工审核工单</h1><span>处理低置信度、高风险及用户主动转人工的问题</span></div><el-button :icon="RefreshRight" @click="refresh()">刷新</el-button></div>
      <div class="metric-grid"><article><span>当前结果</span><strong>{{ items.length }}</strong></article><article><span>待处理</span><strong>{{ pendingCount }}</strong></article><article><span>筛选风险</span><strong>{{ risk || '全部' }}</strong></article></div>
      <div class="ticket-filters"><el-select v-model="status" placeholder="全部状态" @change="refresh()"><el-option label="全部状态" value="" /><el-option label="待处理" value="pending" /><el-option label="处理中" value="processing" /><el-option label="已解决" value="resolved" /></el-select><el-select v-model="risk" placeholder="全部风险" @change="refresh()"><el-option label="全部风险" value="" /><el-option label="低风险" value="LOW" /><el-option label="中风险" value="MEDIUM" /><el-option label="高风险" value="HIGH" /><el-option label="禁止回答" value="PROHIBITED" /></el-select></div>
      <div class="ticket-grid"><aside class="ticket-list"><button v-for="item in items" :key="item.id" :class="{active:active?.id===item.id}" @click="active=item"><header><el-tag size="small">{{ statusText(item.status) }}</el-tag><el-tag size="small" :type="item.risk_level==='HIGH'||item.risk_level==='PROHIBITED'?'danger':'info'">{{ item.risk_level || '未分级' }}</el-tag></header><strong>{{ item.user_question || '未记录用户问题' }}</strong><span>{{ new Date(item.created_at).toLocaleString() }}</span></button><el-empty v-if="!items.length" description="暂无工单" /></aside>
        <section v-if="active" class="ticket-detail"><header><div><p>工单 #{{ active.id }} · {{ active.trigger_reason }}</p><h2>{{ active.user_question }}</h2></div><el-tag>{{ statusText(active.status) }}</el-tag></header><article><label>AI 回答</label><p>{{ active.ai_answer }}</p></article><article v-if="active.user_feedback"><label>用户反馈</label><p>{{ active.user_feedback }}</p></article><article><label>检索引用（{{ active.citations.length }}）</label><pre>{{ JSON.stringify(active.citations, null, 2) }}</pre></article><article v-if="active.resolution" class="resolution"><label>人工处理结果</label><p>{{ active.resolution }}</p></article><footer><el-button v-if="active.status==='pending'" type="primary" @click="start(active)">开始处理</el-button><el-button v-if="active.status==='processing'" type="primary" :icon="Check" @click="resolve(active)">填写结论并解决</el-button><el-button v-if="active.status==='resolved'" @click="convertToFaq(active)">生成 FAQ</el-button></footer></section><section v-else class="ticket-detail empty-detail"><el-empty description="选择一条工单查看详情" /></section></div>
    </section>
  </main>
</template>
