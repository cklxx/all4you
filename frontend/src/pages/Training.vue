<template>
  <div class="training">
    <el-card>
      <template #header>
        <span style="font-weight: bold">🎯 Training Jobs</span>
      </template>

      <!-- 开始新任务 -->
      <el-button type="primary" size="large" @click="showNewTaskDialog" style="margin-bottom: 20px">
        ➕ Start New Training
      </el-button>

      <!-- 任务列表 -->
      <el-table :data="trainingTasks" stripe style="width: 100%">
        <el-table-column prop="name" label="Task Name" width="150" />
        <el-table-column prop="model_name" label="Model" width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag
              :type="
                row.status === 'completed'
                  ? 'success'
                  : row.status === 'running'
                    ? 'warning'
                    : row.status === 'failed'
                      ? 'danger'
                      : 'info'
              "
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Progress" width="200">
          <template #default="{ row }">
            <div v-if="row.progress">
              <el-progress :percentage="row.progress.percentage || 0" />
              <span style="font-size: 12px">
                {{ row.progress.completed_steps }} / {{ row.progress.total_steps }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Loss" width="100">
          <template #default="{ row }">
            <span v-if="row.progress?.current_loss"> {{ row.progress.current_loss.toFixed(4) }} </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="Created" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewDetails(row)">Details</el-button>
            <el-button type="danger" size="small" @click="deleteTask(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新任务对话框 -->
    <el-dialog v-model="newTaskVisible" title="Start New Training" width="600px">
      <el-form :model="newTaskForm" label-width="120px">
        <el-form-item label="Task Name">
          <el-input v-model="newTaskForm.name" placeholder="e.g., My Qwen3 Finetuning" />
        </el-form-item>

        <el-form-item label="Data File">
          <el-select v-model="newTaskForm.data_file_id" placeholder="Select a data file">
            <el-option v-for="file in dataFiles" :key="file.id" :label="file.filename" :value="file.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="Config">
          <el-select v-model="newTaskForm.config_id" placeholder="Select a configuration">
            <el-option v-for="config in configs" :key="config.id" :label="config.name" :value="config.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="newTaskVisible = false">Cancel</el-button>
        <el-button type="primary" @click="startTraining">Start Training</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailsVisible" title="Task Details" width="700px">
      <div v-if="selectedTask" class="task-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Task ID">{{ selectedTask.id }}</el-descriptions-item>
          <el-descriptions-item label="Task Name">{{ selectedTask.name }}</el-descriptions-item>
          <el-descriptions-item label="Model">{{ selectedTask.model_name }}</el-descriptions-item>
          <el-descriptions-item label="Status">
            <el-tag
              :type="
                selectedTask.status === 'completed'
                  ? 'success'
                  : selectedTask.status === 'running'
                    ? 'warning'
                    : 'danger'
              "
            >
              {{ selectedTask.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Created">{{ new Date(selectedTask.created_at).toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="Started">
            {{ selectedTask.started_at ? new Date(selectedTask.started_at).toLocaleString() : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="Total Steps">{{ selectedTask.total_steps }}</el-descriptions-item>
          <el-descriptions-item label="Completed Steps">{{ selectedTask.completed_steps }}</el-descriptions-item>
          <el-descriptions-item label="Current Loss">{{ selectedTask.current_loss?.toFixed(4) || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="Best Loss">{{ selectedTask.best_loss?.toFixed(4) || 'N/A' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedTask.progress" class="task-progress">
          <el-progress :percentage="detailsProgress" />
          <p class="task-progress__summary">
            {{ selectedTask.progress?.completed_steps || selectedTask.completed_steps }} /
            {{ selectedTask.progress?.total_steps || selectedTask.total_steps }}
          </p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const trainingTasks = ref([])
const dataFiles = ref([])
const configs = ref([])
const newTaskVisible = ref(false)
const detailsVisible = ref(false)
const selectedTask = ref(null)
const newTaskForm = ref({
  name: '',
  data_file_id: '',
  config_id: ''
})
let refreshTimer = null

const calculatePercentage = (completedSteps = 0, totalSteps = 0) => {
  if (!totalSteps || totalSteps <= 0) {
    return 0
  }

  return Math.min(100, Math.max(0, Math.round((completedSteps / totalSteps) * 100)))
}

const normalizeTask = task => {
  if (!task) {
    return null
  }

  const progress = task.progress || {}
  const totalSteps = progress.total_steps ?? task.total_steps ?? 0
  const completedSteps = progress.completed_steps ?? task.completed_steps ?? 0
  const percentage =
    task.progress_percentage ?? progress.percentage ?? calculatePercentage(completedSteps, totalSteps)

  return {
    ...task,
    progress: {
      total_steps: totalSteps,
      completed_steps: completedSteps,
      current_loss: progress.current_loss ?? task.current_loss ?? null,
      best_loss: progress.best_loss ?? task.best_loss ?? null,
      percentage
    },
    progress_percentage: percentage
  }
}

onMounted(() => {
  loadTrainingTasks()
  loadDataFiles()
  loadConfigs()

  // 定期刷新任务状态
  refreshTimer = setInterval(() => {
    loadTrainingTasks()
  }, 5000)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})

const loadTrainingTasks = async () => {
  try {
    const response = await axios.get('/api/train/list')
    const tasks = response.data.data?.tasks || []
    trainingTasks.value = tasks.map(normalizeTask).filter(Boolean)
  } catch (error) {
    console.error('Failed to load training tasks', error)
  }
}

const loadDataFiles = async () => {
  try {
    const response = await axios.get('/api/data/list?limit=100')
    dataFiles.value = response.data.data?.files || []
  } catch (error) {
    console.error('Failed to load data files')
  }
}

const loadConfigs = async () => {
  try {
    const response = await axios.get('/api/config/list?limit=100')
    configs.value = response.data.data?.configs || []
  } catch (error) {
    console.error('Failed to load configs')
  }
}

const showNewTaskDialog = () => {
  newTaskForm.value = { name: '', data_file_id: '', config_id: '' }
  newTaskVisible.value = true
}

const startTraining = async () => {
  try {
    if (!newTaskForm.value.name || !newTaskForm.value.data_file_id || !newTaskForm.value.config_id) {
      ElMessage.error('Please fill all fields')
      return
    }

    await axios.post('/api/train/start', {
      name: newTaskForm.value.name,
      data_file_id: newTaskForm.value.data_file_id,
      config_id: newTaskForm.value.config_id
    })

    ElMessage.success('Training started successfully')
    newTaskVisible.value = false
    loadTrainingTasks()
  } catch (error) {
    ElMessage.error('Failed to start training')
  }
}

const viewDetails = async (task) => {
  try {
    const response = await axios.get(`/api/train/status/${task.id}`)
    const normalized = normalizeTask(response.data)
    if (!normalized) {
      throw new Error('Invalid task response')
    }
    selectedTask.value = normalized
    detailsVisible.value = true
  } catch (error) {
    ElMessage.error('Failed to load task details')
  }
}

const deleteTask = (task) => {
  ElMessageBox.confirm('Delete this training task?', 'Warning', {
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    type: 'warning'
  })
    .then(async () => {
      try {
        await axios.delete(`/api/train/${task.id}`)
        ElMessage.success('Task deleted successfully')
        loadTrainingTasks()
      } catch (error) {
        ElMessage.error('Failed to delete task')
      }
    })
    .catch(() => {})
}

const detailsProgress = computed(() => {
  if (!selectedTask.value) {
    return 0
  }

  return selectedTask.value.progress?.percentage ?? 0
})
</script>

<style scoped>
.training {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.task-details {
  padding: 20px;
}

.task-progress {
  margin-top: 20px;
}

.task-progress__summary {
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
}
</style>
