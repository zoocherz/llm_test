<template>
  <div class="runs-view">
    <h2>Test Runs History</h2>
    
    <el-card class="mb-4">
      <div class="card-header">
        <span>Run New Test</span>
        <el-button type="primary" @click="showRunDialog = true">+ Run Test</el-button>
      </div>
    </el-card>
    
    <el-table :data="runs" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="task_id" label="Task ID" width="80" />
      <el-table-column prop="model_name" label="Model" />
      <el-table-column prop="status" label="Status" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total_time" label="Time (s)" width="90" />
      <el-table-column prop="total_cost" label="Cost ($)" width="90" />
      <el-table-column prop="average_judge_score" label="Judge Score" width="100">
        <template #default="{ row }">
          {{ row.average_judge_score ? row.average_judge_score.toFixed(2) : 'N/A' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Date" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="viewResults(row)">Results</el-button>
          <el-button size="small" type="success" @click="exportResults(row.id, 'csv')">CSV</el-button>
          <el-button size="small" type="success" @click="exportResults(row.id, 'xlsx')">Excel</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- Run Dialog -->
    <el-dialog v-model="showRunDialog" title="Run New Test">
      <el-form :model="runForm" label-width="120px">
        <el-form-item label="Task" required>
          <el-select v-model="runForm.task_id" placeholder="Select task" style="width: 100%">
            <el-option v-for="task in tasks" :key="task.id" :label="task.name" :value="task.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="Model Name" required>
          <el-input v-model="runForm.model_name" placeholder="e.g., llama-3-8b-instruct" />
        </el-form-item>
        
        <el-form-item label="Provider (optional)">
          <el-select v-model="runForm.provider_id" placeholder="Use provider pool" clearable style="width: 100%">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="Judge Model">
          <el-input v-model="judgeModel" placeholder="gpt-4o-mini" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showRunDialog = false">Cancel</el-button>
        <el-button type="primary" @click="runTest" :loading="running">Run Test</el-button>
      </template>
    </el-dialog>
    
    <!-- Results Dialog -->
    <el-dialog v-model="showResultsDialog" title="Test Results" width="80%">
      <div v-if="currentRun">
        <h3>Run #{{ currentRun.id }} - {{ currentRun.model_name }}</h3>
        <p>Status: {{ currentRun.status }} | Time: {{ currentRun.total_time?.toFixed(2) }}s | Cost: ${{ currentRun.total_cost?.toFixed(4) }}</p>
        
        <el-table :data="results" stripe>
          <el-table-column prop="test_case_id" label="Case ID" width="80" />
          <el-table-column prop="provider_used" label="Provider" />
          <el-table-column prop="response_time" label="Time (s)" width="90" />
          <el-table-column prop="cost" label="Cost ($)" width="90" />
          <el-table-column prop="judge_score" label="Score" width="80">
            <template #default="{ row }">
              <el-tag :type="getScoreType(row.judge_score)">{{ row.judge_score?.toFixed(2) || 'N/A' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="judge_feedback" label="Feedback" show-overflow-tooltip />
          <el-table-column label="Response" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="viewResponse(row)">View</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <template #footer>
        <el-button @click="showResultsDialog = false">Close</el-button>
      </template>
    </el-dialog>
    
    <!-- Response Dialog -->
    <el-dialog v-model="showResponseDialog" title="Model Response" width="70%">
      <div v-if="currentResult">
        <h4>Response from {{ currentResult.provider_used }}</h4>
        <el-input 
          v-model="currentResult.model_response" 
          type="textarea" 
          rows="15" 
          readonly
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { tasksApi, providersApi } from '../api'

const runs = ref([])
const tasks = ref([])
const providers = ref([])
const results = ref([])
const loading = ref(false)
const running = ref(false)
const showRunDialog = ref(false)
const showResultsDialog = ref(false)
const showResponseDialog = ref(false)
const currentRun = ref(null)
const currentResult = ref(null)

const runForm = ref({
  task_id: null,
  model_name: '',
  provider_id: null,
})

const judgeModel = ref('gpt-4o-mini')

const loadRuns = async () => {
  loading.value = true
  try {
    const res = await tasksApi.getRuns({ limit: 100 })
    runs.value = res.data
  } catch (e) {
    ElMessage.error('Failed to load runs')
  } finally {
    loading.value = false
  }
}

const loadTasks = async () => {
  try {
    const res = await tasksApi.getAll()
    tasks.value = res.data.filter(t => t.is_active)
  } catch (e) {}
}

const loadProviders = async () => {
  try {
    const res = await providersApi.getAll({ is_active: true })
    providers.value = res.data
  } catch (e) {}
}

const runTest = async () => {
  if (!runForm.value.task_id || !runForm.value.model_name) {
    ElMessage.warning('Please fill required fields')
    return
  }
  
  running.value = true
  try {
    await tasksApi.runTest(runForm.value, judgeModel.value)
    ElMessage.success('Test completed!')
    showRunDialog.value = false
    runForm.value = { task_id: null, model_name: '', provider_id: null }
    loadRuns()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Test execution failed')
  } finally {
    running.value = false
  }
}

const viewResults = async (run) => {
  currentRun.value = run
  try {
    const res = await tasksApi.getRunResults(run.id)
    results.value = res.data
    showResultsDialog.value = true
  } catch (e) {
    ElMessage.error('Failed to load results')
  }
}

const viewResponse = (result) => {
  currentResult.value = result
  showResponseDialog.value = true
}

const exportResults = async (runId, format) => {
  try {
    const res = await tasksApi.exportResults(runId, format)
    const blob = new Blob([res.data], { type: res.headers['content-type'] })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `test_run_${runId}.${format}`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Export successful')
  } catch (e) {
    ElMessage.error('Export failed')
  }
}

const getStatusType = (status) => {
  const map = { completed: 'success', running: 'warning', failed: 'danger', pending: 'info' }
  return map[status] || 'info'
}

const getScoreType = (score) => {
  if (score === null || score === undefined) return 'info'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  loadRuns()
  loadTasks()
  loadProviders()
})
</script>

<style scoped>
.mb-4 { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
