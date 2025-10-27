<template>
  <div class="home">
    <!-- 欢迎区域 -->
    <el-card class="welcome-card">
      <div class="welcome-content">
        <h2>Welcome to Qwen3 Fine-tuner</h2>
        <p>A professional platform for fine-tuning Qwen3 LLM models with an intuitive web interface.</p>
        <div class="feature-grid">
          <div class="feature-item">
            <div class="feature-icon">📊</div>
            <div class="feature-text">
              <h4>Data Management</h4>
              <p>Upload and manage your training data with support for multiple formats</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🚀</div>
            <div class="feature-text">
              <h4>Efficient Training</h4>
              <p>Integrated with Unsloth, FlashAttention-2, and quantization techniques</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">⚙️</div>
            <div class="feature-text">
              <h4>Multiple Methods</h4>
              <p>Support for SFT, LoRA, QLoRA, DPO, and GRPO training methods</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">📈</div>
            <div class="feature-text">
              <h4>Real-time Monitoring</h4>
              <p>Track training progress with detailed metrics and logs</p>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 快速开始 -->
    <el-card class="quick-start-card">
      <template #header>
        <span style="font-weight: bold">Quick Start</span>
      </template>
      <el-steps :active="activeStep" align-center>
        <el-step title="Prepare Data" description="Upload your training dataset"></el-step>
        <el-step title="Choose Model" description="Select a Qwen3 model"></el-step>
        <el-step title="Configure Training" description="Set training parameters"></el-step>
        <el-step title="Start Training" description="Launch the fine-tuning job"></el-step>
      </el-steps>
      <div class="quick-start-actions">
        <el-button type="primary" size="large" @click="goToData">📁 Upload Data</el-button>
        <el-button type="primary" size="large" @click="goToTraining">🎯 Start Training</el-button>
        <el-button type="primary" size="large" @click="goToModels">🤖 View Models</el-button>
      </div>
    </el-card>

    <!-- 系统统计 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.dataFiles }}</div>
            <div class="stat-label">Data Files</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.trainingTasks }}</div>
            <div class="stat-label">Training Tasks</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.completedTasks }}</div>
            <div class="stat-label">Completed</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.runningTasks }}</div>
            <div class="stat-label">Running</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 文档和支持 -->
    <el-card class="doc-card">
      <template #header>
        <span style="font-weight: bold">Documentation & Support</span>
      </template>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8">
          <div class="doc-item">
            <h4>📚 API Documentation</h4>
            <p>Explore the complete REST API with interactive Swagger UI</p>
            <el-button text type="primary" @click="openDocs">View API Docs</el-button>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="doc-item">
            <h4>🎓 User Guide</h4>
            <p>Step-by-step guide to get started with fine-tuning</p>
            <el-button text type="primary">Read Guide</el-button>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="doc-item">
            <h4>🔗 Resources</h4>
            <p>Links to Qwen3, Unsloth, and other related resources</p>
            <el-button text type="primary">View Resources</el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const activeStep = ref(0)
const stats = ref({
  dataFiles: 0,
  trainingTasks: 0,
  completedTasks: 0,
  runningTasks: 0
})

onMounted(async () => {
  try {
    // 获取统计数据
    const dataRes = await axios.get('/api/data/list?limit=1')
    const trainingRes = await axios.get('/api/train/list?limit=1')

    stats.value.dataFiles = dataRes.data.data?.total || 0
    stats.value.trainingTasks = trainingRes.data.data?.total || 0

    // 计算已完成和正在运行的任务
    const allTasks = await axios.get('/api/train/list?limit=100')
    const tasks = allTasks.data.data?.tasks || []
    stats.value.completedTasks = tasks.filter(t => t.status === 'completed').length
    stats.value.runningTasks = tasks.filter(t => t.status === 'running').length
  } catch (error) {
    console.error('Error loading stats:', error)
  }
})

const goToData = () => {
  router.push({ name: 'data' })
}

const goToTraining = () => {
  router.push({ name: 'training' })
}

const goToModels = () => {
  router.push({ name: 'models' })
}

const openDocs = () => {
  window.open('http://localhost:8000/docs', '_blank')
}
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.welcome-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.welcome-content h2 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 28px;
}

.welcome-content p {
  margin: 0 0 25px 0;
  color: #666;
  font-size: 16px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.feature-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border-radius: 6px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.feature-item:hover {
  background: #e6f7ff;
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.feature-text h4 {
  margin: 0 0 5px 0;
  color: #333;
}

.feature-text p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.quick-start-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.quick-start-actions {
  display: flex;
  gap: 15px;
  margin-top: 30px;
  flex-wrap: wrap;
}

.stat-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-content {
  padding: 20px;
}

.stat-number {
  font-size: 32px;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.doc-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.doc-item {
  padding: 20px;
  text-align: center;
  border-radius: 6px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.doc-item:hover {
  background: #e6f7ff;
}

.doc-item h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.doc-item p {
  margin: 0 0 15px 0;
  color: #666;
  font-size: 14px;
}
</style>
