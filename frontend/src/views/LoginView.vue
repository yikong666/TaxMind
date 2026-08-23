<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue'
import { reactive } from 'vue'

const form = reactive({ username: '', password: '', captcha: '' })
</script>

<template>
  <main class="login-page">
    <section class="brand-panel">
      <div class="brand-mark">税</div>
      <p class="eyebrow">TAXMIND · 税智通</p>
      <h1>让每一次财税问答<br />都有据可查</h1>
      <p class="brand-copy">
        基于权威政策知识库，为财税服务人员提供带文号、有效期与来源引用的智能回答。
      </p>
      <div class="trust-list">
        <span>政策时效校验</span><span>地区口径隔离</span><span>来源完整引用</span>
      </div>
    </section>

    <section class="form-panel">
      <div class="login-card">
        <p class="card-kicker">欢迎回来</p>
        <h2>登录 TaxMind</h2>
        <p class="card-subtitle">请输入工作账号继续使用财税知识助手</p>
        <el-form :model="form" label-position="top" size="large">
          <el-form-item label="用户名">
            <el-input v-model="form.username" :prefix-icon="User" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" :prefix-icon="Lock" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
          <el-form-item label="图形验证码">
            <div class="captcha-row">
              <el-input v-model="form.captcha" placeholder="请输入验证码" />
              <button class="captcha-placeholder" type="button" aria-label="刷新验证码">A7K9</button>
            </div>
          </el-form-item>
          <el-button class="login-button" type="primary">登录</el-button>
        </el-form>
        <p class="register-hint">还没有账号？<a href="#">注册新账号</a></p>
      </div>
      <p class="legal">TaxMind 提供政策信息辅助，不替代主管税务机关或专业人员的最终判断。</p>
    </section>
  </main>
</template>
