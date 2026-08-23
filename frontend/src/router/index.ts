import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
const ChatView = () => import('@/views/ChatView.vue')
const KnowledgeBasesView = () => import('@/views/KnowledgeBasesView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/chat', name: 'chat', component: ChatView, meta: { requiresAuth: true } },
    { path: '/knowledge-bases', name: 'knowledge-bases', component: KnowledgeBasesView, meta: { requiresAuth: true } },
  ],
})

// 页面守卫只判断 Token 是否存在，签名和过期时间仍由后端统一验证。
router.beforeEach((to) => {
  const authenticated = Boolean(sessionStorage.getItem('taxmind_access_token'))
  if (to.meta.requiresAuth && !authenticated) return { name: 'login' }
  if ((to.name === 'login' || to.name === 'register') && authenticated) return { name: 'chat' }
})

export default router
