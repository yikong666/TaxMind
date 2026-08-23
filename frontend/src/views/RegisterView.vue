<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '@/api/auth'
import { getErrorMessage } from '@/api/http'
import { useCaptcha } from '@/composables/useCaptcha'

const router = useRouter()
const submitting = ref(false)
const form = reactive({ username: '', password: '', confirm_password: '', captcha_code: '' })
const { captchaId, captchaImageUrl, captchaLoading, captchaError, refreshCaptcha } = useCaptcha()

async function submitRegister() {
  if (!form.username || !form.password || !form.confirm_password || !form.captcha_code) return ElMessage.warning('请完整填写注册信息')
  if (form.password !== form.confirm_password) return ElMessage.warning('两次输入的密码不一致')
  submitting.value = true
  try {
    await register({ ...form, captcha_id: captchaId.value })
    ElMessage.success('注册成功，请登录')
    await router.push('/login')
  } catch (error) {
    ElMessage.error(getErrorMessage(error))
    form.captcha_code = ''
    await refreshCaptcha()
  } finally { submitting.value = false }
}
</script>

<template>
  <main class="login-page register-page">
    <section class="brand-panel">
      <div class="brand-mark">税</div><p class="eyebrow">TAXMIND · 税智通</p>
      <h1>创建你的<br />财税知识工作台</h1>
      <p class="brand-copy">统一管理政策知识、历史问答与人工反馈，让团队经验持续沉淀。</p>
    </section>
    <section class="form-panel"><div class="login-card">
      <p class="card-kicker">创建账号</p><h2>注册 TaxMind</h2>
      <p class="card-subtitle">用户名支持中文、字母、数字、下划线和连字符</p>
      <el-form :model="form" label-position="top" size="large" @submit.prevent="submitRegister">
        <el-form-item label="用户名"><el-input v-model="form.username" placeholder="至少 3 个字符" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password placeholder="至少 8 个字符" /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入密码" /></el-form-item>
        <el-form-item label="图形验证码" :error="captchaError"><div class="captcha-row">
          <el-input v-model="form.captcha_code" maxlength="8" placeholder="请输入验证码" />
          <button class="captcha-placeholder" type="button" :disabled="captchaLoading" @click="refreshCaptcha">
            <img v-if="captchaImageUrl" :src="captchaImageUrl" alt="图形验证码" /><span v-else>{{ captchaLoading ? '加载中' : '点击刷新' }}</span>
          </button>
        </div></el-form-item>
        <el-button class="login-button" type="primary" native-type="submit" :loading="submitting">注册账号</el-button>
      </el-form>
      <p class="register-hint">已有账号？<router-link to="/login">返回登录</router-link></p>
    </div></section>
  </main>
</template>
