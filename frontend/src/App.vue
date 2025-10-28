<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1>🚀 Qwen3 Fine-tuner</h1>
        <p class="subtitle">Professional fine-tuning platform for Qwen3 models</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="navigateTo('home')">Home</el-button>
        <el-button @click="navigateTo('data')">Data</el-button>
        <el-button @click="navigateTo('training')">Training</el-button>
        <el-button @click="navigateTo('models')">Models</el-button>
        <el-button @click="navigateTo('downloads')">Downloads</el-button>
        <el-button @click="navigateTo('docs')">API Docs</el-button>
      </div>
    </el-header>

    <el-main class="app-main">
      <router-view />
    </el-main>

    <el-footer class="app-footer">
      <p>© 2024 Qwen3 Fine-tuner. All rights reserved.</p>
      <p>Powered by Qwen3, Transformers, PEFT, and Unsloth</p>
    </el-footer>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const navigateTo = (name) => {
  if (name === 'docs') {
    window.open('http://localhost:8000/docs', '_blank')
  } else {
    router.push({ name })
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.header-left h1 {
  font-size: 28px;
  margin: 0;
  font-weight: bold;
}

.header-left .subtitle {
  font-size: 12px;
  margin: 5px 0 0 0;
  opacity: 0.9;
}

.header-right {
  display: flex;
  gap: 10px;
}

.app-main {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

.app-footer {
  background: #f5f7fa;
  border-top: 1px solid #ebeef5;
  text-align: center;
  padding: 20px;
  color: #606266;
}

.app-footer p {
  margin: 5px 0;
  font-size: 13px;
}
</style>
