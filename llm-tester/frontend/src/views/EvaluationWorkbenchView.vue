<template>
  <div class="workbench">
    <el-card>
      <template #header><b>{{ experimentMode ? 'Эксперименты' : 'Главная' }}</b></template>
      <p>Быстро сравните сохранённые модели или перейдите к отдельным разделам для подготовки данных и подключений.</p>
      <div class="section-links"><el-button @click="$router.push('/datasets')">Перейти в «Датасеты»</el-button><el-button @click="$router.push('/models')">Перейти в «Модели»</el-button><el-button @click="$router.push('/runs')">Перейти в «Запуски»</el-button></div>
      <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
    </el-card>
    <el-card v-if="!experimentMode" class="space quick-run-card">
      <template #header><b>Быстрый запуск</b></template>
      <p class="hint">Вставьте примеры, выберите сохранённые модели и запустите сравнение. Подробные технические настройки будут созданы автоматически и сохранятся в снимке запуска.</p>
      <el-form label-position="top" class="quick-run-form">
        <el-form-item label="Тексты для проверки"><el-input v-model="quickForm.texts" type="textarea" :rows="4" placeholder="Один пример на строку" /><span class="field-help">Каждая непустая строка станет отдельным примером.</span></el-form-item>
        <el-form-item label="Модели для сравнения"><el-select v-model="quickForm.routeIds" multiple filterable collapse-tags placeholder="Выберите одну или несколько моделей"><el-option v-for="item in routes" :key="item.id" :value="item.id" :label="item.provider_name + ' / ' + item.model_identifier" :disabled="!item.credential_available" /></el-select></el-form-item>
        <el-alert v-if="!routes.length" title="Сначала сохраните хотя бы одну модель в разделе «Модели»." type="info" :closable="false" />
        <el-alert v-else :title="'Примеров: ' + quickRows.length + ' · моделей: ' + quickForm.routeIds.length + ' · модельных вызовов: ' + quickCandidateCalls" type="info" :closable="false" />
        <el-alert v-if="quickError" :title="quickError" type="error" :closable="false" class="space" />
        <el-form-item class="space"><el-button type="success" :disabled="!quickReady" :loading="creatingQuick" @click="createQuickRun">Запустить сравнение</el-button></el-form-item>
      </el-form>
      <el-alert v-if="quickMessage" :title="quickMessage" type="success" show-icon :closable="false" />
    </el-card>
    <el-radio-group v-if="experimentMode" v-model="experimentTab" class="space"><el-radio-button value="launch">Запуск</el-radio-button><el-radio-button value="settings">Настройки</el-radio-button></el-radio-group>
    <ExperimentConfiguration v-if="experimentMode" v-show="experimentTab === 'settings'" @created="configurationSelected" />
    <el-card v-if="experimentMode" v-show="experimentTab === 'launch'" class="space"><template #header><div class="card-header"><b>Подробная проверка и запуск</b><el-button link :loading="loadingDefinitions" @click="loadDefinitions">Обновить список</el-button></div></template>
      <el-alert v-if="!hasDefinitions" title="Используйте быстрый запуск или заполните подробные шаги выше: здесь появятся сохранённые настройки." type="info" :closable="false" />
      <el-form label-position="top" class="run-form">
        <el-form-item label="Данные"><el-select v-model="form.datasetVersionId" placeholder="Выберите DatasetVersion" filterable><el-option v-for="item in publishedDatasetVersions" :key="item.id" :value="item.id" :label="item.dataset_name + ' · v' + item.version_number" /></el-select></el-form-item>
        <el-form-item label="Инструкция (PromptVersion)"><el-select v-model="form.promptVersionId" placeholder="Выберите prompt" filterable><el-option v-for="item in prompts" :key="item.id" :value="item.id" :label="item.name + ' · ' + item.id.slice(0, 8)" /></el-select></el-form-item>
        <el-form-item label="Схема обработки (PipelineVersion)"><el-select v-model="form.pipelineVersionId" placeholder="Выберите pipeline" filterable><el-option v-for="item in pipelines" :key="item.id" :value="item.id" :label="item.name + ' · ' + item.id.slice(0, 8)" /></el-select></el-form-item>
        <el-form-item label="Модели для сравнения"><el-select v-model="form.routeIds" multiple collapse-tags placeholder="Выберите один или несколько маршрутов" filterable><el-option v-for="item in routes" :key="item.id" :value="item.id" :label="item.provider_name + ' / ' + item.model_identifier" /></el-select></el-form-item>
        <el-form-item label="Режим"><el-radio-group v-model="form.policy.mode"><el-radio value="benchmark">Сравнение</el-radio><el-radio value="availability">Доступность</el-radio></el-radio-group></el-form-item>
        <div class="run-actions">
          <el-form-item label="Лимит токенов ответа"><el-input-number v-model="form.policy.max_output_tokens" :min="128" :max="65536" :step="1024" /><span>Больший лимит может увеличить время и стоимость.</span></el-form-item>
          <p v-if="!readyToRun">Выберите датасет, инструкцию, схему обработки и хотя бы одну модель.</p>
          <el-alert v-if="actionError" :title="actionError" type="error" :closable="false" show-icon class="space action-error" />
          <el-button :disabled="!form.datasetVersionId || !form.promptVersionId" :loading="previewingPrompt" @click="previewInstruction">Показать инструкцию для первой строки</el-button>
          <el-button :disabled="!readyToRun" :loading="estimating" @click="estimate">Оценить объём</el-button>
          <el-button type="success" :disabled="!readyToRun" :loading="launching" @click="launchSaved">Запустить выбранную конфигурацию</el-button>
          <div v-if="promptPreview" class="space"><el-button link @click="previewHidden = !previewHidden">{{ previewHidden ? 'Показать сохранённую инструкцию' : 'Скрыть инструкцию' }}</el-button><div v-show="!previewHidden"><b>Инструкция для первой строки · {{ promptPreview.externalId }}</b><p>Без вызова модели. Проверка всего датасета выполняется при оценке объёма и запуске.</p><pre>{{ promptPreview.rendered }}</pre></div></div>
        </div>
      </el-form>
      <el-alert v-if="estimateResult" :title="'Будет выполнено: ' + estimateResult.total_calls + ' вызовов (' + estimateResult.candidate_calls + ' кандидатов, ' + estimateResult.judge_calls + ' оценок).'" type="success" :closable="false" />
    </el-card>
    <div ref="resultAnchor" class="current-results"><RunResults v-if="run" :key="run.id" :run="run" :items="items" :routes="routes" class="space" @retried="showRun" /></div>
    <el-card class="space">
      <template #header><div class="card-header"><b>Последние запуски</b><el-button link @click="$router.push('/runs')">Вся история, поиск и фильтры</el-button></div></template>
      <el-table :data="runs.slice(0, 5)" max-height="240" empty-text="Запусков пока нет" @row-click="openRun" class="clickable">
        <el-table-column label="Тип" min-width="190"><template #default="{ row }">{{ row.kind === 'evaluation' ? 'Оценка судьёй' : row.kind === 'generation' ? 'Генерация ответов' : 'Старый запуск' }}</template></el-table-column>
        <el-table-column prop="status" label="Статус" width="180" />
        <el-table-column label="Готово" width="150"><template #default="{ row }">{{ row.progress_json?.completed || 0 }} / {{ row.progress_json?.total || 0 }}</template></el-table-column>
        <el-table-column label="Создан" width="210"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="Идентификатор"><template #default="{ row }">{{ shortId(row.id) }}</template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ExperimentConfiguration from '../components/ExperimentConfiguration.vue'
import { evaluationApi } from '../api'
import RunResults from '../components/RunResults.vue'
import { explain } from '../utils/evaluationErrors'
import { useRunDetails } from '../composables/useRunDetails'
const props = defineProps({ experimentMode: { type: Boolean, default: false } })
const route = useRoute(), router = useRouter()
const experimentTab = computed({ get: () => route.query.view === 'settings' ? 'settings' : 'launch', set: value => router.replace({ query: { ...route.query, view: value } }) })
const launching = ref(false), estimating = ref(false), loadingDefinitions = ref(false)

const error = ref(''), estimateResult = ref(null)
const actionError = ref(''), quickError = ref(''), promptPreview = ref(null), previewingPrompt = ref(false)
const previewHidden = ref(false)
let formRevision = 0
const { run, items, openRunDetails, stopRunUpdates } = useRunDetails({ error, onUpdated: loadRuns })
const datasetVersions = ref([]), prompts = ref([]), pipelines = ref([]), routes = ref([]), suites = ref([]), runs = ref([])

const quickForm = reactive({ texts: '', routeIds: [] })
const creatingQuick = ref(false), quickMessage = ref('')

const form = reactive({ datasetVersionId: '', promptVersionId: '', pipelineVersionId: '', routeIds: [], suiteVersionId: '', policy: { mode: 'benchmark', concurrency: 3, request_timeout_seconds: 60, fallback_enabled: false } })
try {
  const saved = JSON.parse(sessionStorage.getItem('experiment-selection') || 'null')
  if (saved && typeof saved === 'object') Object.assign(form, saved)
} catch { /* Invalid saved selection starts with the default form. */ }
form.policy.max_output_tokens ??= 4096
watch(form, (value) => { sessionStorage.setItem('experiment-selection', JSON.stringify(value)); estimateResult.value = null; actionError.value = ''; promptPreview.value = null; formRevision += 1 }, { deep: true })
const publishedDatasetVersions = computed(() => datasetVersions.value.filter((item) => item.status === 'published'))
const hasDefinitions = computed(() => publishedDatasetVersions.value.length || prompts.value.length || pipelines.value.length || routes.value.length || suites.value.length)
const readyToRun = computed(() => Boolean(form.datasetVersionId && form.promptVersionId && form.pipelineVersionId && form.routeIds.length))

const quickRows = computed(() => quickForm.texts.split(/\r?\n/).map((text) => text.trim()).filter(Boolean))
const quickCandidateCalls = computed(() => quickRows.value.length * quickForm.routeIds.length)
const quickReady = computed(() => quickRows.value.length > 0 && quickForm.routeIds.length > 0 && !creatingQuick.value)

const requestPayload = () => ({ dataset_version_id: form.datasetVersionId, prompt_version_ids: [form.promptVersionId], candidate_route_ids: form.routeIds, pipeline_version_id: form.pipelineVersionId, policy: form.policy })
const shortId = (id) => id ? id.slice(0, 8) : ''

async function loadDefinitions() {
  loadingDefinitions.value = true
  try {
    const [versions, promptRows, pipelineRows, routeRows, suiteRows] = await Promise.all([evaluationApi.listDatasetVersions(), evaluationApi.listPrompts(), evaluationApi.listPipelines(), evaluationApi.listRoutes(), evaluationApi.listSuites()])
    datasetVersions.value = versions.data; prompts.value = promptRows.data; pipelines.value = pipelineRows.data; routes.value = routeRows.data; suites.value = suiteRows.data

  } catch (cause) { error.value = explain(cause, 'Не удалось загрузить сохранённые конфигурации') } finally { loadingDefinitions.value = false }
  await loadRuns()
}
async function loadRuns() {
  try { runs.value = (await evaluationApi.listRuns()).data } catch (cause) { error.value = explain(cause, 'Не удалось загрузить историю запусков') }
}
const resultAnchor = ref(null)
async function showRun(id) { if (props.experimentMode) { await router.push('/runs/' + id); return } await openRunDetails(id); await nextTick(); resultAnchor.value?.scrollIntoView({ block: 'start', behavior: 'smooth' }) }
async function openRun(row) { await showRun(row.id) }

const formatDate = (value) => value ? new Date(value).toLocaleString('ru-RU') : '—'

async function configurationSelected(selection) {
  Object.assign(form, selection)
  await loadDefinitions()
}
async function ensureQuickConfiguration() {
  let prompt = prompts.value.find((item) => item.name === 'quick-run-default-prompt' && item.template === '{{text}}')
  let pipeline = pipelines.value.find((item) => item.name === 'quick-run-default-pipeline')
  if (!prompt) prompt = (await evaluationApi.createPrompt({ name: 'quick-run-default-prompt', template: '{{text}}' })).data
  if (!pipeline) pipeline = (await evaluationApi.createPipeline({ name: 'quick-run-default-pipeline', definition: { nodes: [{ id: 'generate', kind: 'generate' }], edges: [] } })).data
  return { prompt, pipeline }
}
async function createQuickRun() {
  creatingQuick.value = true; quickError.value = ''; quickMessage.value = ''; estimateResult.value = null; stopRunUpdates()
  try {
    const stamp = Date.now()
    const dataset = (await evaluationApi.createDataset({ name: 'quick-run-' + stamp, description: 'Created by quick comparison', schema: { modalities: ['text'] } })).data
    const rows = quickRows.value.map((text, index) => ({ external_id: 'quick-' + (index + 1), input: { text }, metadata: { source: 'quick-run' } }))
    await evaluationApi.commitItems(dataset.draft_version_id, rows)
    await evaluationApi.publishDataset(dataset.draft_version_id)
    const { prompt, pipeline } = await ensureQuickConfiguration()
    const payload = {
      dataset_version_id: dataset.draft_version_id,
      prompt_version_ids: [prompt.id],
      candidate_route_ids: [...quickForm.routeIds],
      pipeline_version_id: pipeline.id,
      judge_enabled: false,
      policy: { mode: 'benchmark', concurrency: 3, request_timeout_seconds: 60, fallback_enabled: false },
    }
    run.value = (await evaluationApi.createRun(payload)).data
    Object.assign(form, { datasetVersionId: dataset.draft_version_id, promptVersionId: prompt.id, pipelineVersionId: pipeline.id, routeIds: [...quickForm.routeIds] })
    quickMessage.value = 'Запуск создан: ' + rows.length + ' примеров × ' + quickForm.routeIds.length + ' моделей. Результаты появятся в истории ниже.'
    await loadDefinitions(); await showRun(run.value.id)
  } catch (cause) { quickError.value = explain(cause, 'Не удалось выполнить быстрый запуск') } finally { creatingQuick.value = false }
}

async function estimate() {
  estimating.value = true; actionError.value = ''; estimateResult.value = null
  try { const payload = requestPayload(); delete payload.pipeline_version_id; delete payload.suite_version_id; estimateResult.value = (await evaluationApi.estimateRun(payload)).data }
  catch (cause) { actionError.value = explain(cause, 'Не удалось оценить объём запуска') } finally { estimating.value = false }
}
async function launchSaved() {
  launching.value = true; actionError.value = ''; stopRunUpdates()
  try { run.value = (await evaluationApi.createRun(requestPayload())).data; estimateResult.value = null; await showRun(run.value.id) }
  catch (cause) { actionError.value = explain(cause, 'Не удалось запустить выбранную конфигурацию') } finally { launching.value = false }
}
async function previewInstruction() {
  previewHidden.value = false
  const revision = formRevision
  previewingPrompt.value = true; actionError.value = ''; promptPreview.value = null
  try {
    const prompt = prompts.value.find((item) => item.id === form.promptVersionId)
    if (!prompt) throw new Error('Выберите сохранённую инструкцию.')
    const response = await evaluationApi.listDatasetItems(form.datasetVersionId, { limit: 1, offset: 0 })
    const row = response.data.items?.[0]
    if (!row) throw new Error('В выбранном датасете нет строк.')
    const preview = await evaluationApi.previewPrompt({ template: prompt.template, input: row.input_json })
    if (revision === formRevision) promptPreview.value = { rendered: preview.data.rendered, externalId: row.external_id }
  } catch (cause) { if (revision === formRevision) actionError.value = explain(cause, 'Не удалось проверить инструкцию') }
  finally { previewingPrompt.value = false }
}
onMounted(loadDefinitions)
</script>
<style scoped>
.run-actions { grid-column: 1 / -1; }
.run-actions pre { white-space: pre-wrap; overflow-wrap: anywhere; }
.action-error { margin-bottom: 12px; }
.workbench { max-width: 1100px; margin: 0 auto; }
.space { margin-top: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.hint { color: var(--el-text-color-secondary); margin-top: 0; }
.quick-run-form { max-width: 760px; }
.quick-run-form :deep(.el-select) { width: 100%; }
.field-help { color: var(--el-text-color-secondary); font-size: 12px; margin-left: 8px; }

.run-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; margin-top: 16px; }
.run-form :deep(.el-select) { width: 100%; }
@media (max-width: 760px) { .run-form { grid-template-columns: 1fr; } }
</style>
