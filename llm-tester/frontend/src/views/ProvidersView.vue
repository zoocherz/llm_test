<template>
  <div class="providers-view">
    <h2>Providers Management</h2>
    
    <el-card class="mb-4">
      <div class="card-header">
        <span>Add New Provider</span>
        <el-button type="primary" @click="showAddDialog = true">+ Add Provider</el-button>
      </div>
      
      <el-button type="success" @click="validatePool" :loading="validating">Validate All Providers</el-button>
    </el-card>
    
    <el-table :data="providers" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="provider_type" label="Type" />
      <el-table-column prop="priority" label="Priority" width="80" />
      <el-table-column prop="is_active" label="Active" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? 'Yes' : 'No' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="testProvider(row.id)">Test</el-button>
          <el-button size="small" type="primary" @click="editProvider(row)">Edit</el-button>
          <el-button size="small" type="danger" @click="deleteProvider(row.id)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- Add/Edit Dialog -->
    <el-dialog v-model="showAddDialog" :title="editingProvider ? 'Edit Provider' : 'Add Provider'">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Name" required>
          <el-input v-model="form.name" placeholder="e.g., My Google Provider" />
        </el-form-item>
        
        <el-form-item label="Type" required>
          <el-select v-model="form.provider_type" placeholder="Select type">
            <el-option v-for="type in providerTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key" type="password" placeholder="Your API key" />
        </el-form-item>
        
        <el-form-item label="Base URL (optional)">
          <el-input v-model="form.base_url" placeholder="Custom base URL" />
        </el-form-item>
        
        <el-form-item label="Priority">
          <el-input-number v-model="form.priority" :min="1" :max="100" />
        </el-form-item>
        
        <el-form-item label="Active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveProvider" :loading="saving">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { providersApi } from '../api'

const providers = ref([])
const providerTypes = ref([])
const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const showAddDialog = ref(false)
const editingProvider = ref(null)

const form = ref({
  name: '',
  provider_type: '',
  api_key: '',
  base_url: null,
  priority: 10,
  is_active: true,
})

const loadProviders = async () => {
  loading.value = true
  try {
    const res = await providersApi.getAll()
    providers.value = res.data
  } catch (e) {
    ElMessage.error('Failed to load providers')
  } finally {
    loading.value = false
  }
}

const loadTypes = async () => {
  try {
    const res = await providersApi.getTypes()
    providerTypes.value = res.data
  } catch (e) {
    console.error('Failed to load types')
  }
}

const validatePool = async () => {
  validating.value = true
  try {
    const res = await providersApi.validatePool()
    const validCount = res.data.filter(r => r.is_valid).length
    ElMessage.success(`Validation complete: ${validCount}/${res.data.length} providers working`)
  } catch (e) {
    ElMessage.error('Validation failed')
  } finally {
    validating.value = false
  }
}

const testProvider = async (id) => {
  try {
    const res = await providersApi.test(id)
    if (res.data.is_valid) {
      ElMessage.success('Provider is working!')
    } else {
      ElMessage.warning(`Provider test failed: ${res.data.error}`)
    }
  } catch (e) {
    ElMessage.error('Test failed')
  }
}

const editProvider = (provider) => {
  editingProvider.value = provider
  form.value = {
    name: provider.name,
    provider_type: provider.provider_type,
    api_key: provider.api_key,
    base_url: provider.base_url,
    priority: provider.priority,
    is_active: provider.is_active,
  }
  showAddDialog.value = true
}

const saveProvider = async () => {
  saving.value = true
  try {
    if (editingProvider.value) {
      await providersApi.update(editingProvider.value.id, form.value)
      ElMessage.success('Provider updated')
    } else {
      await providersApi.create(form.value)
      ElMessage.success('Provider created')
    }
    showAddDialog.value = false
    editingProvider.value = null
    loadProviders()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Operation failed')
  } finally {
    saving.value = false
  }
}

const deleteProvider = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure?', 'Delete Provider', { type: 'warning' })
    await providersApi.delete(id)
    ElMessage.success('Provider deleted')
    loadProviders()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('Delete failed')
    }
  }
}

onMounted(() => {
  loadProviders()
  loadTypes()
})
</script>

<style scoped>
.mb-4 {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
