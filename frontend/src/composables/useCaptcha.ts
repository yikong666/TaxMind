import { computed, onMounted, ref } from 'vue'

import { fetchCaptcha } from '@/api/auth'
import { getErrorMessage } from '@/api/http'

export function useCaptcha() {
  // 验证码状态封装为组合式函数，登录和注册页面复用刷新与异常处理。
  const captchaId = ref('')
  const captchaSvg = ref('')
  const captchaLoading = ref(false)
  const captchaError = ref('')
  const captchaImageUrl = computed(() => captchaSvg.value ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(captchaSvg.value)}` : '')
  async function refreshCaptcha() {
    captchaLoading.value = true
    captchaError.value = ''
    try {
      const challenge = await fetchCaptcha()
      captchaId.value = challenge.captcha_id
      captchaSvg.value = challenge.image_svg
    } catch (error) {
      captchaError.value = getErrorMessage(error)
    } finally {
      captchaLoading.value = false
    }
  }
  onMounted(refreshCaptcha)
  return { captchaId, captchaImageUrl, captchaLoading, captchaError, refreshCaptcha }
}
