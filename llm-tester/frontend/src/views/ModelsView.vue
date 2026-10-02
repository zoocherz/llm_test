<template>
  <div class="models-view">
    <el-card>
      <template #header><div><b>Модели</b><div class="hint">Настройте подключения, затем используйте одну модель как candidate, генератор данных или Judge.</div></div></template>
      <el-alert v-if="error" :title="error" type="error" show-icon class="space" />
      <el-form label-position="top" class="route-form">
        <el-form-item label="Сервис модели"><el-select v-model="provider" @change="loadCatalog"><el-option label="Offline — без внешнего API" value="offline" /><el-option label="Google Gemini" value="google" /><el-option label="OpenRouter" value="openrouter" /><el-option label="ЦРТ МКО — без авторизации" value="crt_mko" /></el-select></el-form-item>
        <el-form-item label="Модель">
          <el-input v-if="provider === 'offline'" v-model="activeDraft.model" />
          <div v-else class="model-picker"><el-select v-model="activeDraft.model" filterable allow-create default-first-option :loading="loadingCatalog" placeholder="Найдите или введите модель"><el-option v-for="model in visibleCatalog" :key="model.id" :value="model.id" :label="model.display_name + ' · ' + model.id"><span>{{ model.display_name }} · {{ model.id }}</span><el-tag v-if="model.is_free" type="success" size="small">бесплатно</el-tag></el-option></el-select><el-button :loading="loadingCatalog" @click="loadCatalog">Обновить список</el-button></div>
          <span v-if="provider !== 'offline'" class="field-help">Каталог загружается через backend. Ручной identifier остаётся fallback.</span>
          <el-checkbox v-if="provider === 'openrouter'" v-model="freeOnly">Только бесплатные модели</el-checkbox>
        </el-form-item>
        <el-form-item v-if="!['offline', 'crt_mko'].includes(provider)" label="Имя переменной с ключом"><el-input v-model="activeDraft.secretName" placeholder="GOOGLE_API_KEY" /><span class="field-help">Укажите только имя; значение ключа не передаётся браузеру.</span></el-form-item>
        <el-form-item v-if="provider === 'crt_mko'" label="Адрес API ЦРТ МКО"><el-input v-model="activeDraft.baseUrl" placeholder="https://mko.example.org:8443/api/v1" @input="endpointChanged" /><span class="field-help">Полный адрес API: сервер, порт и путь (обычно /api/v1). Без авторизации. Сначала укажите адрес, затем обновите список моделей. Лимит выходных токенов пока не гарантируется.</span><el-checkbox v-if="activeDraft.baseUrl.trim().toLowerCase().startsWith('http:')" v-model="activeDraft.allowHttp">Разрешаю передачу выбранных данных по HTTP</el-checkbox></el-form-item>
        <el-form-item label="Максимальное ожидание"><el-input-number v-model="activeDraft.timeout" :min="1" :max="600" /><span class="field-help">секунд на весь вызов, включая HTTP-повторы. После таймаута увеличьте ожидание и создайте новый запуск: старый повтор сохраняет прежний лимит.</span></el-form-item>
        <el-form-item><el-button type="primary" :loading="saving" @click="saveRoute">{{ editingId ? 'Сохранить изменения' : 'Сохранить подключение' }}</el-button><el-button v-if="editingId" @click="cancelEdit">Отменить изменение</el-button></el-form-item>
      </el-form>
      <el-alert v-if="catalogError" :title="catalogError" type="warning" show-icon :closable="false" />
      <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />
    </el-card>

    <el-card class="space">
      <template #header><div class="card-header"><div><b>Сохранённые модели</b><div class="hint">Изменения влияют только на будущие запуски; старые RunSnapshot остаются неизменными.</div></div><el-button :loading="loading" @click="loadRoutes">Обновить</el-button></div></template>
      <el-table :data="routes" empty-text="Подключений пока нет">
        <el-table-column prop="provider_name" label="Сервис" width="140" />
        <el-table-column prop="model_identifier" label="Модель" min-width="260" />
        <el-table-column label="Ключ" width="160"><template #default="{ row }"><el-tag :type="row.credential_available ? 'success' : 'danger'">{{ ['offline', 'crt_mko'].includes(row.provider_name) ? 'не требуется' : (row.credential_available ? 'доступен' : 'не найден') }}</el-tag></template></el-table-column>
        <el-table-column label="Адрес API" min-width="230"><template #default="{ row }">{{ row.capabilities_json?.base_url || (row.provider_name === 'crt_mko' ? 'Укажите адрес через «Изменить»' : 'Стандартный') }}</template></el-table-column>
        <el-table-column label="Timeout" width="110"><template #default="{ row }">{{ row.timeout_seconds }} с</template></el-table-column>
        <el-table-column label="Действия" width="190"><template #default="{ row }"><el-button link @click="editRoute(row)">Изменить</el-button><el-button link type="danger" :loading="deletingId === row.id" @click="deleteRoute(row)">Удалить</el-button></template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { evaluationApi } from '../api'

const routes = ref([])
const loading = ref(false)
const saving = ref(false)
const deletingId = ref('')
const loadingCatalog = ref(false)
const error = ref('')
const catalogError = ref('')
const message = ref('')
const editingId = ref('')
const provider = ref('offline')
const freeOnly = ref(true)
const drafts = reactive({
  offline: { model: 'deterministic', secretName: '', timeout: 60 },
  google: { model: 'gemini-3.6-flash', secretName: 'GOOGLE_API_KEY', timeout: 60 },
  openrouter: { model: 'openrouter/free', secretName: 'OPENROUTER_API_KEY', timeout: 60 },
  crt_mko: { model: '', secretName: '', timeout: 120, allowHttp: false, baseUrl: '' },
})
const catalogs = reactive({ google: [], openrouter: [], crt_mko: [] })
const activeDraft = computed(() => drafts[provider.value])
const visibleCatalog = computed(() => provider.value === 'openrouter' && freeOnly.value ? catalogs.openrouter.filter((model) => model.is_free) : (catalogs[provider.value] || []))

const providerMessages = {
  credential_unavailable: 'Ключ не найден. Проверьте имя переменной окружения.',
  http_429: 'Провайдер временно ограничил запросы.',
  network_error: 'Не удалось связаться с провайдером.',
}
function explain(cause, fallback) {
  const detail = cause.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.code && providerMessages[detail.code]) return providerMessages[detail.code]
  if (detail?.message) return detail.message
  return cause.message || fallback
}
function credentialRef() {
  if (['offline', 'crt_mko'].includes(provider.value)) return null
  const name = activeDraft.value.secretName.trim()
  if (!/^[A-Z][A-Z0-9_]*$/.test(name)) throw new Error('Имя переменной должно состоять из заглавных латинских букв, цифр и _')
  return 'env:' + name
}
async function loadRoutes() {
  loading.value = true
  error.value = ''
  try { routes.value = (await evaluationApi.listRoutes()).data }
  catch (cause) { error.value = explain(cause, 'Не удалось загрузить модели') }
  finally { loading.value = false }
}
let catalogGeneration = 0
function endpointChanged() { catalogGeneration += 1; catalogs.crt_mko = []; drafts.crt_mko.allowHttp = false; catalogError.value = '' }
function endpointOptions() {
  if (provider.value !== 'crt_mko') return {}
  let url
  try { url = new URL(activeDraft.value.baseUrl.trim()) } catch { throw new Error('Укажите полный адрес API ЦРТ МКО.') }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('Нужен HTTP/HTTPS адрес без логина, пароля и параметров.')
  if (url.protocol === 'http:' && !activeDraft.value.allowHttp) throw new Error('Подтвердите передачу текстов по HTTP.')
  return { base_url: activeDraft.value.baseUrl.trim().replace(/\/+$/, ''), allow_insecure_http: url.protocol === 'http:' && activeDraft.value.allowHttp }
}
async function loadCatalog() {
  const generation = ++catalogGeneration
  catalogError.value = ''
  if (provider.value === 'offline') return
  if (provider.value === 'crt_mko' && !activeDraft.value.baseUrl.trim()) return
  const name = activeDraft.value.secretName.trim()
  if (provider.value !== 'crt_mko' && !/^[A-Z][A-Z0-9_]*$/.test(name)) { catalogError.value = 'Сначала укажите корректное имя переменной окружения.'; return }
  loadingCatalog.value = true
  try {
    const selectedProvider = provider.value
    const rows = (await evaluationApi.listProviderModels(selectedProvider, selectedProvider === 'crt_mko' ? undefined : 'env:' + name, endpointOptions())).data
    if (generation !== catalogGeneration) return
    catalogs[selectedProvider] = rows
    if (!drafts[selectedProvider].model && catalogs[selectedProvider].length) drafts[selectedProvider].model = catalogs[selectedProvider][0].id
  } catch (cause) { catalogError.value = explain(cause, 'Не удалось загрузить каталог; identifier можно ввести вручную.') }
  finally { loadingCatalog.value = false }
}
async function saveRoute() {
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    if (!activeDraft.value.model.trim()) throw new Error('Укажите модель')
    const endpoint = endpointOptions()
    const payload = { provider_name: provider.value, model_identifier: activeDraft.value.model.trim(), capabilities: { modalities: ['text'], ...endpoint }, credential_ref: credentialRef(), timeout_seconds: activeDraft.value.timeout }
    const wasEditing = Boolean(editingId.value)
    const response = wasEditing ? await evaluationApi.updateRoute(editingId.value, payload) : await evaluationApi.createRoute(payload)
    editingId.value = ''
    message.value = (wasEditing ? 'Подключение обновлено: ' : 'Подключение сохранено: ') + response.data.provider_name + ' / ' + response.data.model_identifier
    await loadRoutes()
  } catch (cause) { error.value = explain(cause, 'Не удалось сохранить подключение') }
  finally { saving.value = false }
}
async function editRoute(route) {
  provider.value = route.provider_name.toLowerCase()
  if (!drafts[provider.value]) return
  drafts[provider.value].model = route.model_identifier
  drafts[provider.value].secretName = route.credential_ref?.replace(/^env:/, '') || ''
  drafts[provider.value].timeout = route.timeout_seconds || 60
  if (provider.value === 'crt_mko') { drafts.crt_mko.allowHttp = route.capabilities_json?.allow_insecure_http === true; drafts.crt_mko.baseUrl = route.capabilities_json?.base_url || '' }
  editingId.value = route.id
  message.value = ''
  await loadCatalog()
}
function cancelEdit() { editingId.value = ''; message.value = 'Изменение отменено.' }
async function deleteRoute(route) {
  try { await ElMessageBox.confirm('Удалить ' + route.provider_name + ' / ' + route.model_identifier + '? Прошлые RunSnapshot останутся доступны.', 'Удаление подключения', { confirmButtonText: 'Удалить', cancelButtonText: 'Отмена', type: 'warning' }) }
  catch { return }
  deletingId.value = route.id
  error.value = ''
  try {
    await evaluationApi.deleteRoute(route.id)
    if (editingId.value === route.id) editingId.value = ''
    message.value = 'Подключение удалено. История запусков не изменена.'
    await loadRoutes()
  } catch (cause) { error.value = explain(cause, 'Не удалось удалить подключение') }
  finally { deletingId.value = '' }
}

onMounted(loadRoutes)
</script>

<style scoped>
.models-view { max-width: 1100px; margin: 0 auto; }
.space { margin-top: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.hint, .field-help { color: var(--el-text-color-secondary); font-weight: normal; }
.hint { margin-top: 4px; }
.field-help { display: block; font-size: 12px; margin-top: 6px; }
.route-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
.route-form :deep(.el-select), .route-form :deep(.el-input) { width: 100%; }
.model-picker { display: flex; gap: 8px; width: 100%; }
.model-picker :deep(.el-select) { flex: 1; }
@media (max-width: 760px) { .route-form { grid-template-columns: 1fr; } }
</style>
