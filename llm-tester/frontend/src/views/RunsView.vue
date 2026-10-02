<template>
  <div class="runs-view">
    <RunResults v-if="run" :key="run.id" :run="run" :items="items" :routes="routes" class="space current-results" @retried="openRunDetails" />
    <el-card class="runs-history">
      <template #header><div class="card-header"><div><b>Запуски</b><div class="hint">История сравнений, сводка по моделям и результаты отдельных примеров.</div></div><el-button :loading="loading" @click="loadRuns">Обновить</el-button></div></template>
      <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <el-input v-model="search" clearable placeholder="Поиск по ID запуска" />
      <el-select v-model="kind" clearable placeholder="Все типы"><el-option value="generation" label="Генерация ответов" /><el-option value="evaluation" label="Оценка судьёй" /><el-option value="legacy" label="Старые запуски" /></el-select>
      <el-select v-model="statusFilter" clearable placeholder="Все статусы"><el-option v-for="status in ['queued','running','cancelling','completed','completed_with_errors','failed','cancelled']" :key="status" :value="status" :label="status" /></el-select>
      <p>{{ filteredRuns.length }} из {{ runs.length }} запусков</p>
      <el-table :data="filteredRuns" max-height="65vh" empty-text="Нет подходящих запусков" class="clickable" highlight-current-row @row-click="selectRun">
        <el-table-column prop="created_at" label="Запуск · сортировка по дате" sortable><template #default="{ row }"><b>{{ (row.kind || row.snapshot_json?.kind) === 'evaluation' ? 'Оценка судьёй' : (row.kind || row.snapshot_json?.kind) === 'generation' ? 'Генерация ответов' : 'Старый запуск' }}</b><RunProgress :run="row" compact /><small>{{ formatDate(row.created_at) }} · {{ shortId(row.id) }}</small></template></el-table-column>
      </el-table>
    </el-card>

  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { evaluationApi } from '../api'
import RunResults from '../components/RunResults.vue'
import RunProgress from '../components/RunProgress.vue'
import { explain } from '../utils/evaluationErrors'
import { useRunDetails } from '../composables/useRunDetails'

const route = useRoute()
const router = useRouter()
const runs = ref([])
const search = ref(''), kind = ref(''), statusFilter = ref('')
const filteredRuns = computed(() => runs.value.filter(row => (!search.value || row.id.toLowerCase().includes(search.value.toLowerCase())) && (!kind.value || (row.kind || row.snapshot_json?.kind || 'legacy') === kind.value) && (!statusFilter.value || row.status === statusFilter.value)))
const routes = ref([])
const error = ref('')
const { run, items, openRunDetails } = useRunDetails({ error, onUpdated: (updated) => {
  runs.value = runs.value.map((item) => item.id === updated.id ? updated : item)
} })
const loading = ref(false)
const shortId = (id) => id ? id.slice(0, 8) : ''
const formatDate = (value) => value ? new Date(value).toLocaleString('ru-RU') : '—'

let historyTimer, disposed = false
async function loadRuns(quiet = false) {
  clearTimeout(historyTimer)
  if (loading.value || disposed) return
  loading.value = true
  if (!quiet) error.value = ''
  try {
    const [runRows, routeRows] = await Promise.all([evaluationApi.listRuns(), evaluationApi.listRoutes()])
    if (disposed) return
    runs.value = runRows.data
    routes.value = routeRows.data
  } catch (cause) {
    if (!quiet && !disposed) error.value = explain(cause, 'Не удалось загрузить историю запусков')
  } finally {
    loading.value = false
    if (!disposed) historyTimer = setTimeout(() => loadRuns(true), 2000)
  }
}

function selectRun(row) {
  if (route.params.runId !== row.id) router.push('/runs/' + row.id)
}



watch(() => route.params.runId, (id) => openRunDetails(id))
onBeforeUnmount(() => { disposed = true; clearTimeout(historyTimer) })
onMounted(async () => {
  await loadRuns()
  if (route.params.runId) await openRunDetails(route.params.runId)
})
</script>

<style scoped>
.runs-view { display: grid; grid-template-columns: 340px minmax(0, 1fr); gap: 16px; margin: 0 auto; align-items: start; }
.current-results { grid-column: 2; grid-row: 1; min-width: 0; margin-top: 0; }
.runs-history { grid-column: 1; grid-row: 1; min-width: 0; position: sticky; top: 12px; }
.runs-history .el-select { width: 100%; margin-top: 8px; }
@media (max-width: 1100px) { .runs-view { display: flex; flex-direction: column; } .current-results, .runs-history { width: 100%; } .runs-history { position: static; } }
.space { margin-top: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.hint { color: var(--el-text-color-secondary); font-weight: normal; margin-top: 4px; }
.clickable :deep(.el-table__row) { cursor: pointer; }
</style>
