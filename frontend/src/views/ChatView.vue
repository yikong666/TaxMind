<script setup lang="ts">
import {
  ArrowDown, ChatLineRound, CirclePlus, Delete, EditPen, Expand,
  Fold, MoreFilled, Setting, SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  createConversation, deleteConversation, downloadDocument, getConversation,
  listConversations, renameConversation, streamChat,
  type ChatMessage, type Citation, type Conversation, type ConversationDetail,
} from '@/api/conversations'
import { getErrorMessage } from '@/api/http'
import { listKnowledgeBases, type KnowledgeBase } from '@/api/knowledgeBases'
import { handoffMessage, submitFeedback } from '@/api/reviews'
import MessageBubble from '@/components/chat/MessageBubble.vue'

const router = useRouter()
const conversations = ref<Conversation[]>([])
const active = ref<ConversationDetail | null>(null)
const knowledgeBases = ref<KnowledgeBase[]>([])
const query = ref('')
const sending = ref(false)
const loading = ref(true)
const sidebarCollapsed = ref(false)
const settingsVisible = ref(true)
const stage = ref('')
const messageList = ref<HTMLElement>()
const feedbackStates = reactive<Record<number, string>>({})
const username = computed(() => {
  try { return JSON.parse(sessionStorage.getItem('taxmind_user') ?? '{}').username ?? '当前用户' }
  catch { return '当前用户' }
})
const settings = reactive({
  knowledge_base_ids: [] as number[], region: '全国', model: 'qwen3-max',
  temperature: 0.2, top_p: 0.8, max_tokens: 2000, history_rounds: 5,
})

const stageLabels: Record<string, string> = {
  query_rewrite: '正在改写检索问题', generating: '正在依据政策生成回答',
}

function today(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

async function scrollToBottom() {
  await nextTick()
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' })
}

async function refreshConversations(selectId?: number) {
  conversations.value = await listConversations()
  const id = selectId ?? active.value?.id ?? conversations.value[0]?.id
  if (id) await selectConversation(id)
}

async function selectConversation(id: number) {
  if (sending.value) return ElMessage.warning('请等待当前回答完成')
  active.value = await getConversation(id)
  await scrollToBottom()
}

async function newConversation() {
  if (sending.value) return ElMessage.warning('请等待当前回答完成')
  const item = await createConversation()
  conversations.value.unshift(item)
  active.value = { ...item, messages: [] }
}

async function renameItem(item: Conversation) {
  try {
    const result = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      inputValue: item.title, inputPattern: /\S+/, inputErrorMessage: '会话名称不能为空',
      confirmButtonText: '确认', cancelButtonText: '取消',
    })
    const updated = await renameConversation(item.id, result.value.trim())
    Object.assign(item, updated)
    if (active.value?.id === item.id) active.value.title = updated.title
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error))
  }
}

async function removeItem(item: Conversation) {
  try {
    await ElMessageBox.confirm(`确定删除“${item.title}”及其全部聊天记录吗？`, '删除会话', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await deleteConversation(item.id)
    if (active.value?.id === item.id) active.value = null
    await refreshConversations()
    if (!active.value) await newConversation()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error))
  }
}

async function sendMessage() {
  const text = query.value.trim()
  if (!text || sending.value) return
  if (!active.value) await newConversation()
  const conversation = active.value!
  const userMessage: ChatMessage = {
    id: -Date.now(), role: 'user', content: text, status: 'completed', risk_level: null,
    route_source: null, model_name: null, citations: [], error_message: null,
    retrieval_strategy: null, retrieval_queries: [], created_at: new Date().toISOString(),
  }
  const assistant: ChatMessage = {
    ...userMessage, id: userMessage.id - 1, role: 'assistant', content: '', status: 'generating',
  }
  conversation.messages.push(userMessage, assistant)
  query.value = ''
  sending.value = true
  stage.value = '正在理解问题'
  await scrollToBottom()
  try {
    await streamChat(conversation.id, {
      query: text, knowledge_base_ids: settings.knowledge_base_ids, region: settings.region,
      query_date: today(), model: settings.model || null, temperature: settings.temperature,
      top_p: settings.top_p, max_tokens: settings.max_tokens,
      history_rounds: settings.history_rounds,
    }, (event) => {
      if (event.event === 'session') assistant.id = Number(event.data.message_id)
      if (event.event === 'status') {
        const current = String(event.data.stage ?? '')
        stage.value = stageLabels[current] ?? '正在检索政策依据'
        if (event.data.strategy) assistant.retrieval_strategy = String(event.data.strategy)
      }
      if (event.event === 'token') assistant.content += String(event.data.text ?? '')
      if (event.event === 'citation') assistant.citations.push(event.data as unknown as Citation)
      if (event.event === 'done') {
        assistant.status = 'completed'
        assistant.route_source = String(event.data.route_source ?? '')
      }
      if (event.event === 'error') {
        assistant.status = 'failed'
        assistant.content = String(event.data.message ?? '回答生成失败，请稍后重试')
      }
      void scrollToBottom()
    })
    // 流结束后以 MySQL 记录校准风险、改写 Query 和引用等完整元数据。
    active.value = await getConversation(conversation.id)
    conversations.value = await listConversations()
  } catch (error) {
    assistant.status = 'failed'
    assistant.content = error instanceof Error ? error.message : getErrorMessage(error)
    ElMessage.error(assistant.content)
  } finally {
    sending.value = false
    stage.value = ''
    await scrollToBottom()
  }
}

async function feedback(message: ChatMessage, type: 'like' | 'dislike') {
  try {
    let reason: string | undefined
    if (type === 'dislike') {
      const result = await ElMessageBox.prompt('请简单说明需要改进的地方', '提交反馈', {
        inputType: 'textarea', inputPlaceholder: '例如：政策依据不够完整',
        inputPattern: /\S+/, inputErrorMessage: '请填写反馈原因',
        confirmButtonText: '提交', cancelButtonText: '取消',
      })
      reason = result.value.trim()
    }
    await submitFeedback(message.id, type, reason)
    feedbackStates[message.id] = type === 'like' ? '已点赞' : '反馈已提交'
    ElMessage.success('感谢你的反馈')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error))
  }
}

async function handoff(message: ChatMessage) {
  try {
    const result = await ElMessageBox.prompt('可补充希望人工重点核实的内容', '转人工审核', {
      inputType: 'textarea', inputPlaceholder: '选填',
      confirmButtonText: '确认转人工', cancelButtonText: '取消',
    })
    await handoffMessage(message.id, result.value.trim() || undefined)
    feedbackStates[message.id] = '已转人工'
    ElMessage.success('已进入人工审核队列')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error))
  }
}

async function download(citation: Citation) {
  if (!citation.document_id) return
  try { await downloadDocument(citation.document_id, citation.original_name ?? '') }
  catch (error) { ElMessage.error(getErrorMessage(error)) }
}

function logout() {
  sessionStorage.removeItem('taxmind_access_token')
  sessionStorage.removeItem('taxmind_user')
  void router.replace('/login')
}

onMounted(async () => {
  try {
    const [sessions, bases] = await Promise.all([listConversations(), listKnowledgeBases()])
    conversations.value = sessions
    knowledgeBases.value = bases
    if (sessions.length) await selectConversation(sessions[0].id)
    else await newConversation()
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { loading.value = false }
})
</script>

<template>
  <main class="chat-page" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'settings-hidden': !settingsVisible }">
    <aside class="chat-sidebar">
      <div class="sidebar-brand"><div class="brand-mark small">税</div><div v-if="!sidebarCollapsed"><strong>TaxMind</strong><span>税智通</span></div></div>
      <el-button class="new-chat" type="primary" :icon="CirclePlus" @click="newConversation"><span v-if="!sidebarCollapsed">新建会话</span></el-button>
      <div v-if="!sidebarCollapsed" class="session-label">历史会话</div>
      <nav v-if="!sidebarCollapsed" class="session-list">
        <button v-for="item in conversations" :key="item.id" class="session-item" :class="{ active: active?.id === item.id }" @click="selectConversation(item.id)">
          <ChatLineRound /><span>{{ item.title }}</span>
          <el-dropdown trigger="click" @command="(command: string) => command === 'rename' ? renameItem(item) : removeItem(item)">
            <el-icon class="session-more" @click.stop><MoreFilled /></el-icon>
            <template #dropdown><el-dropdown-menu><el-dropdown-item command="rename" :icon="EditPen">重命名</el-dropdown-item><el-dropdown-item command="delete" :icon="Delete" divided>删除</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
        </button>
      </nav>
      <div class="sidebar-footer">
        <button class="user-chip"><span class="user-avatar">{{ username.slice(0, 1) }}</span><span v-if="!sidebarCollapsed">{{ username }}</span></button>
        <el-button text :icon="SwitchButton" aria-label="退出登录" @click="logout" />
      </div>
      <button class="collapse-button" @click="sidebarCollapsed = !sidebarCollapsed"><el-icon><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon></button>
    </aside>

    <section class="chat-workspace">
      <header class="chat-topbar">
        <div><p>智能财税问答</p><h1>{{ active?.title || '新会话' }}</h1></div>
        <div class="topbar-actions"><el-button @click="router.push('/knowledge-bases')">知识库</el-button><el-button @click="router.push('/faqs')">FAQ</el-button><span class="trust-indicator"><i />政策时效与地区过滤已启用</span><el-button :icon="Setting" circle @click="settingsVisible = !settingsVisible" /></div>
      </header>
      <div ref="messageList" class="message-list" v-loading="loading">
        <section v-if="active && !active.messages.length" class="empty-chat">
          <div class="empty-orbit"><span>税</span></div><p class="empty-kicker">TAXMIND KNOWLEDGE ASSISTANT</p>
          <h2>今天想查询什么财税问题？</h2>
          <p>我会结合你选择的知识库，校验地区、政策有效期并提供可追溯引用。</p>
          <div class="suggestion-grid"><button @click="query = '小规模纳税人增值税有哪些优惠政策？'">小规模纳税人有哪些增值税优惠？</button><button @click="query = '重庆企业如何办理增值税申报？'">重庆企业如何办理增值税申报？</button><button @click="query = '个人所得税专项附加扣除有哪些项目？'">个税专项附加扣除有哪些项目？</button></div>
        </section>
        <template v-else><MessageBubble v-for="message in active?.messages" :key="message.id" :message="message" :busy="sending" :feedback="feedbackStates[message.id]" @feedback="feedback(message, $event)" @handoff="handoff(message)" @download="download" /></template>
      </div>
      <footer class="composer-wrap">
        <div v-if="stage" class="stream-stage"><span /><span /><span />{{ stage }}</div>
        <div class="composer">
          <el-input v-model="query" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" resize="none" maxlength="4000" placeholder="输入财税问题，Enter 发送，Shift + Enter 换行" @keydown.enter.exact.prevent="sendMessage" />
          <el-button class="send-button" type="primary" :loading="sending" :disabled="!query.trim()" @click="sendMessage">发送<el-icon><ArrowDown /></el-icon></el-button>
        </div>
        <p class="answer-notice">回答仅供政策信息参考，重要涉税事项建议向主管税务机关或专业人员确认。</p>
      </footer>
    </section>

    <aside class="settings-panel">
      <header><div><p>检索配置</p><h2>回答设置</h2></div><el-button text @click="settingsVisible = false">关闭</el-button></header>
      <section><label>知识库范围</label><el-select v-model="settings.knowledge_base_ids" multiple collapse-tags collapse-tags-tooltip placeholder="未选择时仅匹配 FAQ" class="full-width"><el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id"><span>{{ item.name }}</span><small>{{ item.document_count }} 个文档</small></el-option></el-select><p class="field-help">可多选，后端会再次执行用户权限校验。</p></section>
      <section><label>适用地区</label><el-segmented v-model="settings.region" :options="['全国', '重庆']" /></section>
      <el-divider />
      <section><label>模型</label><el-select v-model="settings.model" class="full-width"><el-option label="通义千问 qwen3-max" value="qwen3-max" /></el-select></section>
      <section class="slider-field"><label><span>Temperature</span><b>{{ settings.temperature.toFixed(1) }}</b></label><el-slider v-model="settings.temperature" :min="0" :max="2" :step="0.1" /></section>
      <section class="slider-field"><label><span>Top P</span><b>{{ settings.top_p.toFixed(1) }}</b></label><el-slider v-model="settings.top_p" :min="0.1" :max="1" :step="0.1" /></section>
      <section><label>最大输出 Token</label><el-input-number v-model="settings.max_tokens" :min="100" :max="8000" :step="100" controls-position="right" class="full-width" /></section>
      <section><label>历史对话轮数</label><el-input-number v-model="settings.history_rounds" :min="0" :max="20" controls-position="right" class="full-width" /><p class="field-help">默认读取最近 5 轮，不包含当前问题。</p></section>
      <div class="settings-tip"><strong>可信回答模式</strong><p>无可靠知识库依据时不会生成确定性政策结论，并自动进入人工审核队列。</p></div>
    </aside>
  </main>
</template>
