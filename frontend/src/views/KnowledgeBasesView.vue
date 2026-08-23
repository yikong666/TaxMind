<script setup lang="ts">
import { ArrowLeft, Delete, DocumentAdd, EditPen, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getErrorMessage } from '@/api/http'
import {
  createKnowledgeBase, deleteChildChunk, deleteKnowledgeBase, deleteParentChunk,
  getKnowledgeBase, indexDocument, listChunks, listKnowledgeBases, parseDocument,
  savePolicyMetadata, updateChildChunk, updateKnowledgeBase, updateParentChunk,
  uploadDocuments, type KnowledgeBase, type KnowledgeBaseDetail, type KnowledgeDocument,
  type ParentChunk, type PolicyMetadata,
} from '@/api/knowledgeBases'

const router = useRouter()
const bases = ref<KnowledgeBase[]>([])
const selected = ref<KnowledgeBaseDetail | null>(null)
const loading = ref(false)
const uploading = ref(false)
const files = ref<File[]>([])
const dialog = ref<'base' | 'metadata' | 'chunks' | null>(null)
const editing = ref<KnowledgeDocument | null>(null)
const chunks = ref<ParentChunk[]>([])
const baseForm = reactive({ id: 0, name: '', description: '', kb_type: 'public_policy' as KnowledgeBase['kb_type'] })
const parseForm = reactive({ parent_chunk_size: 1200, child_chunk_size: 300, chunk_overlap: 50 })
const metadata = reactive<PolicyMetadata>({ policy_title: null, doc_no: null, region: '全国', tax_type: null, taxpayer_type: null, publish_date: null, effective_start: null, effective_end: null, policy_status: 'active', source_url: null })
const totalDocuments = computed(() => bases.value.reduce((sum, item) => sum + item.document_count, 0))
const totalChunks = computed(() => bases.value.reduce((sum, item) => sum + item.chunk_count, 0))

async function refresh(selectId?: number) {
  loading.value = true
  try {
    bases.value = await listKnowledgeBases()
    const id = selectId ?? selected.value?.id ?? bases.value[0]?.id
    selected.value = id ? await getKnowledgeBase(id) : null
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { loading.value = false }
}
async function selectBase(id: number) { selected.value = await getKnowledgeBase(id) }
function openBase(item?: KnowledgeBase) {
  Object.assign(baseForm, item ? { ...item } : { id: 0, name: '', description: '', kb_type: 'public_policy' })
  dialog.value = 'base'
}
async function saveBase() {
  if (!baseForm.name.trim()) return ElMessage.warning('请输入知识库名称')
  try {
    const item = baseForm.id ? await updateKnowledgeBase(baseForm.id, baseForm) : await createKnowledgeBase(baseForm)
    dialog.value = null; await refresh(item.id); ElMessage.success('知识库已保存')
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
}
async function removeBase(item: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(`删除“${item.name}”后，其文档和 Chunk 将一并删除。`, '确认删除', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    await deleteKnowledgeBase(item.id); await refresh(); ElMessage.success('知识库已删除')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error)) }
}
function chooseFiles(items: UploadFile[]) {
  files.value = items.flatMap((item) => item.raw ? [item.raw as File] : [])
}
async function upload() {
  if (!selected.value || !files.value.length) return ElMessage.warning('请先选择文档')
  uploading.value = true
  try { await uploadDocuments(selected.value.id, files.value); files.value = []; await refresh(selected.value.id); ElMessage.success('文档上传成功') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { uploading.value = false }
}
async function parse(item: KnowledgeDocument) {
  try { await parseDocument(item.id, parseForm); await refresh(selected.value?.id); ElMessage.success('文档解析完成') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
}
function openMetadata(item: KnowledgeDocument) {
  editing.value = item
  Object.assign(metadata, { policy_title: null, doc_no: null, region: '全国', tax_type: null, taxpayer_type: null, publish_date: null, effective_start: null, effective_end: null, policy_status: 'active', source_url: null, ...item.policy_metadata })
  // 空元数据首次打开时默认选择“现行有效”，减少政策入库的重复操作。
  if (!metadata.policy_status) metadata.policy_status = 'active'
  dialog.value = 'metadata'
}
async function saveMetadata() {
  if (!editing.value) return
  try { await savePolicyMetadata(editing.value.id, metadata); dialog.value = null; await refresh(selected.value?.id); ElMessage.success('政策元数据已保存') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
}
async function index(item: KnowledgeDocument) {
  try { await indexDocument(item.id); await refresh(selected.value?.id); ElMessage.success('向量化完成') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
}
async function openChunks(item: KnowledgeDocument) { editing.value = item; chunks.value = await listChunks(item.id); dialog.value = 'chunks' }
async function saveParent(item: ParentChunk) { await updateParentChunk(item.id, { heading: item.heading, content: item.content }); ElMessage.success('Parent Chunk 已保存') }
async function saveChild(id: number, content: string) { await updateChildChunk(id, content); ElMessage.success('Child Chunk 已保存') }
async function removeChunk(kind: 'parent' | 'child', id: number) {
  try {
    await ElMessageBox.confirm('删除后需要重新向量化该文档，是否继续？', '删除 Chunk', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    if (kind === 'parent') await deleteParentChunk(id); else await deleteChildChunk(id)
    if (editing.value) chunks.value = await listChunks(editing.value.id)
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error)) }
}
onMounted(() => refresh())
</script>

<template>
  <main class="management-page">
    <header class="management-header"><div class="management-brand"><span>税</span><div><strong>TaxMind</strong><small>知识资产中心</small></div></div><nav><el-button text :icon="ArrowLeft" @click="router.push('/chat')">返回智能问答</el-button></nav></header>
    <section class="management-content" v-loading="loading">
      <div class="page-heading"><div><p>KNOWLEDGE OPERATIONS</p><h1>知识库管理</h1><span>维护政策资料、解析内容和检索向量状态</span></div><el-button type="primary" :icon="Plus" @click="openBase()">新建知识库</el-button></div>
      <div class="metric-grid"><article><span>知识库</span><strong>{{ bases.length }}</strong></article><article><span>文档总数</span><strong>{{ totalDocuments }}</strong></article><article><span>Child Chunk</span><strong>{{ totalChunks }}</strong></article></div>
      <div class="management-grid">
        <aside class="base-list"><header><strong>我的知识库</strong><el-button text :icon="Refresh" circle @click="refresh()" /></header><button v-for="item in bases" :key="item.id" :class="{ active: selected?.id === item.id }" @click="selectBase(item.id)"><div><strong>{{ item.name }}</strong><span>{{ item.document_count }} 文档 · {{ item.chunk_count }} Chunk</span></div><el-tag size="small" effect="plain">{{ item.kb_type === 'internal' ? '企业内部' : item.kb_type === 'local_policy' ? '地方政策' : '公共政策' }}</el-tag></button><el-empty v-if="!bases.length" description="尚未创建知识库" :image-size="64" /></aside>
        <section class="base-detail" v-if="selected"><header><div><p>{{ selected.description || '暂无描述' }}</p><h2>{{ selected.name }}</h2></div><div><el-button :icon="EditPen" @click="openBase(selected)">编辑</el-button><el-button type="danger" plain :icon="Delete" @click="removeBase(selected)">删除</el-button></div></header>
          <div class="upload-zone"><el-upload drag multiple :auto-upload="false" :on-change="(_f: UploadFile, fs: UploadFile[]) => chooseFiles(fs)" :on-remove="(_f: UploadFile, fs: UploadFile[]) => chooseFiles(fs)"><el-icon><DocumentAdd /></el-icon><div>拖拽或点击选择 PDF、Office、Markdown、文本、HTML、图片</div></el-upload><div class="parse-settings"><el-input-number v-model="parseForm.parent_chunk_size" :min="300" :max="5000" /><span>Parent</span><el-input-number v-model="parseForm.child_chunk_size" :min="100" :max="2000" /><span>Child</span><el-input-number v-model="parseForm.chunk_overlap" :min="0" :max="500" /><span>Overlap</span><el-button type="primary" :loading="uploading" @click="upload">上传 {{ files.length || '' }}</el-button></div></div>
          <el-table :data="selected.documents" empty-text="暂无文档"><el-table-column prop="original_name" label="文档" min-width="190" /><el-table-column label="解析状态" width="110"><template #default="{ row }"><el-tag :type="row.parse_status === 'completed' ? 'success' : row.parse_status === 'failed' ? 'danger' : 'info'">{{ row.parse_status }}</el-tag></template></el-table-column><el-table-column label="Chunk" width="105"><template #default="{ row }">{{ row.parent_chunk_count }}/{{ row.child_chunk_count }}</template></el-table-column><el-table-column label="元数据" width="100"><template #default="{ row }"><span>{{ row.policy_metadata?.is_complete ? '完整' : selected.kb_type === 'internal' ? '不需要' : '待完善' }}</span></template></el-table-column><el-table-column label="操作" min-width="310"><template #default="{ row }"><el-button link type="primary" @click="parse(row)">解析</el-button><el-button v-if="selected.kb_type !== 'internal'" link @click="openMetadata(row)">元数据</el-button><el-button link :disabled="row.parse_status !== 'completed'" @click="openChunks(row)">预览</el-button><el-button link :disabled="row.parse_status !== 'completed'" @click="index(row)">向量化</el-button></template></el-table-column></el-table>
        </section><section v-else class="base-detail empty-detail"><el-empty description="选择或创建知识库" /></section>
      </div>
    </section>

    <el-dialog :model-value="dialog !== null" @update:model-value="(visible: boolean) => { if (!visible) dialog = null }" :show-close="true" :title="dialog === 'base' ? (baseForm.id ? '编辑知识库' : '新建知识库') : dialog === 'metadata' ? '政策元数据' : 'Chunk 内容预览'" :width="dialog === 'chunks' ? '900px' : '620px'">
      <el-form v-if="dialog === 'base'" label-position="top"><el-form-item label="名称"><el-input v-model="baseForm.name" maxlength="100" /></el-form-item><el-form-item label="类型"><el-select v-model="baseForm.kb_type" :disabled="Boolean(baseForm.id)"><el-option label="公共政策知识库" value="public_policy" /><el-option label="地方政策知识库" value="local_policy" /><el-option label="企业内部知识库" value="internal" /></el-select></el-form-item><el-form-item label="描述"><el-input v-model="baseForm.description" type="textarea" :rows="4" /></el-form-item></el-form>
      <el-form v-if="dialog === 'metadata'" class="metadata-form" label-position="top"><el-form-item label="政策标题"><el-input v-model="metadata.policy_title" /></el-form-item><el-form-item label="文号"><el-input v-model="metadata.doc_no" /></el-form-item><el-form-item label="地区"><el-input v-model="metadata.region" /></el-form-item><el-form-item label="税种"><el-input v-model="metadata.tax_type" /></el-form-item><el-form-item label="纳税人类型"><el-input v-model="metadata.taxpayer_type" /></el-form-item><el-form-item label="政策状态"><el-select v-model="metadata.policy_status"><el-option label="现行有效" value="active" /><el-option label="已失效" value="expired" /><el-option label="已被替代" value="replaced" /></el-select></el-form-item><el-form-item label="发布日期"><el-date-picker v-model="metadata.publish_date" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="生效日期"><el-date-picker v-model="metadata.effective_start" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="失效日期"><el-date-picker v-model="metadata.effective_end" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="官方来源" class="wide"><el-input v-model="metadata.source_url" placeholder="https://..." /></el-form-item></el-form>
      <div v-if="dialog === 'chunks'" class="chunk-editor"><el-collapse><el-collapse-item v-for="parent in chunks" :key="parent.id" :title="`Parent ${parent.chunk_index + 1} · ${parent.heading || '无标题'}`"><el-input v-model="parent.heading" placeholder="标题" /><el-input v-model="parent.content" type="textarea" :rows="5" /><div class="chunk-actions"><el-button size="small" @click="saveParent(parent)">保存 Parent</el-button><el-button size="small" type="danger" plain @click="removeChunk('parent', parent.id)">删除</el-button></div><article v-for="child in parent.children" :key="child.id"><header>Child {{ child.chunk_index + 1 }} <el-tag size="small">{{ child.vector_status }}</el-tag></header><el-input v-model="child.content" type="textarea" :rows="3" /><el-button size="small" @click="saveChild(child.id, child.content)">保存 Child</el-button><el-button size="small" type="danger" link @click="removeChunk('child', child.id)">删除</el-button></article></el-collapse-item></el-collapse><el-empty v-if="!chunks.length" description="尚未生成 Chunk，请先解析文档" /></div>
      <template #footer><el-button @click="dialog = null">关闭</el-button><el-button v-if="dialog === 'base'" type="primary" @click="saveBase">保存</el-button><el-button v-if="dialog === 'metadata'" type="primary" @click="saveMetadata">保存元数据</el-button></template>
    </el-dialog>
  </main>
</template>
