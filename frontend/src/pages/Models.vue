<template>
  <div class="models">
    <el-card>
      <template #header>
        <span style="font-weight: bold">🤖 Available Models</span>
      </template>

      <el-row :gutter="20">
        <el-col v-for="model in models" :key="model.model_name" :xs="24" :sm="12" :md="8">
          <div class="model-card">
            <div class="model-header">
              <h3>{{ model.model_name }}</h3>
              <el-tag type="info">{{ model.model_size }}</el-tag>
            </div>

            <div class="model-content">
              <p><strong>Parameters:</strong> {{ formatNumber(model.parameters) }}</p>
              <p><strong>Max Sequence:</strong> {{ model.max_seq_length }}</p>
              <p><strong>Description:</strong> {{ model.description }}</p>

              <div class="training-methods">
                <strong>Supported Methods:</strong>
                <div style="margin-top: 8px">
                  <el-tag v-for="method in model.supported_training_methods" :key="method" style="margin: 3px">
                    {{ method.toUpperCase() }}
                  </el-tag>
                </div>
              </div>
            </div>

            <div class="model-footer">
              <el-button type="primary" @click="selectModel(model)">Select Model</el-button>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 训练方法说明 -->
    <el-card>
      <template #header>
        <span style="font-weight: bold">📚 Training Methods</span>
      </template>

      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" v-for="(desc, method) in trainingMethods" :key="method">
          <div class="method-card">
            <h4>{{ method.toUpperCase() }}</h4>
            <p>{{ desc }}</p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 配置模板 -->
    <el-card>
      <template #header>
        <span style="font-weight: bold">⚙️ Training Configurations</span>
      </template>

      <el-table :data="configs" stripe style="width: 100%">
        <el-table-column prop="name" label="Config Name" width="200" />
        <el-table-column prop="model_name" label="Model" width="200" show-overflow-tooltip />
        <el-table-column prop="training_method" label="Method" width="100" />
        <el-table-column prop="description" label="Description" show-overflow-tooltip />
        <el-table-column prop="is_default" label="Default" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">Yes</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="150">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewConfig(row)">View</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 配置详情对话框 -->
    <el-dialog v-model="configVisible" title="Configuration Details" width="700px">
      <div v-if="selectedConfig" class="config-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Name">{{ selectedConfig.name }}</el-descriptions-item>
          <el-descriptions-item label="Model">{{ selectedConfig.model_name }}</el-descriptions-item>
          <el-descriptions-item label="Method">{{ selectedConfig.training_method }}</el-descriptions-item>
          <el-descriptions-item label="Description">{{ selectedConfig.description }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 20px; margin-bottom: 10px">Training Parameters</h4>
        <el-table :data="configParams" size="small" style="width: 100%">
          <el-table-column prop="key" label="Parameter" width="200" />
          <el-table-column prop="value" label="Value" />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const models = ref([])
const configs = ref([])
const configVisible = ref(false)
const selectedConfig = ref(null)
const configParams = ref([])

const trainingMethods = {
  sft: 'Supervised Fine-Tuning (SFT) - Train on instruction-output pairs for basic supervised learning',
  lora:
    'Low-Rank Adaptation (LoRA) - Parameter-efficient fine-tuning by adding low-rank matrices to attention weights',
  qlora: 'Quantized LoRA - Combines 4-bit quantization with LoRA for minimal memory usage',
  dpo: 'Direct Preference Optimization - Optimize model preferences directly without reinforcement learning',
  grpo: 'Group Relative Policy Optimization - Efficient preference optimization with grouped samples'
}

onMounted(() => {
  loadModels()
  loadConfigs()
})

const loadModels = async () => {
  try {
    const response = await axios.get('/api/models/list')
    models.value = response.data.data?.models || []
  } catch (error) {
    ElMessage.error('Failed to load models')
  }
}

const loadConfigs = async () => {
  try {
    const response = await axios.get('/api/config/list?limit=100')
    configs.value = response.data.data?.configs || []
  } catch (error) {
    ElMessage.error('Failed to load configurations')
  }
}

const formatNumber = (num) => {
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  return num.toString()
}

const selectModel = (model) => {
  ElMessage.info(`Selected model: ${model.model_name}. Go to Data Management to upload data and start training.`)
  router.push({ name: 'training' })
}

const viewConfig = (config) => {
  selectedConfig.value = config
  configParams.value = Object.entries(config.config || {}).map(([key, value]) => ({
    key,
    value: JSON.stringify(value)
  }))
  configVisible.value = true
}
</script>

<style scoped>
.models {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.model-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.model-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-header h3 {
  margin: 0;
  color: #333;
  font-size: 16px;
}

.model-content {
  flex: 1;
}

.model-content p {
  margin: 8px 0;
  font-size: 14px;
  color: #666;
}

.training-methods {
  margin-top: 10px;
}

.model-footer {
  text-align: center;
}

.method-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 20px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.method-card:hover {
  background: #e6f7ff;
  border-color: #667eea;
}

.method-card h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.method-card p {
  margin: 0;
  font-size: 13px;
  color: #666;
}

.config-details {
  padding: 20px;
}
</style>
