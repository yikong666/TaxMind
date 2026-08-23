<script setup lang="ts">
import { ArrowLeft, Delete, EditPen, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createFaq, deleteFaq, listFaqs, routeFaq, updateFaq, type Faq, type FaqPayload, type FaqRouteResult } from '@/api/faqs'
import { getErrorMessage } from '@/api/http'

// 页面同时维护 FAQ 数据和路由试测状态，写操作成功后统一重新读取后端列表。
const router = useRouter()
const items = ref<Faq[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filters = reactive({ keyword: '', category: '', region: '', status: '' })
const tester = reactive({ query: '', region: '全国', query_date: new Date().toISOString().slice(0, 10) })
const testResult = ref<FaqRouteResult | null>(null)
const testing = ref(false)
const form = reactive<FaqPayload>({ question: '', answer: '', category: '未分类', region: '全国', doc_no: null, effective_start: null, effective_end: null, is_enabled: true })
const categories = computed(() => [...new Set(items.value.map((item) => item.category))])
const enabledCount = computed(() => items.value.filter((item) => item.is_enabled).length)
const expiredCount = computed(() => items.value.filter((item) => item.effective_end && item.effective_end < tester.query_date).length)

async function refresh() {
  loading.value = true
  try {
    items.value = await listFaqs({
      keyword: filters.keyword || undefined,
      category: filters.category || undefined,
      region: filters.region || undefined,
      is_enabled: filters.status === '' ? undefined : filters.status === 'enabled',
    })
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { loading.value = false }
}
function openEditor(item?: Faq) {
  editingId.value = item?.id ?? null
  Object.assign(form, item ? {
    question: item.question, answer: item.answer, category: item.category, region: item.region,
    doc_no: item.doc_no, effective_start: item.effective_start,
    effective_end: item.effective_end, is_enabled: item.is_enabled,
  } : { question: '', answer: '', category: '未分类', region: '全国', doc_no: null, effective_start: null, effective_end: null, is_enabled: true })
  dialogVisible.value = true
}
async function save() {
  if (!form.question.trim() || !form.answer.trim()) return ElMessage.warning('问题和标准答案不能为空')
  try {
    if (editingId.value) await updateFaq(editingId.value, form)
    else await createFaq(form)
    dialogVisible.value = false; await refresh(); ElMessage.success('FAQ 已保存，路由缓存已刷新')
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
}
async function toggle(item: Faq) {
  try { await updateFaq(item.id, { is_enabled: item.is_enabled }); ElMessage.success(item.is_enabled ? 'FAQ 已启用' : 'FAQ 已停用') }
  catch (error) { item.is_enabled = !item.is_enabled; ElMessage.error(getErrorMessage(error)) }
}
async function remove(item: Faq) {
  try {
    await ElMessageBox.confirm(`确认删除“${item.question}”吗？`, '删除 FAQ', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    await deleteFaq(item.id); await refresh(); ElMessage.success('FAQ 已删除')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error)) }
}
async function testRoute() {
  if (!tester.query.trim()) return ElMessage.warning('请输入待测试问题')
  testing.value = true
  try { testResult.value = await routeFaq(tester) }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { testing.value = false }
}
onMounted(refresh)
</script>

<template>
  <main class="management-page faq-page">
    <header class="management-header"><div class="management-brand"><span>税</span><div><strong>TaxMind</strong><small>高频问答运营</small></div></div><nav><el-button text @click="router.push('/tickets')">人工工单</el-button><el-button text @click="router.push('/knowledge-bases')">知识库管理</el-button><el-button text :icon="ArrowLeft" @click="router.push('/chat')">返回智能问答</el-button></nav></header>
    <section class="management-content" v-loading="loading">
      <div class="page-heading"><div><p>FAQ OPERATIONS</p><h1>高频问答管理</h1><span>维护标准答案，命中后优先于 RAG 检索直接返回</span></div><el-button type="primary" :icon="Plus" @click="openEditor()">新增 FAQ</el-button></div>
      <div class="metric-grid"><article><span>当前结果</span><strong>{{ items.length }}</strong></article><article><span>已启用</span><strong>{{ enabledCount }}</strong></article><article><span>已过适用期</span><strong>{{ expiredCount }}</strong></article></div>
      <section class="faq-workbench">
        <div class="faq-main">
          <div class="filter-bar"><el-input v-model="filters.keyword" clearable placeholder="搜索问题、答案或文号" :prefix-icon="Search" @keyup.enter="refresh" /><el-select v-model="filters.category" clearable placeholder="全部分类"><el-option v-for="item in categories" :key="item" :label="item" :value="item" /></el-select><el-select v-model="filters.region" clearable placeholder="全部地区"><el-option label="全国" value="全国" /><el-option label="重庆" value="重庆" /></el-select><el-select v-model="filters.status" placeholder="全部状态"><el-option label="全部状态" value="" /><el-option label="已启用" value="enabled" /><el-option label="已停用" value="disabled" /></el-select><el-button type="primary" @click="refresh">筛选</el-button></div>
          <div class="faq-list"><article v-for="item in items" :key="item.id" class="faq-item"><header><div><el-tag size="small" effect="plain">{{ item.category }}</el-tag><el-tag size="small" effect="plain">{{ item.region }}</el-tag><span v-if="item.doc_no">{{ item.doc_no }}</span></div><el-switch v-model="item.is_enabled" inline-prompt active-text="启" inactive-text="停" @change="toggle(item)" /></header><h3>{{ item.question }}</h3><p>{{ item.answer }}</p><footer><span>{{ item.effective_start || '不限' }} 至 {{ item.effective_end || '长期' }}</span><div><el-button link :icon="EditPen" @click="openEditor(item)">编辑</el-button><el-button link type="danger" :icon="Delete" @click="remove(item)">删除</el-button></div></footer></article><el-empty v-if="!items.length" description="没有符合条件的 FAQ" /></div>
        </div>
        <aside class="route-tester"><p>ROUTE INSPECTOR</p><h2>FAQ 路由试测</h2><span>查看问题是否由 Redis / BM25 命中，或继续进入 RAG。</span><label>待测试问题</label><el-input v-model="tester.query" type="textarea" :rows="4" placeholder="例如：小规模纳税人如何申报增值税？" /><label>地区与查询日期</label><div class="tester-row"><el-select v-model="tester.region"><el-option label="全国" value="全国" /><el-option label="重庆" value="重庆" /></el-select><el-date-picker v-model="tester.query_date" value-format="YYYY-MM-DD" /></div><el-button type="primary" :loading="testing" @click="testRoute">执行路由测试</el-button><section v-if="testResult" class="route-result" :class="{ hit: testResult.matched }"><header><strong>{{ testResult.matched ? 'FAQ 已命中' : '继续进入 RAG' }}</strong><el-tag>{{ testResult.source }}</el-tag></header><div><span>匹配得分</span><b>{{ testResult.score.toFixed(4) }}</b></div><template v-if="testResult.faq"><h3>{{ testResult.faq.question }}</h3><p>{{ testResult.faq.answer }}</p><small>{{ testResult.faq.doc_no || '暂无文号' }} · {{ testResult.faq.region }}</small></template></section></aside>
      </section>
    </section>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 FAQ' : '新增 FAQ'" width="720px"><el-form class="faq-form" label-position="top"><el-form-item label="标准问题" class="wide"><el-input v-model="form.question" maxlength="500" show-word-limit /></el-form-item><el-form-item label="标准答案" class="wide"><el-input v-model="form.answer" type="textarea" :rows="7" maxlength="10000" show-word-limit /></el-form-item><el-form-item label="分类"><el-input v-model="form.category" /></el-form-item><el-form-item label="地区"><el-input v-model="form.region" /></el-form-item><el-form-item label="政策文号"><el-input v-model="form.doc_no" /></el-form-item><el-form-item label="启用状态"><el-switch v-model="form.is_enabled" active-text="启用" inactive-text="停用" /></el-form-item><el-form-item label="生效日期"><el-date-picker v-model="form.effective_start" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="失效日期"><el-date-picker v-model="form.effective_end" value-format="YYYY-MM-DD" /></el-form-item></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="save">保存 FAQ</el-button></template></el-dialog>
  </main>
</template>
