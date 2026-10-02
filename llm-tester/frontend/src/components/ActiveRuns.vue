<template>
  <aside v-if="active.length" class="active-runs" aria-label="Активные запуски">
    <b>Сейчас выполняются</b><span v-if="stale"> · Нет связи: показаны последние данные</span>
    <div class="active-list"><router-link v-for="run in active" :key="run.id" :to="'/runs/' + run.id"><span>{{ run.kind === 'evaluation' ? 'Оценка' : 'Генерация' }} · {{ run.id.slice(0, 8) }}</span><RunProgress :run="run" compact /></router-link></div>
  </aside>
</template>
<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { evaluationApi } from '../api'
import RunProgress from './RunProgress.vue'
const active = ref([]), stale = ref(false)
let timer, disposed = false
async function refresh() {
  try {
    const response = await evaluationApi.listRuns()
    if (disposed) return
    active.value = response.data.filter(run => ['queued', 'running', 'cancelling'].includes(run.status))
    stale.value = false
  } catch { if (!disposed) stale.value = true }
  finally { if (!disposed) timer = setTimeout(refresh, 2000) }
}
onMounted(refresh)
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
</script>
<style scoped>
.active-runs { margin-bottom: 16px; padding: 10px; border: 1px solid var(--el-color-primary-light-5); background: var(--el-bg-color); border-radius: 8px; }
.active-list { display: flex; gap: 12px; overflow-x: auto; max-height: 190px; }
a { flex: 0 0 280px; color: inherit; text-decoration: none; }
</style>
