<template>
  <div class="data-management">
    <el-card>
      <template #header>
        <span style="font-weight: bold">📁 Data Management</span>
      </template>

      <!-- 上传区域 -->
      <el-upload
        drag
        action="/api/data/upload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :multiple="true"
        class="upload-area"
        accept=".json,.jsonl,.csv,.txt"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          Drop file here or <em>click to upload</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            Supported formats: JSON, JSONL, CSV, TXT
            <br />
            Max file size: 500MB
          </div>
        </template>
      </el-upload>

      <!-- 数据列表 -->
      <div style="margin-top: 30px">
        <h3>Uploaded Data Files</h3>
        <el-table :data="dataFiles" stripe style="width: 100%; margin-top: 15px">
          <el-table-column prop="filename" label="Filename" width="200" />
          <el-table-column prop="file_type" label="Type" width="100" />
          <el-table-column prop="format_type" label="Format" width="100" />
          <el-table-column prop="total_samples" label="Samples" width="100" />
          <el-table-column prop="file_size" label="Size (KB)" width="100">
            <template #default="{ row }">
              {{ (row.file_size / 1024).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="Upload Time" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="200">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="handlePreviewData(row)">Preview</el-button>
              <el-button type="danger" size="small" @click="deleteData(row)">Delete</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewVisible" title="Data Preview" width="80%">
      <div v-if="previewData" class="preview-content">
        <p>Total Samples: {{ previewData.total_samples }}</p>
        <p>Preview Count: {{ previewData.preview_count }}</p>
        <el-table :data="previewData.samples" stripe style="width: 100%; margin-top: 15px">
          <el-table-column
            v-for="(value, key) in previewData.samples[0] || {}"
            :key="key"
            :prop="key"
            :label="key"
            show-overflow-tooltip
          />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'

const dataFiles = ref([])
const previewVisible = ref(false)
const previewData = ref(null)

onMounted(() => {
  loadDataFiles()
})

const loadDataFiles = async () => {
  try {
    const response = await axios.get('/api/data/list')
    dataFiles.value = response.data.data?.files || []
  } catch (error) {
    ElMessage.error('Failed to load data files')
  }
}

const handleUploadSuccess = (response) => {
  ElMessage.success('File uploaded successfully')
  loadDataFiles()
}

const handleUploadError = () => {
  ElMessage.error('File upload failed')
}

const handlePreviewData = async (row) => {
  try {
    const response = await axios.post('/api/data/preview', {
      file_id: row.id,
      limit: 10
    })
    previewData.value = response.data
    previewVisible.value = true
  } catch (error) {
    ElMessage.error('Failed to preview data')
  }
}

const deleteData = (row) => {
  ElMessageBox.confirm(
    'This will delete the data file. Continue?',
    'Warning',
    { confirmButtonText: 'Delete', cancelButtonText: 'Cancel', type: 'warning' }
  )
    .then(async () => {
      try {
        await axios.delete(`/api/data/${row.id}`)
        ElMessage.success('File deleted successfully')
        loadDataFiles()
      } catch (error) {
        ElMessage.error('Failed to delete file')
      }
    })
    .catch(() => {})
}
</script>

<style scoped>
.data-management {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-area {
  border: 2px dashed #667eea;
  border-radius: 6px;
  padding: 20px;
}

.preview-content {
  max-height: 600px;
  overflow-y: auto;
}
</style>
