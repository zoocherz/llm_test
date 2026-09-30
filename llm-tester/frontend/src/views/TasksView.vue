<template>
  <div class="tasks-view">
    <h2>Tasks Management</h2>
    
    <el-card class="mb-4">
      <div class="card-header">
        <span>Create New Task</span>
        <el-button type="primary" @click="showTaskDialog = true">+ Add Task</el-button>
      </div>
    </el-card>
    
    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="description" label="Description" show-overflow-tooltip />
      <el-table-column prop="is_active" label="Active" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? 'Yes' : 'No' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="300">
        <template #default="{ row }">
          <el-button size="small" @click="viewTestCases(row)">Test Cases</el-button>
          <el-button size="small" type="primary" @click="editTask(row)">Edit</el-button>
          <el-button size="small" type="danger" @click="deleteTask(row.id)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- Task Dialog -->
    <el-dialog v-model="showTaskDialog" :title="editingTask ? 'Edit Task' : 'Add Task'" width="70%">
      <el-form :model="taskForm" label-width="150px">
        <el-form-item label="Name" required>
          <el-input v-model="taskForm.name" placeholder="e.g., Phone Call Annotation" />
        </el-form-item>
        
        <el-form-item label="Description">
          <el-input v-model="taskForm.description" type="textarea" rows="3" placeholder="Task description" />
        </el-form-item>
        
        <el-form-item label="Judge Prompt" required>
          <el-input 
            v-model="taskForm.judge_prompt" 
            type="textarea" 
            rows="6" 
            placeholder="Instructions for the judge model on how to evaluate responses"
          />
        </el-form-item>
        
        <el-form-item label="Output Schema (JSON)">
          <el-input 
            v-model="outputSchemaStr" 
            type="textarea" 
            rows="4" 
            placeholder='{"type": "object", "properties": {...}}'
          />
        </el-form-item>
        
        <el-form-item label="Active">
          <el-switch v-model="taskForm.is_active" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showTaskDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveTask" :loading="saving">Save</el-button>
      </template>
    </el-dialog>
    
    <!-- Test Cases Dialog -->
    <el-dialog v-model="showTestCasesDialog" title="Test Cases" width="80%">
      <div v-if="currentTask">
        <h3>{{ currentTask.name }}</h3>
        
        <el-button type="primary" size="small" @click="showTestCaseForm = true" class="mb-2">+ Add Test Case</el-button>
        
        <el-table :data="testCases" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="Name" />
          <el-table-column prop="prompt" label="Prompt" show-overflow-tooltip />
          <el-table-column label="Actions" width="150">
            <template #default="{ row }">
              <el-button size="small" type="danger" @click="deleteTestCase(row.id)">Delete</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- Add Test Case Form -->
        <el-dialog v-model="showTestCaseForm" title="Add Test Case" append-to-body>
          <el-form :model="testCaseForm" label-width="100px">
            <el-form-item label="Name" required>
              <el-input v-model="testCaseForm.name" />
            </el-form-item>
            
            <el-form-item label="Prompt" required>
              <el-input v-model="testCaseForm.prompt" type="textarea" rows="4" />
            </el-form-item>
            
            <el-form-item label="Input Text">
              <el-input v-model="testCaseForm.input_text" type="textarea" rows="3" />
            </el-form-item>
            
            <el-form-item label="Expected Output">
              <el-input v-model="testCaseForm.expected_output" type="textarea" rows="3" />
            </el-form-item>
          </el-form>
          
          <template #footer>
            <el-button @click="showTestCaseForm = false">Cancel</el-button>
            <el-button type="primary" @click="saveTestCase">Save</el-button>
          </template>
        </el-dialog>
      </div>
      
      <template #footer>
        <el-button @click="showTestCasesDialog = false">Close</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tasksApi } from '../api'

const tasks = ref([])
const testCases = ref([])
const loading = ref(false)
const saving = ref(false)
const showTaskDialog = ref(false)
const showTestCasesDialog = ref(false)
const showTestCaseForm = ref(false)
const editingTask = ref(null)
const currentTask = ref(null)

const taskForm = ref({
  name: '',
  description: '',
  judge_prompt: '',
  output_schema: null,
  is_active: true,
})

const outputSchemaStr = ref('')

const testCaseForm = ref({
  name: '',
  prompt: '',
  input_text: '',
  expected_output: '',
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await tasksApi.getAll()
    tasks.value = res.data
  } catch (e) {
    ElMessage.error('Failed to load tasks')
  } finally {
    loading.value = false
  }
}

const editTask = (task) => {
  editingTask.value = task
  taskForm.value = {
    name: task.name,
    description: task.description,
    judge_prompt: task.judge_prompt,
    output_schema: task.output_schema,
    is_active: task.is_active,
  }
  outputSchemaStr.value = task.output_schema ? JSON.stringify(task.output_schema, null, 2) : ''
  showTaskDialog.value = true
}

const saveTask = async () => {
  saving.value = true
  try {
    let outputSchema = null
    if (outputSchemaStr.value.trim()) {
      outputSchema = JSON.parse(outputSchemaStr.value)
    }
    
    const data = { ...taskForm.value, output_schema: outputSchema }
    
    if (editingTask.value) {
      await tasksApi.update(editingTask.value.id, data)
      ElMessage.success('Task updated')
    } else {
      await tasksApi.create(data)
      ElMessage.success('Task created')
    }
    showTaskDialog.value = false
    editingTask.value = null
    loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Invalid JSON schema' || 'Operation failed')
  } finally {
    saving.value = false
  }
}

const deleteTask = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure?', 'Delete Task', { type: 'warning' })
    await tasksApi.delete(id)
    ElMessage.success('Task deleted')
    loadTasks()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Delete failed')
  }
}

const viewTestCases = async (task) => {
  currentTask.value = task
  try {
    const res = await tasksApi.getTestCases(task.id)
    testCases.value = res.data
    showTestCasesDialog.value = true
  } catch (e) {
    ElMessage.error('Failed to load test cases')
  }
}

const saveTestCase = async () => {
  try {
    await tasksApi.createTestCase(currentTask.value.id, testCaseForm.value)
    ElMessage.success('Test case added')
    showTestCaseForm.value = false
    testCaseForm.value = { name: '', prompt: '', input_text: '', expected_output: '' }
    const res = await tasksApi.getTestCases(currentTask.value.id)
    testCases.value = res.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Failed to add test case')
  }
}

const deleteTestCase = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure?', 'Delete Test Case', { type: 'warning' })
    await tasksApi.deleteTestCase(id)
    ElMessage.success('Test case deleted')
    const res = await tasksApi.getTestCases(currentTask.value.id)
    testCases.value = res.data
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Delete failed')
  }
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.mb-4 { margin-bottom: 16px; }
.mb-2 { margin-bottom: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
