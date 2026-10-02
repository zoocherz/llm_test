<template>
    <el-card v-if="run" class="space result-card">
      <template #header><div class="card-header"><span>Run {{ run.id }}</span><span><el-button size="small" :loading="downloading === 'json'" @click="downloadRun('json')">Экспорт JSON</el-button><el-button size="small" :loading="downloading === 'csv'" @click="downloadRun('csv')">Экспорт CSV</el-button></span></div></template>
      <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <div class="space"><el-button v-if="['queued', 'running', 'cancelling'].includes(run.status)" type="danger" plain :disabled="run.status === 'cancelling'" :loading="cancelling" @click="cancelRequested = true">Отменить запуск</el-button><span v-if="run.status === 'cancelling'"> Отмена запрошена: ожидаем окончания текущего запроса, новые не начинаются.</span></div>
      <el-alert v-if="cancelRequested" type="warning" :closable="false"><p>Полученные результаты сохранятся. Уже отправленный запрос может завершиться и быть оплачен провайдером.</p><el-button type="danger" :loading="cancelling" @click="cancelCurrent">Подтвердить отмену запуска</el-button><el-button @click="cancelRequested = false">Продолжить запуск</el-button></el-alert>
      <RunProgress :run="run" :active-label="activeItemLabel" class="sticky-progress" />
      <el-descriptions :column="3" border>
        <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <el-descriptions-item label="Статус">{{ run.status }}</el-descriptions-item>
      <el-descriptions-item label="Тип">{{ run.snapshot_json?.kind === 'evaluation' ? 'Оценка судьёй' : run.snapshot_json?.kind === 'generation' ? 'Генерация ответов' : 'Старый запуск' }}</el-descriptions-item>
        <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <el-descriptions-item label="Готово">{{ run.progress_json?.completed }} / {{ run.progress_json?.total }}</el-descriptions-item>
        <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <el-descriptions-item label="Ошибки">{{ run.progress_json?.failed || 0 }}</el-descriptions-item>
      </el-descriptions>

      <h3 class="space">Сводка по моделям</h3>
      <el-alert v-if="!run.snapshot_json?.kind" title="Числовые оценки старого запуска — техническая заглушка, не оценка качества LLM-судьёй." type="warning" :closable="false" show-icon class="space" />
      <el-alert v-if="run.snapshot_json?.kind === 'generation'" title="Ответы получены без оценки качества. Оценку можно запустить отдельно ниже." type="info" :closable="false" />
      <div v-if="run.snapshot_json?.kind === 'evaluation'" class="space">
        <p>Отдельная оценка · Судья: {{ run.snapshot_json.judge.route.provider_name }} / {{ run.snapshot_json.judge.route.model_identifier }}</p>
        <router-link :to="'/runs/' + run.snapshot_json.source_run_id">Открыть исходные ответы</router-link>
        <el-alert v-if="run.snapshot_json.judge.route.provider_name === 'offline'" title="Offline-оценки — тестовые, не отражают качество ответов." type="warning" :closable="false" />
      </div>
      <el-table :data="runSummary" empty-text="Результаты ещё не получены">
        <el-table-column prop="model" label="Модель" min-width="220" />
        <el-table-column label="Успешно" width="120"><template #default="{ row }">{{ row.completed }} / {{ row.total }}</template></el-table-column>
        <el-table-column prop="failed" label="Ошибки" width="100" />
        <el-table-column v-if="run.snapshot_json?.suite?.scoring_mode !== 'independent'" label="Средняя оценка" width="150"><template #default="{ row }">{{ formatNumber(row.averageScore, 2) }}</template></el-table-column>
        <el-table-column v-for="criterion in run.snapshot_json?.kind === 'evaluation' ? (run.snapshot_json?.suite?.criteria || []) : []" :key="criterion.key" :label="'Среднее: ' + criterion.key" min-width="150"><template #default="{ row }">{{ criterionAverage(row.routeId, criterion.key) }}</template></el-table-column>
        <el-table-column label="Среднее время" width="150"><template #default="{ row }">{{ row.averageLatency === null ? '—' : Math.round(row.averageLatency) + ' мс' }}</template></el-table-column>
        <el-table-column label="Токены" width="110"><template #default="{ row }">{{ row.totalTokens || '—' }}</template></el-table-column>
        <el-table-column label="Стоимость" width="120"><template #default="{ row }">{{ formatNumber(row.totalCost, 6) }}</template></el-table-column>
      </el-table>

      <h3 class="space">Отдельные примеры</h3>
      <p>Повтор выполняется в этом запуске с исходными настройками. Старые ответы и оценки сохранены в истории попыток.</p>
      <div class="retry-actions">
        <p v-if="!canRetry">{{ ['queued', 'running', 'cancelling'].includes(run.status) ? 'Повтор станет доступен после завершения или отмены запуска.' : 'Для старого запуска без полного снимка настроек повтор недоступен.' }}</p>
        <el-button :disabled="!canRetry || !selectedIds.length || retrying" @click="prepareRetry(selectedIds)">Повторить выбранные</el-button>
        <el-button :disabled="!canRetry || !failedIds.length || retrying" @click="prepareRetry(failedIds)">Повторить все с ошибкой</el-button>
        <el-button :disabled="!canRetry || !missingIds.length || retrying" @click="prepareRetry(missingIds)">Повторить все без результата</el-button>
        <p v-if="retryIds.length">Будет выполнено {{ retryIds.length }} вызовов. <el-button type="primary" :loading="retrying" @click="retrySelected">Подтвердить повтор</el-button><el-button @click="retryIds = []">Отмена</el-button></p>
        <el-alert v-if="retryError" :title="retryError" type="error" :closable="false" />
      </div>
      <div class="table-tools"><el-input v-model="itemSearch" clearable placeholder="Поиск примера или текста" /><el-select v-model="itemStatus" clearable placeholder="Любой статус"><el-option v-for="status in ['completed', 'failed', 'running', 'queued', 'cancelled']" :key="status" :value="status" :label="status" /></el-select><span>{{ filteredItems.length }} из {{ items.length }}</span></div>
      <el-alert v-if="run.snapshot_json?.suite?.scoring_mode === 'independent' && run.snapshot_json?.kind === 'evaluation'" title="Каждый критерий — отдельная колонка со своей шкалой. «—» означает отсутствие валидной оценки, не ноль. Средние учитывают только успешные оценки." type="info" :closable="false" />
      <el-table :data="filteredItems" max-height="460" row-key="id" empty-text="Нет подходящих записей" @selection-change="rows => selectedIds = rows.map(row => row.id)">
        <el-table-column type="selection" :reserve-selection="true" :selectable="() => canRetry" width="45" fixed />
        <el-table-column label="Действия" width="185" fixed><template #default="{ row }"><el-button link @click="detailId = row.id">Открыть</el-button><el-button link :disabled="!canRetry || retrying" @click="prepareRetry([row.id])">Повторить</el-button></template></el-table-column>
        <el-table-column prop="status" label="Статус" width="180" sortable fixed><template #default="{ row }"><span v-if="row.status === 'running'" class="row-spinner" aria-hidden="true"></span><span v-else aria-hidden="true">{{ row.status === 'completed' ? '✓' : row.status === 'failed' ? '⚠' : row.status === 'cancelled' ? '■' : '◷' }}</span> {{ itemStatusLabels[row.status] || row.status }}<div v-if="row.status === 'running'">Попытка {{ row.attempts?.at(-1)?.route_snapshot_json?.sequence || row.attempts?.length || 1 }} · HTTP {{ row.attempts?.at(-1)?.route_snapshot_json?.http_attempts || 0 }}</div></template></el-table-column>
        <el-table-column v-for="criterion in run.snapshot_json?.kind === 'evaluation' ? (run.snapshot_json?.suite?.criteria || []) : []" :key="criterion.key" :label="criterion.key + ' (' + (criterion.min_score ?? 0) + '–' + (criterion.max_score ?? 1) + ')'" min-width="150"><template #default="{ row }">{{ row.results?.[0]?.value_json?.scores?.[criterion.key] ?? '—' }}</template></el-table-column>
        <el-table-column label="Пример" width="150"><template #default="{ row }">{{ row.dataset_item?.external_id || shortId(row.dataset_item_id) }}</template></el-table-column>
        <el-table-column label="Модель" min-width="210"><template #default="{ row }">{{ routeLabel(row.route_id) }}</template></el-table-column>
        <el-table-column label="Результат" min-width="260"><template #default="{ row }"><div class="result-preview">{{ itemResultText(row) }}</div></template></el-table-column>
        <el-table-column v-if="run.snapshot_json?.suite?.scoring_mode !== 'independent'" label="Оценка" width="100"><template #default="{ row }">{{ row.results?.[0]?.numeric_score ?? '—' }}</template></el-table-column>
        <el-table-column label="История" width="140"><template #default="{ row }"><el-popover trigger="click" width="600"><template #reference><el-button link>Попытки: {{ row.attempts?.length || 0 }}</el-button></template><div style="max-height: 400px; overflow: auto"><div v-for="(attempt, index) in row.attempts" :key="attempt.id"><b>Попытка {{ index + 1 }} · {{ attempt.error_json ? 'ошибка' : attempt.latency_ms == null ? 'выполняется' : 'ответ' }} · HTTP {{ attempt.route_snapshot_json?.http_attempts ?? '—' }}</b><pre style="white-space: pre-wrap">{{ prettyJson(attempt.output_json || attempt.error_json) }}</pre></div><b>История оценок</b><pre style="white-space: pre-wrap">{{ prettyJson(row.result_history) }}</pre></div></el-popover></template></el-table-column>
        <el-table-column label="Время" width="120"><template #default="{ row }">{{ itemLatency(row) ? itemLatency(row) + ' мс' : '—' }}</template></el-table-column>
      </el-table>
      <el-drawer :model-value="Boolean(detailId)" title="Подробности записи" size="min(780px, 100vw)" @close="detailId = ''"><template v-if="detailItem"><el-button :disabled="!canRetry" @click="prepareRetry([detailId]); detailId = ''">Повторить эту запись</el-button><h3>Ответ / ошибка</h3><pre class="answer-text">{{ itemResultText(detailItem) }}</pre><p v-if="detailItem.output_json?.raw_text || (detailItem.display_text != null && detailItem.display_text !== detailItem.output_json?.text)">Служебная разметка отделена. Исходный ответ сохранён ниже.</p><el-collapse><el-collapse-item title="Исходный ответ и технические данные"><pre>{{ detailItem.output_json?.raw_text || detailItem.output_json?.text || detailItem.error_json?.message }}</pre><pre>{{ prettyJson(detailItem.output_json || detailItem.error_json) }}</pre></el-collapse-item></el-collapse><h3>Вход и эталон</h3><pre>{{ prettyJson(detailItem.dataset_item) }}</pre><h3>Оценки по критериям</h3><pre>{{ prettyJson(detailItem.results) }}</pre><h3>Предыдущие попытки</h3><pre>{{ prettyJson({ attempts: detailItem.attempts, evaluations: detailItem.result_history }) }}</pre></template></el-drawer>
      <RunEvaluationPanel v-if="run.snapshot_json?.kind !== 'evaluation'" :run="run" :items="items" />
      <el-collapse class="space"><el-collapse-item title="Снимок конфигурации Run"><pre>{{ prettyJson(run.snapshot_json) }}</pre></el-collapse-item></el-collapse>
    </el-card>
</template>
<script setup>
import { computed, ref, toRefs } from 'vue'
import { evaluationApi } from '../api'
import RunEvaluationPanel from './RunEvaluationPanel.vue'
import RunProgress from './RunProgress.vue'
import { explain, providerErrorMessages } from '../utils/evaluationErrors'
const props = defineProps({ run: { type: Object, required: true }, items: { type: Array, default: () => [] }, routes: { type: Array, default: () => [] } })
const emit = defineEmits(['retried'])
const { run, items, routes } = toRefs(props)
const downloading = ref(''), error = ref('')
const itemStatusLabels = { running: 'Выполняется', queued: 'В очереди', completed: 'Готово', failed: 'Ошибка', cancelled: 'Отменено' }
const activeItemLabel = computed(() => { const row = items.value.find(item => item.id === run.value.progress_json?.active_item_id); return row ? (row.dataset_item?.external_id || shortId(row.id)) + ' · ' + routeLabel(row.route_id) : '' })
const cancelling = ref(false), cancelRequested = ref(false), detailId = ref(''), itemSearch = ref(''), itemStatus = ref('')
const detailItem = computed(() => items.value.find(row => row.id === detailId.value))
const filteredItems = computed(() => items.value.filter(row => (!itemStatus.value || row.status === itemStatus.value) && (!itemSearch.value || [row.dataset_item?.external_id, row.output_json?.text, row.error_json?.message].join(' ').toLowerCase().includes(itemSearch.value.toLowerCase()))))
async function cancelCurrent() {
  cancelling.value = true; error.value = ''
  try { await evaluationApi.cancelRun(run.value.id); cancelRequested.value = false; emit('retried', run.value.id) }
  catch (cause) { error.value = explain(cause, 'Не удалось отменить запуск') }
  finally { cancelling.value = false }
}
const selectedIds = ref([]), retryIds = ref([]), retrying = ref(false), retryError = ref('')
const canRetry = computed(() => ['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(run.value.status) && ['generation', 'evaluation'].includes(run.value.snapshot_json?.kind))
const failedIds = computed(() => items.value.filter(row => row.status === 'failed').map(row => row.id))
const missingIds = computed(() => items.value.filter(row => !row.output_json?.text?.trim()).map(row => row.id))
function prepareRetry(ids) { retryIds.value = [...ids]; retryError.value = '' }
async function retrySelected() {
  retrying.value = true; retryError.value = ''
  try { await evaluationApi.retryRun(run.value.id, retryIds.value); retryIds.value = []; selectedIds.value = []; emit('retried', run.value.id) }
  catch (cause) { retryError.value = explain(cause, 'Не удалось повторить записи') }
  finally { retrying.value = false }
}
const shortId = (id) => id ? id.slice(0, 8) : ''

const itemLatency = (row) => (row.attempts || []).reduce((sum, attempt) => sum + Number(attempt.latency_ms || 0), 0)
const prettyJson = (value) => value == null ? '—' : JSON.stringify(value, null, 2)
const formatNumber = (value, digits) => value == null ? '—' : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: digits })
function criterionAverage(routeId, key) {
  const values = items.value.filter(row => row.route_id === routeId).map(row => row.results?.[0]?.value_json?.scores?.[key]).filter(Number.isFinite)
  return values.length ? formatNumber(values.reduce((a, b) => a + b, 0) / values.length, 2) : '—'
}

function routeLabel(routeId) {
  const value = run.value?.snapshot_json?.routes?.find((item) => item.id === routeId) || routes.value.find((item) => item.id === routeId)
  return value ? value.provider_name + ' / ' + value.model_identifier : shortId(routeId)
}

function itemResultText(row) {
  if (row.error_json?.code === 'invalid_judge_response') return row.error_json.message || providerErrorMessages.invalid_judge_response
  if (row.display_text != null) return row.display_text.trim() ? row.display_text : 'Финальный текст отсутствует: получены только служебные блоки. Исходный ответ сохранён.'
  if (row.output_json?.text?.trim()) return row.output_json.text
  if (row.status === 'queued') return 'Ожидает обработки'
  if (row.status === 'running') return 'Обрабатывается'
  if (row.error_json?.code === 'timeout' && row.error_json.message?.includes('snapshot')) return row.error_json.message
  const providerMessage = providerErrorMessages[row.error_json?.code]
  if (providerMessage) return providerMessage
  if (row.error_json?.code?.startsWith('http_')) return 'Провайдер отклонил запрос (' + row.error_json.code.replace('_', ' ').toUpperCase() + ').'
  return row.error_json?.message || (row.status === 'completed' ? 'Пустой текстовый ответ — полезный результат не получен. Можно повторить запись.' : 'Ответ не получен')
}

const runSummary = computed(() => {
  const grouped = new Map()
  for (const item of items.value) {
    if (!grouped.has(item.route_id)) grouped.set(item.route_id, { routeId: item.route_id, total: 0, completed: 0, failed: 0, scores: [], latencies: [], totalTokens: 0, totalCost: 0, hasCost: false })
    const row = grouped.get(item.route_id)
    row.total += 1
    if (item.status === 'completed') row.completed += 1
    if (item.status === 'failed') row.failed += 1
    for (const result of item.results || []) if (Number.isFinite(result.numeric_score)) row.scores.push(result.numeric_score)
    const latency = itemLatency(item)
    if (latency) row.latencies.push(latency)
    row.totalTokens += Number(item.output_json?.usage?.total || 0)
    const rawCost = item.output_json?.usage?.cost
    const cost = Number(rawCost)
    if (rawCost != null && rawCost !== '' && Number.isFinite(cost)) { row.totalCost += cost; row.hasCost = true }
  }
  return [...grouped.values()].map((row) => ({
    ...row,
    model: routeLabel(row.routeId),
    averageScore: row.scores.length ? row.scores.reduce((sum, value) => sum + value, 0) / row.scores.length : null,
    averageLatency: row.latencies.length ? row.latencies.reduce((sum, value) => sum + value, 0) / row.latencies.length : null,
    totalCost: row.hasCost ? row.totalCost : null,
  }))
})

async function downloadRun(format) {
  downloading.value = format
  error.value = ''
  try {
    const response = await evaluationApi.exportRun(run.value.id, format)
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'run-' + run.value.id + '.' + format
    link.click()
    URL.revokeObjectURL(url)
  } catch (cause) {
    error.value = explain(cause, 'Не удалось экспортировать Run')
  } finally {
    downloading.value = ''
  }
}

</script>
<style scoped>
.result-card { overflow: visible; }
.sticky-progress { position: sticky; top: 8px; z-index: 5; margin: 12px 0; box-shadow: 0 2px 10px #0001; }
.row-spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--el-border-color); border-top-color: var(--el-color-primary); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .row-spinner { animation: none; } }

.result-preview { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.table-tools { display: flex; gap: 10px; margin: 12px 0; }
.table-tools .el-input { max-width: 320px; }
.table-tools .el-select { width: 180px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
.space { margin-top: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.item-detail { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: 8px 32px; }
.item-detail pre, .el-collapse pre { white-space: pre-wrap; word-break: break-word; }
@media (max-width: 760px) { .item-detail { grid-template-columns: 1fr; } }
</style>
