<template>
  <div class="datasets-view">
    <el-card>
      <template #header><div><b>Датасеты</b><div class="hint">Импортируйте и публикуйте версионированные данные для экспериментов.</div></div></template>
      <div v-if="revisionContext" class="revision-banner">
        <div><b>Новая версия «{{ revisionContext.datasetName }}»</b><div class="field-help">Будет создана полная версия v{{ revisionContext.versionNumber }}. Опубликованные версии не изменятся.</div></div>
        <el-button @click="cancelRevision">Отменить</el-button>
      </div>
      <el-alert v-if="error" :title="error" type="error" show-icon class="space" :closable="false" />
      <el-form label-position="top" class="dataset-form">
        <el-form-item label="Название"><el-input v-model="form.name" :disabled="Boolean(revisionContext)" placeholder="Например, support-answers" /></el-form-item>
        <el-form-item label="Источник">
          <el-radio-group v-model="form.source" @change="changeSource">
            <el-radio value="json">JSON-массив</el-radio>
            <el-radio value="jsonl">JSONL-текст</el-radio>
            <el-radio value="file">Файл CSV / JSONL</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.source !== 'file'" :label="form.source === 'jsonl' ? 'Строки JSONL' : 'JSON-массив'">
          <el-input v-model="form.rowsText" type="textarea" :rows="8" :placeholder="textPlaceholder" @input="resetPreview" />
          <span class="field-help">{{ form.source === 'jsonl' ? 'Один полный JSON-объект в строке, без запятых и внешних квадратных скобок.' : 'Объекты разделяются запятыми и заключаются в [ ].' }}</span>
        </el-form-item>
        <el-form-item v-else label="Файл импорта">
          <input :key="fileInputKey" type="file" accept=".csv,.jsonl" @change="selectFile" />
          <span class="field-help">Поддерживаются UTF-8, UTF-16 с BOM и Windows-1251. Для CSV распознаются разделители: запятая, точка с запятой, табуляция и |. Максимальный размер — 5 MiB.</span>
        </el-form-item>
        <el-alert type="info" :closable="false" class="canonical-help">
          <template #title>Каноническая строка: <code>{"external_id":"1","input":{"text":"..."}}</code></template>
          Поля <code>external_id</code> и объект <code>input</code> обязательны. Неизвестные поля вроде <code>id</code> или <code>transcript</code> автоматически не переименовываются.
        </el-alert>
        <el-form-item class="space"><el-button :loading="previewing" @click="preview">Проверить строки</el-button><el-button type="primary" :disabled="!canSave" :loading="saving" @click="save">{{ revisionContext ? 'Опубликовать новую версию' : 'Сохранить и опубликовать' }}</el-button></el-form-item>
      </el-form>
      <el-alert v-if="previewResult" :title="previewTitle" :type="previewResult.invalid_count ? 'warning' : 'success'" :closable="false" />
      <div v-if="form.source === 'file' && previewResult" class="detected-format">
        Распознано: <b>{{ previewResult.source_encoding }}</b><template v-if="previewResult.source_format === 'csv'">, разделитель <b>{{ formatDelimiter(previewResult.source_delimiter) }}</b></template>
      </div>
      <div v-if="form.source === 'file' && sourceFields.length" class="mapping-panel space">
        <b>Сопоставление полей файла</b>
        <div class="field-help">Выберите, откуда взять обязательные поля. Преобразование применяется только после нажатия кнопки и сохраняется в версии датасета.</div>
        <div class="source-preview-title">Первые строки исходного файла</div>
        <el-table :data="sourcePreview" size="small" border class="source-preview">
          <el-table-column prop="row" label="Строка" width="80" fixed />
          <el-table-column v-for="field in sourceFields" :key="field" :label="field" min-width="220">
            <template #default="{ row }"><pre class="source-value">{{ row.values[field] }}</pre></template>
          </el-table-column>
        </el-table>
        <div class="field-help">Показаны максимум 3 строки. Значения длиннее 500 символов сокращаются только в preview.</div>
        <el-form label-position="top" class="mapping-form">
          <el-form-item label="Идентификатор строки">
            <el-select v-model="importMapping.external_id_field" placeholder="Поле файла" @change="mappingEnabled = false"><el-option v-for="field in sourceFields" :key="field" :label="field" :value="field" /></el-select>
          </el-form-item>
          <el-form-item label="Текст для модели">
            <el-select v-model="importMapping.input_text_field" placeholder="Поле файла" @change="mappingEnabled = false"><el-option v-for="field in sourceFields" :key="field" :label="field" :value="field" /></el-select>
          </el-form-item>
          <el-form-item label="Эталонный ответ (необязательно)">
            <el-select v-model="importMapping.reference_field" clearable placeholder="Не использовать" @change="mappingEnabled = false"><el-option v-for="field in sourceFields" :key="field" :label="field" :value="field" /></el-select>
          </el-form-item>
          <el-form-item v-if="importMapping.reference_field" label="Формат эталона"><el-select v-model="importMapping.reference_format" @change="mappingEnabled = false"><el-option value="text" label="Обычный текст → reference.text" /><el-option value="json" label="JSON-объект" /></el-select></el-form-item>
        </el-form>
        <p>Текст для модели преобразуется в input.text. Текстовый эталон — в reference.text; фигурные скобки вручную не нужны.</p>
        <el-button type="primary" plain :disabled="!mappingReady" :loading="previewing" @click="applyMapping">Применить сопоставление</el-button>
        <el-tag v-if="mappingEnabled && previewResult?.mapping_applied && !previewResult.invalid_count" type="success" class="mapping-status">Сопоставление проверено</el-tag>
        <div v-if="mappingEnabled && previewResult?.mapping_applied"><b>После преобразования (первые 3 строки)</b><pre v-for="(row, index) in previewResult.preview?.slice(0, 3)" :key="index" class="source-value">{{ prettyJson(row) }}</pre></div>
      </div>
      <el-collapse v-if="previewResult?.row_errors?.length" v-model="openPanels" class="space">
        <el-collapse-item name="errors" title="Почему строки не приняты">
          <el-table :data="previewResult.row_errors" size="small"><el-table-column prop="row" label="Строка" width="100" /><el-table-column prop="reason" label="Причина" /></el-table>
        </el-collapse-item>
      </el-collapse>
      <el-alert v-if="savedMessage" :title="savedMessage" type="success" show-icon class="space" :closable="false" />
    </el-card>

    <el-card class="space">
      <template #header><div class="card-header"><div><b>Сохранённые версии</b><div class="hint">Опубликованная версия неизменяема; изменения должны создавать новую версию.</div></div><el-button :loading="loading" @click="loadVersions">Обновить</el-button></div></template>
      <el-table :data="versions" empty-text="Датасетов пока нет">
        <el-table-column prop="dataset_name" label="Датасет" min-width="220" />
        <el-table-column label="Версия" width="100"><template #default="{ row }">v{{ row.version_number }}</template></el-table-column>
        <el-table-column label="Статус" width="130"><template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'warning'">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="Создан" width="190"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
                <el-table-column label="Действия" width="250"><template #default="{ row }">
          <el-button link :loading="loadingItems && selectedVersion?.id === row.id" @click="viewVersion(row)">Просмотреть</el-button>
          <el-button v-if="row.status === 'draft'" link type="primary" @click="startRevision(row)">Продолжить</el-button>
          <el-button v-else link type="primary" :disabled="hasDraft(row.dataset_id)" @click="startRevision(row)">{{ hasDraft(row.dataset_id) ? 'Есть черновик' : 'Новая версия' }}</el-button>
        </template></el-table-column>
      </el-table>
      <el-alert title="Удаление опубликованных версий временно недоступно: сначала нужна retention-политика, чтобы не разрушить историю запусков." type="info" :closable="false" class="space" />
    </el-card>

    <el-dialog v-model="detailsVisible" :title="selectedVersion ? selectedVersion.dataset_name + ' · v' + selectedVersion.version_number : 'Датасет'" width="80%">
      <el-alert v-if="itemPage.total > itemPage.items.length" :title="'Показаны первые ' + itemPage.items.length + ' из ' + itemPage.total + ' строк.'" type="info" :closable="false" />
      <el-table :data="itemPage.items" class="space" empty-text="В этой версии нет строк">
        <el-table-column prop="external_id" label="external_id" width="160" />
        <el-table-column label="input" min-width="280"><template #default="{ row }"><pre>{{ prettyJson(row.input_json) }}</pre></template></el-table-column>
        <el-table-column label="reference" min-width="240"><template #default="{ row }"><pre>{{ prettyJson(row.reference_json) }}</pre></template></el-table-column>
        <el-table-column label="tags" width="160"><template #default="{ row }">{{ (row.tags_json || []).join(', ') || '—' }}</template></el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { evaluationApi } from '../api'

const versions = ref([])
const loading = ref(false)
const previewing = ref(false)
const saving = ref(false)
const loadingItems = ref(false)
const error = ref('')
const savedMessage = ref('')
const previewResult = ref(null)
const selectedFile = ref(null)
const revisionContext = ref(null)
const mappingEnabled = ref(false)
const importMapping = reactive({ external_id_field: '', input_text_field: '', reference_field: '', reference_format: 'text' })
const fileInputKey = ref(0)
const openPanels = ref([])
const detailsVisible = ref(false)
const selectedVersion = ref(null)
const itemPage = reactive({ total: 0, items: [] })
const initialRow = '{"external_id":"row-1","input":{"text":""}}'
const initialJsonArray = '[\n  ' + initialRow + '\n]'
const form = reactive({ name: '', source: 'json', rowsText: initialJsonArray })

const textPlaceholder = computed(() => form.source === 'jsonl' ? initialRow + '\n{"external_id":"row-2","input":{"text":"..."}}' : '[\n  ' + initialRow + '\n]')
const canSave = computed(() => Boolean(form.name.trim() && previewResult.value && previewResult.value.invalid_count === 0 && previewResult.value.valid_count > 0 && (!previewResult.value.mapping_applied || mappingEnabled.value) && (form.source !== 'file' || selectedFile.value)))
const previewTitle = computed(() => previewResult.value ? 'Проверка: корректных строк — ' + previewResult.value.valid_count + ', ошибок — ' + previewResult.value.invalid_count + '.' : '')
const sourceFields = computed(() => previewResult.value?.source_fields || [])
const sourcePreview = computed(() => previewResult.value?.source_preview || [])
const mappingReady = computed(() => Boolean(importMapping.external_id_field && importMapping.input_text_field))

function explain(cause, fallback) {
  const detail = cause.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ')
  if (detail?.message) return detail.message
  return cause.message || fallback
}
function parseJsonArray() {
  let value
  try { value = JSON.parse(form.rowsText) }
  catch (cause) { throw new Error('Некорректный JSON-массив: ' + cause.message + '. Если каждый объект записан с новой строки без запятых, выберите «JSONL-текст».') }
  if (!Array.isArray(value)) throw new Error('Ожидается JSON-массив в квадратных скобках. Для построчного формата выберите «JSONL-текст».')
  return value
}
function parseJsonl() {
  const rows = []
  for (const [index, line] of form.rowsText.split(/\r?\n/).entries()) {
    if (!line.trim()) continue
    try {
      const value = JSON.parse(line)
      if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('строка должна быть JSON-объектом')
      rows.push(value)
    } catch (cause) {
      throw new Error('JSONL, строка ' + (index + 1) + ': ' + cause.message + '. Ожидается один полный JSON-объект без запятой в конце.')
    }
  }
  if (!rows.length) throw new Error('JSONL не содержит непустых строк.')
  return rows
}
function textRows() { return form.source === 'jsonl' ? parseJsonl() : parseJsonArray() }
function currentImportMapping() {
  if (!mappingEnabled.value || !mappingReady.value) return null
  return {
    external_id_field: importMapping.external_id_field,
    input_text_field: importMapping.input_text_field,
    reference_field: importMapping.reference_field || null,
    reference_format: importMapping.reference_format,
  }
}
function resetMapping() {
  mappingEnabled.value = false
  importMapping.external_id_field = ''
  importMapping.input_text_field = ''
  importMapping.reference_field = ''
}
function suggestMapping() {
  const find = (...names) => sourceFields.value.find((field) => names.includes(field.toLowerCase())) || ''
  if (!importMapping.external_id_field) importMapping.external_id_field = find('external_id', 'id')
  if (!importMapping.input_text_field) importMapping.input_text_field = find('transcript', 'text', 'input_text', 'prompt')
  if (!importMapping.reference_field) importMapping.reference_field = find('reference', 'reference_summary', 'expected_output')
}
function resetPreview() { previewResult.value = null; savedMessage.value = ''; openPanels.value = [] }
function hasDraft(datasetId) { return versions.value.some((version) => version.dataset_id === datasetId && version.status === 'draft') }
function resetEditor() {
  form.source = 'json'
  form.rowsText = initialJsonArray
  selectedFile.value = null
  fileInputKey.value += 1
  resetMapping()
  resetPreview()
  error.value = ''
}
async function startRevision(version) {
  const sameDataset = versions.value.filter((item) => item.dataset_id === version.dataset_id)
  const nextVersion = Math.max(...sameDataset.map((item) => item.version_number), 0) + 1
  revisionContext.value = {
    datasetId: version.dataset_id,
    datasetName: version.dataset_name,
    baseVersionId: version.status === 'published' ? version.id : null,
    draftVersionId: version.status === 'draft' ? version.id : null,
    versionNumber: version.status === 'draft' ? version.version_number : nextVersion,
  }
  resetEditor()
  form.name = version.dataset_name
  if (version.status === 'draft') {
    try {
      const rows = []
      let offset = 0
      while (true) {
        const page = (await evaluationApi.listDatasetItems(version.id, { limit: 500, offset })).data
        rows.push(...page.items.map((item) => ({ external_id: item.external_id, input: item.input_json, reference: item.reference_json, metadata: item.metadata_json, tags: item.tags_json })))
        offset += page.items.length
        if (offset >= page.total || !page.items.length) break
      }
      if (rows.length) { form.rowsText = JSON.stringify(rows, null, 2); await preview() }
    } catch (cause) { error.value = explain(cause, 'Не удалось прочитать черновик') }
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function cancelRevision() {
  revisionContext.value = null
  form.name = ''
  resetEditor()
}
function changeSource(source) {
  const current = form.rowsText.trim()
  if (source === 'jsonl' && current === initialJsonArray.trim()) form.rowsText = initialRow
  if (source === 'json' && current === initialRow) form.rowsText = initialJsonArray
  resetMapping()
  resetPreview()
}
function selectFile(event) { selectedFile.value = event.target.files?.[0] || null; resetMapping(); resetPreview() }
async function applyMapping() {
  if (!mappingReady.value) return
  mappingEnabled.value = true
  await preview()
}
function prettyJson(value) { return value == null ? '—' : JSON.stringify(value, null, 2) }
function formatDelimiter(value) { return value === '\t' ? 'табуляция' : value === ' ' ? 'пробел' : '«' + value + '»' }
function formatDate(value) { return value ? new Date(value).toLocaleString('ru-RU') : '—' }

async function loadVersions() {
  loading.value = true
  error.value = ''
  try { versions.value = (await evaluationApi.listDatasetVersions()).data }
  catch (cause) { error.value = explain(cause, 'Не удалось загрузить датасеты') }
  finally { loading.value = false }
}
async function preview() {
  previewing.value = true
  error.value = ''
  savedMessage.value = ''
  previewResult.value = null
  openPanels.value = []
  try {
    if (form.source === 'file') {
      if (!selectedFile.value) throw new Error('Выберите файл CSV или JSONL')
      previewResult.value = (await evaluationApi.previewImport(selectedFile.value, currentImportMapping())).data
    } else previewResult.value = (await evaluationApi.previewItems(textRows())).data
    if (form.source === 'file' && !previewResult.value.mapping_applied) suggestMapping()
    if (previewResult.value.invalid_count) openPanels.value = ['errors']
  } catch (cause) { error.value = explain(cause, 'Не удалось проверить строки') }
  finally { previewing.value = false }
}
async function save() {
  saving.value = true
  error.value = ''
  savedMessage.value = ''
  try {
    const wasRevision = Boolean(revisionContext.value && revisionContext.value.versionNumber > 1)
    const name = form.name.trim()
    const mapping = form.source === 'file' ? currentImportMapping() : null
    const schema = { modalities: ['text'], ...(mapping ? { import_mapping: mapping } : {}) }
    let draftVersionId
    let publishedVersionNumber = 1
    if (revisionContext.value) {
      publishedVersionNumber = revisionContext.value.versionNumber
      if (revisionContext.value.draftVersionId) draftVersionId = revisionContext.value.draftVersionId
      else {
        const createdVersion = (await evaluationApi.createDatasetVersion(revisionContext.value.datasetId, {
          base_version_id: revisionContext.value.baseVersionId,
          schema,
        })).data
        draftVersionId = createdVersion.id
        revisionContext.value = { ...revisionContext.value, draftVersionId, versionNumber: createdVersion.version_number }
        publishedVersionNumber = createdVersion.version_number
      }
    } else {
      const dataset = (await evaluationApi.createDataset({ name, schema })).data
      draftVersionId = dataset.draft_version_id
      revisionContext.value = { datasetId: dataset.id, datasetName: name, draftVersionId, versionNumber: 1 }
    }
    const existing = []
    let offset = 0
    while (true) {
      const page = (await evaluationApi.listDatasetItems(draftVersionId, { limit: 500, offset })).data
      existing.push(...page.items.map((item) => ({ external_id: item.external_id, input: item.input_json, reference: item.reference_json, metadata: item.metadata_json, tags: item.tags_json })))
      offset += page.items.length
      if (offset >= page.total || !page.items.length) break
    }
    if (existing.length) {
      const canonical = (value) => Array.isArray(value) ? value.map(canonical)
        : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])])) : value
      const fingerprint = (rows) => JSON.stringify(canonical([...rows].sort((a, b) => a.external_id.localeCompare(b.external_id))))
      if (fingerprint(existing) !== fingerprint(previewResult.value.preview)) throw new Error('В черновике уже сохранены другие строки. Откройте «Продолжить» в списке, чтобы проверить и опубликовать сохранённые данные.')
    } else if (form.source === 'file') {
      if (!selectedFile.value) throw new Error('Выберите файл CSV или JSONL')
      await evaluationApi.commitImport(draftVersionId, selectedFile.value, mapping)
    } else await evaluationApi.commitItems(draftVersionId, textRows())
    await evaluationApi.publishDataset(draftVersionId)
    savedMessage.value = wasRevision
      ? 'Опубликована новая версия «' + name + '» · v' + publishedVersionNumber + '.'
      : 'Опубликован датасет «' + name + '». Он доступен в экспериментах.'
    revisionContext.value = null
    form.name = ''
    previewResult.value = null
    selectedFile.value = null
    resetMapping()
    fileInputKey.value += 1
    await loadVersions()
  } catch (cause) { error.value = explain(cause, 'Не удалось сохранить датасет') }
  finally { saving.value = false }
}
async function viewVersion(version) {
  selectedVersion.value = version
  loadingItems.value = true
  error.value = ''
  try {
    const response = await evaluationApi.listDatasetItems(version.id, { limit: 100, offset: 0 })
    itemPage.total = response.data.total
    itemPage.items = response.data.items
    detailsVisible.value = true
  } catch (cause) { error.value = explain(cause, 'Не удалось открыть строки датасета') }
  finally { loadingItems.value = false }
}

onMounted(loadVersions)
</script>

<style scoped>
.datasets-view { max-width: 1100px; margin: 0 auto; }
.dataset-form { max-width: 820px; }
.space { margin-top: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.hint, .field-help { color: var(--el-text-color-secondary); font-weight: normal; }
.hint { margin-top: 4px; }
.field-help { display: block; font-size: 12px; margin-top: 6px; }
.canonical-help { margin: 4px 0; }
.revision-banner { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 12px 16px; margin-bottom: 16px; border: 1px solid var(--el-color-primary-light-5); border-radius: 6px; background: var(--el-color-primary-light-9); }
.detected-format { margin-top: 8px; color: var(--el-text-color-secondary); font-size: 13px; }
.mapping-panel { padding: 16px; border: 1px solid var(--el-border-color); border-radius: 6px; }
.source-preview-title { margin-top: 16px; margin-bottom: 8px; font-weight: 600; }
.source-preview { width: 100%; }
.source-value { max-height: 120px; overflow: auto; }
.mapping-form { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin-top: 12px; }
.mapping-status { margin-left: 12px; }
pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
</style>
