<template>
  <section class="evaluation-panel">
    <h3>Оценка сохранённых ответов</h3>
    <p>Тестируемые модели повторно не вызываются. Каждая оценка сохраняется отдельно.</p>
    <el-alert v-if="error && !opened" :title="error" type="error" :closable="false" />
    <el-button v-if="!opened" :disabled="!finished || !eligible.length" @click="openForm">Оценить ответы</el-button>
    <el-form v-if="opened" label-position="top">
      <el-form-item label="Модель-судья"><el-select v-model="judgeRouteId" placeholder="Выберите судью" filterable><el-option v-for="route in routes" :key="route.id" :value="route.id" :label="route.provider_name + ' / ' + route.model_identifier" :disabled="!route.credential_available" /></el-select></el-form-item>
      <el-form-item label="Правила оценки"><el-select v-model="suiteId" placeholder="Выберите сохранённые правила"><el-option v-for="suite in suites" :key="suite.id" :value="suite.id" :label="suite.name" /></el-select></el-form-item>
      <p v-if="!suites.length">Создайте правила в разделе «Эксперименты» → «Настройки эксперимента».</p>
      <div v-if="selectedSuite">
        <el-table :data="selectedSuite.evaluators_json?.[0]?.criteria || []"><el-table-column prop="key" label="Критерий" /><el-table-column prop="description" label="Что оценивать" /><el-table-column v-if="selectedSuite.decision_rule_json?.scoring_mode !== 'independent'" prop="weight" label="Вес" width="90" /><el-table-column v-else label="Шкала"><template #default="{ row }">{{ row.min_score }}–{{ row.max_score }}</template></el-table-column></el-table>
        <p v-if="selectedSuite.decision_rule_json?.scoring_mode !== 'independent'">Итоговый балл — сумма оценок 0–1, умноженных на веса. Порог успешной оценки: {{ selectedSuite.decision_rule_json?.quality_threshold }}.</p>
        <p v-else>Независимые оценки, без общего балла: <span v-for="c in selectedSuite.evaluators_json?.[0]?.criteria" :key="c.key">{{ c.key }}: {{ c.min_score }}–{{ c.max_score }}; </span></p>
      </div>
      <p><router-link to="/experiments">Открыть редактор инструкций и правил</router-link>. Изменения сохраняются новыми копиями и не меняют прошлые оценки.</p>
      <el-form-item label="Сохранённая инструкция судье"><el-select v-model="selectedPromptId" placeholder="Новая инструкция или сохранённый вариант" clearable @change="selectPrompt"><el-option v-for="prompt in judgePrompts" :key="prompt.id" :value="prompt.id" :label="prompt.name + ' · ' + prompt.id.slice(0, 8)" /></el-select></el-form-item>
      <el-form-item label="Инструкция судье"><el-input v-model="instruction" type="textarea" :rows="6" /></el-form-item>
      <el-form-item label="Лимит токенов ответа судьи"><el-input-number v-model="maxOutputTokens" :min="128" :max="65536" :step="1024" /><span>Больший лимит может увеличить время и стоимость.</span></el-form-item>
      <p>В правилах пишите критерии, не полный промпт: например «Полнота: 0 — важные факты пропущены, 3 — большинство отражено, 5 — все отражены». Шкалы задаются отдельными полями и добавляются автоматически. Инструкция судье задаёт общий подход. Служебный текст со шкалами и форматом scores/rationale добавляется к запросу; отдельного скрытого system-промпта сейчас нет.</p>
      <p>Инструкция объясняет судье, как рассуждать; правила выше — что оценивать и по какой шкале. Переменные: <code v-pre>{{input}}</code> — вход, <code v-pre>{{reference}}</code> — эталон, <code v-pre>{{output}}</code> — ответ проверяемой модели (обязательно). Значение баллов и требования опишите в критериях.</p>
      <p>JSON-контракт scores/rationale добавляется автоматически: писать схему ответа или Pipeline для судьи не нужно. Изменённая инструкция сохранится новым вариантом.</p>
      <el-alert :title="'Будет выполнено: ' + eligible.length + ' вызовов судьи. Повторных вызовов тестируемых моделей: 0.'" type="info" :closable="false" />
      <el-alert v-if="selectedRoute?.provider_name === 'offline'" title="Offline — только проверка работы программы. Его оценки не измеряют качество ответов." type="warning" :closable="false" />
      <el-alert v-if="error" :title="error" type="error" :closable="false" class="space" />
      <el-button class="space" type="primary" :loading="saving" :disabled="!judgeRouteId || !suiteId || !instruction.trim()" @click="startEvaluation">Запустить отдельную оценку</el-button>
    </el-form>
    <div v-if="history.length" class="space"><b>Предыдущие оценки</b><div v-for="entry in history" :key="entry.id"><router-link :to="'/runs/' + entry.id">{{ entry.id.slice(0, 8) }} · {{ entry.status }}</router-link></div></div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { evaluationApi } from '../api'
import { explain } from '../utils/evaluationErrors'
const props = defineProps({ run: { type: Object, required: true }, items: { type: Array, required: true } })
const router = useRouter()
const opened = ref(false), saving = ref(false), error = ref('')
const maxOutputTokens = ref(4096)
const routes = ref([]), suites = ref([]), history = ref([])
const prompts = ref([]), selectedPromptId = ref('')
const judgePrompts = computed(() => prompts.value.filter((prompt) => /{{\s*output\s*}}/.test(prompt.template)))
function selectPrompt(id) { const prompt = prompts.value.find((item) => item.id === id); if (prompt) instruction.value = prompt.template }
const judgeRouteId = ref(''), suiteId = ref('')
const instruction = ref('Оцени ответ по заданным критериям. Сравни с эталоном, если он есть. Обоснуй оценки.\nВход: {{input}}\nЭталон: {{reference}}\nОтвет модели: {{output}}')
const eligible = computed(() => props.items.filter((item) => item.status === 'completed' && typeof item.output_json?.text === 'string' && item.output_json.text.trim()))
const finished = computed(() => ['completed', 'completed_with_errors', 'cancelled', 'failed'].includes(props.run.status))
const selectedSuite = computed(() => suites.value.find((suite) => suite.id === suiteId.value))
const selectedRoute = computed(() => routes.value.find((route) => route.id === judgeRouteId.value))
async function openForm() {
  error.value = ''
  try {
    const [routeRows, suiteRows, promptRows] = await Promise.all([evaluationApi.listRoutes(), evaluationApi.listSuites(), evaluationApi.listPrompts()])
    routes.value = routeRows.data; suites.value = suiteRows.data; prompts.value = promptRows.data
    opened.value = true
  } catch (cause) { error.value = explain(cause, 'Не удалось загрузить настройки оценки') }
}
async function startEvaluation() {
  saving.value = true; error.value = ''
  try {
    if (!/{{\s*output\s*}}/.test(instruction.value)) throw new Error('Добавьте {{output}} в инструкцию: сюда подставится сохранённый ответ, который должен оценить судья.')
    const selected = prompts.value.find((item) => item.id === selectedPromptId.value)
    const prompt = selected?.template === instruction.value ? selected : (await evaluationApi.createPrompt({ name: selected ? selected.name + ' — копия' : 'Инструкция судье — ' + Date.now(), template: instruction.value })).data
    const created = (await evaluationApi.createEvaluation(props.run.id, { judge_route_id: judgeRouteId.value, judge_prompt_id: prompt.id, suite_version_id: suiteId.value, max_output_tokens: maxOutputTokens.value })).data
    await router.push('/runs/' + created.id)
  } catch (cause) { error.value = explain(cause, 'Не удалось запустить оценку') } finally { saving.value = false }
}
onMounted(async () => {
  try { history.value = (await evaluationApi.listEvaluations(props.run.id)).data }
  catch (cause) { error.value = explain(cause, 'Не удалось загрузить историю оценок') }
})
</script>

<style scoped>
.evaluation-panel { margin-top: 24px; }
.space { margin-top: 16px; }
.el-select { width: 100%; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
