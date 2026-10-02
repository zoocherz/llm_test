<template>
  <section :class="['run-progress', { compact }]" aria-label="Прогресс запуска">
    <div class="progress-title"><span v-if="active" class="spinner" aria-hidden="true"></span><span v-else aria-hidden="true">{{ run.status === 'completed' ? '✓' : run.status === 'cancelled' ? '■' : '⚠' }}</span><b>{{ labels[run.status] || run.status }}</b><span v-if="!compact">· {{ run.snapshot_json?.kind === 'evaluation' || run.kind === 'evaluation' ? 'Оценка' : 'Генерация' }} {{ run.id?.slice(0, 8) }}</span></div>
    <el-progress :percentage="percentage" :status="barStatus" :stroke-width="compact ? 8 : 16" />
    <div class="counts">Обработано {{ completed }} / {{ total }} <span>✓ {{ Math.max(0, completed - failed) }}</span> <span :class="{ failures: failed }">⚠ {{ failed }}</span></div>
    <div v-if="active && progress.active_item_id" class="current">{{ activeLabel || 'Строка ' + progress.active_item_id.slice(0, 8) }} · попытка {{ progress.attempt || 1 }}<span v-if="progress.http_attempt"> · HTTP {{ progress.http_attempt }}</span><span v-if="!compact"> · ожидание {{ elapsed }} с / {{ progress.timeout_seconds }} с</span></div>
    <div v-else-if="active && !compact">{{ run.status === 'cancelling' ? 'Ожидаем завершения текущего запроса' : 'Ожидание обработки' }}</div>
    <small v-if="!compact">Процент обработанных строк; ошибки не означают успешный ответ.</small>
  </section>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
const props = defineProps({ run: { type: Object, required: true }, compact: Boolean, activeLabel: String })
const labels = { queued: 'В очереди', running: 'Выполняется', cancelling: 'Останавливается', completed: 'Завершён', completed_with_errors: 'Завершён с ошибками', failed: 'Ошибка', cancelled: 'Отменён' }
const progress = computed(() => props.run.progress_json || {})
const active = computed(() => ['queued', 'running', 'cancelling'].includes(props.run.status))
const total = computed(() => Number(progress.value.total || 0))
const completed = computed(() => Number(progress.value.completed || 0))
const failed = computed(() => Number(progress.value.failed || 0))
const percentage = computed(() => total.value ? Math.min(100, Math.floor(completed.value * 100 / total.value)) : 0)
const barStatus = computed(() => active.value ? undefined : props.run.status === 'completed' ? 'success' : props.run.status === 'cancelled' ? 'warning' : 'exception')
const now = ref(Date.now())
const elapsed = computed(() => Math.max(0, Math.floor((now.value - (Date.parse(progress.value.active_started_at) || now.value)) / 1000)))
let timer
onMounted(() => { if (!props.compact) timer = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => clearInterval(timer))
</script>
<style scoped>
.run-progress { padding: 12px; background: var(--el-bg-color); border: 1px solid var(--el-border-color); border-radius: 8px; }
.progress-title, .counts { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.counts, .current { margin: 6px 0; }
.failures { color: var(--el-color-danger); font-weight: bold; }
small { color: var(--el-text-color-secondary); }
.compact { padding: 6px; font-size: 12px; }
.spinner { width: 14px; height: 14px; border: 2px solid var(--el-border-color); border-top-color: var(--el-color-primary); border-radius: 50%; animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }
</style>
