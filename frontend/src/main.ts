import 'element-plus/dist/index.css'
import './styles/main.css'

import ElementPlus from 'element-plus'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

// 全局插件在唯一入口注册，页面组件只关注具体业务交互。
createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
