<template>
  <div class="downloads-page">
    <el-row :gutter="20">
      <!-- Left Column: Download New Resources -->
      <el-col :xs="24" :sm="24" :md="12">
        <!-- Download Models -->
        <el-card class="download-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><Download /></el-icon> 下载模型</span>
            </div>
          </template>

          <el-form :model="modelForm" label-width="100px">
            <el-form-item label="选择模型">
              <el-select
                v-model="modelForm.selectedModel"
                placeholder="请选择要下载的模型"
                style="width: 100%"
              >
                <el-option
                  v-for="model in availableModels"
                  :key="model.model_name"
                  :label="`${model.model_name} (${model.model_size})`"
                  :value="model.model_name"
                >
                  <div class="model-option">
                    <span>{{ model.model_name }}</span>
                    <el-tag
                      v-if="model.recommended"
                      size="small"
                      type="success"
                      style="margin-left: 10px"
                    >
                      推荐
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="modelForm.forceDownload">
                强制重新下载（覆盖缓存）
              </el-checkbox>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="downloadModel"
                :loading="modelForm.downloading"
                :disabled="!modelForm.selectedModel"
              >
                <el-icon><Download /></el-icon>
                开始下载
              </el-button>
            </el-form-item>
          </el-form>

          <!-- Cached Models -->
          <el-divider>已缓存的模型</el-divider>
          <el-table :data="cachedModels" style="width: 100%" size="small">
            <el-table-column prop="model_name" label="模型名称" />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="scope">
                {{ formatSize(scope.row.size) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="scope">
                <el-button
                  link
                  type="danger"
                  size="small"
                  @click="clearModelCache(scope.row.model_name)"
                >
                  清除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- Download Datasets -->
        <el-card class="download-card" shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span><el-icon><FolderOpened /></el-icon> 下载数据集</span>
            </div>
          </template>

          <el-form :model="datasetForm" label-width="100px">
            <el-form-item label="选择数据集">
              <el-select
                v-model="datasetForm.selectedPreset"
                placeholder="请选择预设数据集"
                style="width: 100%"
                @change="onDatasetPresetChange"
              >
                <el-option
                  v-for="preset in datasetPresets"
                  :key="preset.name"
                  :label="preset.name"
                  :value="preset.name"
                >
                  <div style="display: flex; flex-direction: column">
                    <span>{{ preset.name }}</span>
                    <span style="font-size: 12px; color: #999">
                      {{ preset.description }}
                    </span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="数据集 ID">
              <el-input
                v-model="datasetForm.datasetId"
                placeholder="或输入自定义 ModelScope 数据集 ID"
              />
            </el-form-item>

            <el-form-item label="数据拆分">
              <el-select
                v-model="datasetForm.split"
                placeholder="选择数据拆分"
                style="width: 100%"
              >
                <el-option label="train" value="train" />
                <el-option label="validation" value="validation" />
                <el-option label="test" value="test" />
              </el-select>
            </el-form-item>

            <el-form-item label="样本限制">
              <el-input-number
                v-model="datasetForm.limit"
                :min="0"
                :max="100000"
                placeholder="不限制"
                style="width: 100%"
              />
              <span style="font-size: 12px; color: #999; margin-left: 10px">
                留空表示下载全部样本
              </span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="downloadDataset"
                :loading="datasetForm.downloading"
                :disabled="!datasetForm.datasetId"
              >
                <el-icon><Download /></el-icon>
                开始下载
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Right Column: Download Tasks -->
      <el-col :xs="24" :sm="24" :md="12">
        <el-card class="download-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><List /></el-icon> 下载任务</span>
              <el-button
                size="small"
                @click="loadDownloadTasks"
                :icon="Refresh"
              >
                刷新
              </el-button>
            </div>
          </template>

          <el-empty v-if="downloadTasks.length === 0" description="暂无下载任务" />

          <el-timeline v-else>
            <el-timeline-item
              v-for="task in downloadTasks"
              :key="task.id"
              :timestamp="task.message"
              placement="top"
              :type="getTaskType(task.status)"
            >
              <el-card>
                <template #header>
                  <div class="task-header">
                    <span>{{ task.name_or_id }}</span>
                    <el-tag
                      :type="getTaskTagType(task.status)"
                      size="small"
                    >
                      {{ getTaskStatusText(task.status) }}
                    </el-tag>
                  </div>
                </template>

                <div v-if="task.status === 'running'">
                  <el-progress
                    :percentage="task.progress"
                    :status="task.progress === 100 ? 'success' : undefined"
                  />
                  <p style="margin-top: 10px; font-size: 14px; color: #666">
                    {{ task.message }}
                  </p>
                </div>

                <div v-else-if="task.status === 'completed'">
                  <p style="color: #67c23a; margin-bottom: 10px">
                    <el-icon><CircleCheck /></el-icon>
                    {{ task.message }}
                  </p>
                  <el-descriptions :column="1" size="small" border>
                    <el-descriptions-item label="输出路径">
                      {{ task.output_path }}
                    </el-descriptions-item>
                    <el-descriptions-item
                      v-if="task.metadata"
                      label="样本数量"
                    >
                      {{ task.metadata.total_samples }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>

                <div v-else-if="task.status === 'failed'">
                  <el-alert
                    :title="task.message"
                    type="error"
                    :closable="false"
                  />
                  <p
                    v-if="task.error"
                    style="margin-top: 10px; font-size: 12px; color: #f56c6c"
                  >
                    错误详情: {{ task.error }}
                  </p>
                </div>

                <div v-else>
                  <p style="color: #909399">{{ task.message }}</p>
                </div>

                <div style="margin-top: 15px; text-align: right">
                  <el-button
                    v-if="
                      task.status === 'pending' || task.status === 'running'
                    "
                    size="small"
                    type="danger"
                    @click="cancelDownload(task.id)"
                  >
                    取消
                  </el-button>
                  <el-button
                    v-if="
                      task.status === 'completed' ||
                      task.status === 'failed' ||
                      task.status === 'cancelled'
                    "
                    size="small"
                    @click="removeTask(task.id)"
                  >
                    移除
                  </el-button>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download,
  FolderOpened,
  List,
  Refresh,
  CircleCheck,
} from '@element-plus/icons-vue'

// Model download form
const modelForm = ref({
  selectedModel: '',
  forceDownload: false,
  downloading: false,
})

// Dataset download form
const datasetForm = ref({
  selectedPreset: '',
  datasetId: '',
  split: 'train',
  limit: null,
  downloading: false,
})

// Data
const availableModels = ref([])
const cachedModels = ref([])
const datasetPresets = ref([])
const downloadTasks = ref([])

// Auto-refresh timer
let refreshTimer = null

// Load available models
async function loadModels() {
  try {
    const response = await axios.get('/api/models/list')
    availableModels.value = response.data.data.models
  } catch (error) {
    console.error('Failed to load models:', error)
    ElMessage.error('加载模型列表失败')
  }
}

// Load cached models
async function loadCachedModels() {
  try {
    const response = await axios.get('/api/models/cache/list')
    cachedModels.value = response.data.data.models
  } catch (error) {
    console.error('Failed to load cached models:', error)
  }
}

// Load dataset presets
async function loadDatasetPresets() {
  try {
    const response = await axios.get('/api/datasets/presets')
    datasetPresets.value = response.data.data.presets
  } catch (error) {
    console.error('Failed to load dataset presets:', error)
    ElMessage.error('加载数据集预设失败')
  }
}

// Load download tasks
async function loadDownloadTasks() {
  try {
    const response = await axios.get('/api/datasets/downloads/list')
    downloadTasks.value = response.data.data.tasks.reverse() // Show latest first
  } catch (error) {
    console.error('Failed to load download tasks:', error)
  }
}

// Download model
async function downloadModel() {
  modelForm.value.downloading = true
  try {
    const response = await axios.post('/api/models/download', null, {
      params: {
        model_name: modelForm.value.selectedModel,
        force: modelForm.value.forceDownload,
      },
    })

    if (response.data.success) {
      ElMessage.success(response.data.message)
      await loadCachedModels()
    }
  } catch (error) {
    console.error('Failed to download model:', error)
    ElMessage.error('模型下载失败: ' + error.message)
  } finally {
    modelForm.value.downloading = false
  }
}

// Download dataset
async function downloadDataset() {
  datasetForm.value.downloading = true
  try {
    const response = await axios.post('/api/datasets/download', null, {
      params: {
        name_or_id: datasetForm.value.datasetId,
        split: datasetForm.value.split,
        limit: datasetForm.value.limit || undefined,
      },
    })

    if (response.data.success) {
      ElMessage.success('数据集下载已开始')
      await loadDownloadTasks()

      // Start monitoring task
      if (refreshTimer === null) {
        refreshTimer = setInterval(loadDownloadTasks, 3000)
      }
    }
  } catch (error) {
    console.error('Failed to download dataset:', error)
    ElMessage.error('数据集下载失败: ' + error.message)
  } finally {
    datasetForm.value.downloading = false
  }
}

// Clear model cache
async function clearModelCache(modelName) {
  try {
    await ElMessageBox.confirm(
      `确定要清除 ${modelName} 的缓存吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const encodedName = modelName.replace('/', '_')
    await axios.delete(`/api/models/cache/${encodedName}`)
    ElMessage.success('缓存已清除')
    await loadCachedModels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to clear cache:', error)
      ElMessage.error('清除缓存失败')
    }
  }
}

// Cancel download
async function cancelDownload(taskId) {
  try {
    await axios.delete(`/api/datasets/download/${taskId}`)
    ElMessage.success('下载已取消')
    await loadDownloadTasks()
  } catch (error) {
    console.error('Failed to cancel download:', error)
    ElMessage.error('取消下载失败')
  }
}

// Remove task from list
async function removeTask(taskId) {
  try {
    await axios.delete(`/api/datasets/download/${taskId}`)
    await loadDownloadTasks()
  } catch (error) {
    console.error('Failed to remove task:', error)
    ElMessage.error('移除任务失败')
  }
}

// On dataset preset change
function onDatasetPresetChange(presetName) {
  const preset = datasetPresets.value.find((p) => p.name === presetName)
  if (preset) {
    datasetForm.value.datasetId = preset.dataset_id
    datasetForm.value.split = preset.split || 'train'
  }
}

// Get task type for timeline
function getTaskType(status) {
  const typeMap = {
    pending: 'primary',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return typeMap[status] || 'info'
}

// Get task tag type
function getTaskTagType(status) {
  const typeMap = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return typeMap[status] || 'info'
}

// Get task status text
function getTaskStatusText(status) {
  const textMap = {
    pending: '等待中',
    running: '下载中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return textMap[status] || status
}

// Format file size
function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// Initialize
onMounted(async () => {
  await Promise.all([
    loadModels(),
    loadCachedModels(),
    loadDatasetPresets(),
    loadDownloadTasks(),
  ])

  // Start auto-refresh if there are running tasks
  const hasRunningTasks = downloadTasks.value.some(
    (t) => t.status === 'running' || t.status === 'pending'
  )
  if (hasRunningTasks) {
    refreshTimer = setInterval(loadDownloadTasks, 3000)
  }
})

// Cleanup
onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.downloads-page {
  padding: 20px;
}

.download-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.model-option {
  display: flex;
  align-items: center;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-timeline-item__timestamp) {
  font-size: 12px;
  color: #909399;
}
</style>
