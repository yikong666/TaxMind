import { computed, onMounted, ref } from 'vue'

import { fetchCaptcha } from '@/api/auth'
import { getErrorMessage } from '@/api/http'

export function useCaptcha() {
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
