<template>
  <el-card class="space configuration-card">
    <template #header><b>Настройки эксперимента</b></template>
    <p>Инструкция говорит модели, что сделать. Схема обработки определяет порядок вызовов. Правила оценки нужны только для отдельного судьи после получения ответов.</p>
    <el-button type="primary" :loading="creatingRecommended" @click="createRecommendedConfiguration">Создать и выбрать рекомендуемую настройку</el-button>
    <el-alert v-if="libraryError" :title="libraryError" type="error" :closable="false" class="space" />
    <el-alert v-if="configurationCreated" :title="configurationCreated" type="success" :closable="false" class="space" />
    <p class="hint">Откройте сохранённый вариант в списке, чтобы прочитать или изменить его. Изменения сохраняются новой копией: оригинал и прошлые запуски остаются прежними.</p>

    <section class="config-section prompt-editor">
      <h3>Инструкция модели (PromptVersion)</h3>
      <el-form label-position="top" @submit.prevent="savePrompt">
        <el-form-item label="Сохранённые инструкции"><el-select v-model="selectedPromptId" placeholder="Открыть сохранённую инструкцию" filterable @change="openPrompt"><el-option v-for="item in prompts" :key="item.id" :value="item.id" :label="itemLabel(item)" /></el-select><el-button class="new-button" @click="newPrompt">Новая инструкция</el-button></el-form-item>
        <el-form-item label="Название инструкции"><el-input v-model="promptForm.name" /></el-form-item>
        <el-form-item label="Загрузить YAML-промпт"><input type="file" accept=".yaml,.yml" @change="importYaml" /><span>Файл заполнит редактор, но не сохранится автоматически.</span></el-form-item>
        <el-alert v-if="importNotice" :title="importNotice" type="warning" :closable="false" />
        <el-button v-if="importNotice" @click="promptForm.template += '\n\nВходные данные:\n{{text}}'">Добавить подстановку текста датасета</el-button>
        <el-form-item label="Текст инструкции"><el-input v-model="promptForm.template" type="textarea" :rows="8" /></el-form-item>
        <p v-pre>Пишите обычный текст, например: «Кратко перескажи разговор: {{text}}». {{text}} берётся из поля input.text датасета; {{input.text}} — также допустимая запись. Вложенные поля: {{customer.name}}.</p>
        <p v-pre>Нужен JSON-ответ? Опишите его в тексте промпта: «Верни JSON: {"summary": "..."}». Обычные скобки остаются текстом; двойные {{...}} используются только для подстановки данных. Проверка ответа по JSON Schema пока не выполняется.</p>
        <el-alert v-if="errors.prompt" :title="errors.prompt" type="error" :closable="false" />
        <el-alert v-if="messages.prompt" :title="messages.prompt" type="success" :closable="false" />
        <el-button type="primary" :loading="saving.prompt" @click="savePrompt">{{ selectedPromptId ? 'Сохранить новую копию инструкции' : 'Сохранить инструкцию' }}</el-button>
      </el-form>
    </section>

    <section class="config-section pipeline-editor">
      <h3>Схема обработки (PipelineVersion)</h3>
      <p>Это не схема ответа. Pipeline описывает последовательность работы: данные → подстановка в промпт → вызов модели → сохранённый ответ.</p>
      <p>Сейчас поддерживается один вызов модели. JSON вручную заполнять не нужно. Желаемый формат ответа задайте в инструкции выше.</p>
      <el-form label-position="top" @submit.prevent="savePipeline">
        <el-form-item label="Сохранённые схемы"><el-select v-model="selectedPipelineId" placeholder="Открыть сохранённую схему" filterable @change="openPipeline"><el-option v-for="item in pipelines" :key="item.id" :value="item.id" :label="itemLabel(item)" /></el-select><el-button class="new-button" @click="newPipeline">Новая схема</el-button></el-form-item>
        <el-form-item label="Название схемы"><el-input v-model="pipelineForm.name" /></el-form-item>
        <el-alert v-if="!supportedPipeline" title="Эта сохранённая схема пока не поддерживается исполнителем. Можно прочитать её ниже и явно заменить в новой копии на один вызов модели." type="warning" :closable="false" />
        <el-button v-if="!supportedPipeline" @click="pipelineForm.definition = defaultPipeline()">Взять поддерживаемую схему</el-button>
        <details><summary>Техническое представление схемы</summary><pre>{{ JSON.stringify(pipelineForm.definition, null, 2) }}</pre></details>
        <el-alert v-if="errors.pipeline" :title="errors.pipeline" type="error" :closable="false" />
        <el-alert v-if="messages.pipeline" :title="messages.pipeline" type="success" :closable="false" />
        <el-button type="primary" :loading="saving.pipeline" :disabled="!supportedPipeline" @click="savePipeline">{{ selectedPipelineId ? 'Сохранить новую копию схемы' : 'Сохранить схему' }}</el-button>
      </el-form>
    </section>

    <section class="config-section suite-editor">
      <h3>Правила оценки (EvaluationSuite)</h3>
      <p>Каждый критерий оценивается отдельно по своей шкале. Общий балл нужен только в режиме взвешенной оценки.</p>
      <el-form label-position="top" @submit.prevent="saveSuite">
        <el-form-item label="Сохранённые правила"><el-select v-model="selectedSuiteId" placeholder="Открыть сохранённые правила" filterable @change="openSuite"><el-option v-for="item in suites" :key="item.id" :value="item.id" :label="itemLabel(item)" /></el-select><el-button class="new-button" @click="newSuite">Новые правила</el-button></el-form-item>
        <el-form-item label="Название правил"><el-input v-model="suiteForm.name" /></el-form-item>
        <el-form-item label="Режим оценки"><el-select v-model="suiteForm.mode"><el-option value="independent" label="Независимые оценки по своим шкалам" /><el-option value="weighted" label="Общий взвешенный балл (0–1)" /></el-select></el-form-item>
        <div v-for="(criterion, index) in suiteForm.criteria" :key="index" class="criterion-row">
          <el-form-item :label="'Код критерия ' + (index + 1)"><el-input v-model="criterion.key" placeholder="accuracy" /></el-form-item>
          <el-form-item :label="'Что оценивать ' + (index + 1)"><el-input v-model="criterion.description" type="textarea" :rows="2" placeholder="Насколько ответ соответствует фактам и эталону" /></el-form-item>
          <el-form-item v-if="suiteForm.mode === 'weighted'" :label="'Вес ' + (index + 1)"><el-input-number v-model="criterion.weight" :min="0.01" :max="1" :step="0.05" :precision="2" /></el-form-item>
          <div v-else><el-form-item :label="'Минимум ' + (index + 1)"><el-input-number v-model="criterion.min_score" /></el-form-item><el-form-item :label="'Максимум ' + (index + 1)"><el-input-number v-model="criterion.max_score" /></el-form-item></div>
          <el-button :disabled="suiteForm.criteria.length === 1" @click="suiteForm.criteria.splice(index, 1)">Убрать критерий {{ index + 1 }}</el-button>
        </div>
        <el-button @click="suiteForm.criteria.push({ key: '', description: '', weight: 0.5, min_score: 0, max_score: 5 })">Добавить критерий</el-button>
        <p v-if="suiteForm.mode === 'weighted'" :class="{ invalid: !weightsValid }">Сумма весов: {{ weightSum.toFixed(2) }} / 1.00</p>
        <p class="hint">Код: латинские строчные буквы, цифры и подчёркивание. В независимом режиме веса и общий порог не используются; оценки выводятся отдельными столбцами.</p>
        <el-form-item v-if="suiteForm.mode === 'weighted'" label="Порог успешной оценки"><el-input-number v-model="suiteForm.threshold" :min="0" :max="1" :step="0.05" /></el-form-item>
        <el-alert v-if="errors.suite" :title="errors.suite" type="error" :closable="false" />
        <el-alert v-if="messages.suite" :title="messages.suite" type="success" :closable="false" />
        <el-button type="primary" :loading="saving.suite" @click="saveSuite">{{ selectedSuiteId ? 'Сохранить новую копию правил' : 'Сохранить правила' }}</el-button>
      </el-form>
    </section>
  </el-card>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { evaluationApi } from '../api'
import { explain } from '../utils/evaluationErrors'
const emit = defineEmits(['created'])
const prompts = ref([]), pipelines = ref([]), suites = ref([])
const selectedPromptId = ref(''), selectedPipelineId = ref(''), selectedSuiteId = ref('')
const libraryError = ref(''), configurationCreated = ref(''), creatingRecommended = ref(false)
const errors = reactive({ prompt: '', pipeline: '', suite: '' }), messages = reactive({ prompt: '', pipeline: '', suite: '' })
const saving = reactive({ prompt: false, pipeline: false, suite: false })
const importNotice = ref('')
async function importYaml(event) {
  const file = event.target.files?.[0]
  if (!file) return
  resetMessages('prompt'); importNotice.value = ''
  try {
    if (file.size > 256 * 1024) throw new Error('Максимальный размер YAML — 256 KiB.')
    const data = new FormData(); data.append('file', file)
    const imported = (await evaluationApi.importPrompt(data)).data
    selectedPromptId.value = ''; Object.assign(promptForm, { name: imported.name, template: imported.template })
    importNotice.value = imported.warnings.join(' ') + (imported.ignored_fields.length ? ' Не применены поля: ' + imported.ignored_fields.join(', ') : '')
  } catch (cause) { errors.prompt = explain(cause, 'Не удалось прочитать YAML') }
  event.target.value = ''
}
const defaultPipeline = () => ({ nodes: [{ id: 'generate', kind: 'generate' }], edges: [] })
const defaultCriteria = () => [{ key: 'quality', description: 'Точность и полнота ответа относительно задания и эталона, если он задан', weight: 1 }]
const promptForm = reactive({ name: '', template: 'Кратко перескажи: {{text}}' })
const pipelineForm = reactive({ name: '', definition: defaultPipeline() })
const suiteForm = reactive({ name: '', criteria: defaultCriteria().map(c => ({ ...c, min_score: 0, max_score: 5 })), threshold: 0.7, mode: 'independent' })
const weightSum = computed(() => suiteForm.criteria.reduce((sum, row) => sum + Number(row.weight || 0), 0))
const weightsValid = computed(() => Math.abs(weightSum.value - 1) < 0.000001)
const supportedPipeline = computed(() => {
  const value = pipelineForm.definition, nodes = value?.nodes
  return Array.isArray(nodes) && nodes.length === 1 && nodes[0]?.kind === 'generate' && typeof nodes[0]?.id === 'string' && nodes[0].id.trim() && Array.isArray(value.edges || []) && !(value.edges || []).length && Object.keys(value).every((key) => ['nodes', 'edges'].includes(key)) && Object.keys(nodes[0]).every((key) => ['id', 'kind'].includes(key))
})
const itemLabel = (item) => item.name + ' · ' + item.id.slice(0, 8)
const clone = (value) => JSON.parse(JSON.stringify(value))
function resetMessages(kind) { errors[kind] = ''; messages[kind] = '' }
function newPrompt() { selectedPromptId.value = ''; Object.assign(promptForm, { name: '', template: 'Кратко перескажи: {{text}}' }); resetMessages('prompt') }
function newPipeline() { selectedPipelineId.value = ''; Object.assign(pipelineForm, { name: '', definition: defaultPipeline() }); resetMessages('pipeline') }
function newSuite() { selectedSuiteId.value = ''; Object.assign(suiteForm, { name: '', criteria: defaultCriteria().map(c => ({ ...c, min_score: 0, max_score: 5 })), threshold: 0.7, mode: 'independent' }); resetMessages('suite') }
function openPrompt(id) { const item = prompts.value.find((row) => row.id === id); if (item) Object.assign(promptForm, { name: item.name, template: item.template }); resetMessages('prompt') }
function openPipeline(id) { const item = pipelines.value.find((row) => row.id === id); if (item) Object.assign(pipelineForm, { name: item.name, definition: clone(item.definition_json) }); resetMessages('pipeline') }
function openSuite(id) { const item = suites.value.find((row) => row.id === id); if (item) Object.assign(suiteForm, { name: item.name, criteria: clone(item.evaluators_json?.[0]?.criteria || []).map(c => ({ min_score: 0, max_score: 1, ...c })), threshold: item.decision_rule_json?.quality_threshold ?? 0.7, mode: item.decision_rule_json?.scoring_mode || 'weighted' }); resetMessages('suite') }
async function loadLibrary() {
  libraryError.value = ''
  try {
    const [p, g, s] = await Promise.all([evaluationApi.listPrompts(), evaluationApi.listPipelines(), evaluationApi.listSuites()])
    prompts.value = p.data; pipelines.value = g.data; suites.value = s.data
  } catch (cause) { libraryError.value = explain(cause, 'Не удалось загрузить сохранённые настройки') }
}
async function savePrompt() {
  saving.prompt = true; resetMessages('prompt')
  try {
    if (!promptForm.name.trim()) throw new Error('Укажите название инструкции.')
    const item = (await evaluationApi.createPrompt({ name: promptForm.name.trim(), template: promptForm.template })).data
    await loadLibrary(); selectedPromptId.value = item.id
    emit('created', { promptVersionId: item.id })
    messages.prompt = 'Инструкция сохранена и выбрана: ' + itemLabel(item) + '. Предыдущие варианты не изменены.'
  } catch (cause) { errors.prompt = explain(cause, 'Не удалось сохранить инструкцию') } finally { saving.prompt = false }
}
async function savePipeline() {
  saving.pipeline = true; resetMessages('pipeline')
  try {
    if (!pipelineForm.name.trim()) throw new Error('Укажите название схемы.')
    const item = (await evaluationApi.createPipeline({ name: pipelineForm.name.trim(), definition: pipelineForm.definition })).data
    await loadLibrary(); selectedPipelineId.value = item.id
    emit('created', { pipelineVersionId: item.id })
    messages.pipeline = 'Схема сохранена и выбрана: ' + itemLabel(item) + '. Предыдущие варианты не изменены.'
  } catch (cause) { errors.pipeline = explain(cause, 'Не удалось сохранить схему') } finally { saving.pipeline = false }
}
async function saveSuite() {
  saving.suite = true; resetMessages('suite')
  try {
    if (!suiteForm.name.trim()) throw new Error('Укажите название правил.')
    if (!suiteForm.criteria.length || (suiteForm.mode === 'weighted' && !weightsValid.value)) throw new Error('Нужен хотя бы один критерий. Сумма весов должна равняться 1.')
    if (suiteForm.mode === 'independent' && suiteForm.criteria.some(c => !Number.isFinite(c.min_score) || !Number.isFinite(c.max_score) || c.min_score >= c.max_score)) throw new Error('У каждого критерия максимум шкалы должен быть больше минимума.')
    if (suiteForm.criteria.some((row) => !/^[a-z][a-z0-9_]*$/.test(row.key))) throw new Error('Код критерия: строчные латинские буквы, цифры и подчёркивание; начинается с буквы.')
    if (new Set(suiteForm.criteria.map((row) => row.key)).size !== suiteForm.criteria.length) throw new Error('Коды критериев не должны повторяться.')
    const criteria = suiteForm.criteria.map(c => suiteForm.mode === 'weighted' ? { ...c, min_score: 0, max_score: 1 } : { ...c, weight: 1 })
    const item = (await evaluationApi.createSuite({ name: suiteForm.name.trim(), criteria, quality_threshold: suiteForm.threshold, scoring_mode: suiteForm.mode })).data
    await loadLibrary(); selectedSuiteId.value = item.id
    emit('created', { suiteVersionId: item.id })
    messages.suite = 'Правила сохранены: ' + itemLabel(item) + '. Выберите их при отдельной оценке ответов.'
  } catch (cause) { errors.suite = explain(cause, 'Не удалось сохранить правила') } finally { saving.suite = false }
}
async function createRecommendedConfiguration() {
  creatingRecommended.value = true; libraryError.value = ''; configurationCreated.value = ''
  try {
    const suffix = Date.now()
    const [prompt, pipeline, suite] = await Promise.all([
      evaluationApi.createPrompt({ name: 'recommended-prompt-' + suffix, template: '{{text}}' }),
      evaluationApi.createPipeline({ name: 'recommended-pipeline-' + suffix, definition: defaultPipeline() }),
      evaluationApi.createSuite({ name: 'recommended-quality-' + suffix, criteria: defaultCriteria(), quality_threshold: 0.7 }),
    ])
    await loadLibrary()
    selectedPromptId.value = prompt.data.id; openPrompt(prompt.data.id)
    selectedPipelineId.value = pipeline.data.id; openPipeline(pipeline.data.id)
    selectedSuiteId.value = suite.data.id; openSuite(suite.data.id)
    emit('created', { promptVersionId: prompt.data.id, pipelineVersionId: pipeline.data.id, suiteVersionId: suite.data.id })
    configurationCreated.value = 'Готово: созданы и выбраны инструкция, линейная схема обработки и базовые правила оценки.'
  } catch (cause) { libraryError.value = explain(cause, 'Не удалось создать рекомендуемую настройку') } finally { creatingRecommended.value = false }
}
onMounted(loadLibrary)
</script>
<style scoped>
.space { margin-top: 16px; }
.config-section { margin-top: 28px; border-top: 1px solid var(--el-border-color); padding-top: 12px; }
.el-select { width: min(100%, 620px); }
.new-button { margin-left: 8px; }
.hint { color: var(--el-text-color-secondary); }
.invalid { color: var(--el-color-danger); }
.criterion-row { display: grid; grid-template-columns: 1fr 2fr 180px auto; gap: 12px; align-items: center; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
.el-alert { margin-bottom: 12px; }
@media (max-width: 850px) { .criterion-row { grid-template-columns: 1fr; } }
</style>
