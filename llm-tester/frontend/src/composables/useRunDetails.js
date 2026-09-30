import { onBeforeUnmount, ref } from 'vue'
import { evaluationApi } from '../api'
import { explain } from '../utils/evaluationErrors'

const terminalStatuses = new Set(['completed', 'completed_with_errors', 'cancelled', 'failed'])

// One request pair at a time. A generation token discards responses from an old selection.
export function useRunDetails({ error, onUpdated = () => {} }) {
  const run = ref(null)
  const items = ref([])
  let timer
  let generation = 0
  let disposed = false

  function stopRunUpdates() {
    generation += 1
    clearTimeout(timer)
  }

  async function openRunDetails(id) {
    if (disposed) return
    stopRunUpdates()
    const current = generation
    run.value = null
    items.value = []
    error.value = ''
    if (!id) return

    async function refresh() {
      let finished = false
      try {
        const [runResponse, detailsResponse] = await Promise.all([
          evaluationApi.getRun(id), evaluationApi.getRunDetails(id),
        ])
        if (current !== generation) return
        run.value = runResponse.data
        items.value = detailsResponse.data
        error.value = ''
        finished = terminalStatuses.has(run.value.status)
        await onUpdated(run.value)
      } catch (cause) {
        if (current !== generation) return
        error.value = explain(cause, 'Не удалось обновить запуск. Повторяем запрос автоматически.')
        finished = [403, 404, 422].includes(cause.response?.status)
      } finally {
        if (current === generation && !finished) timer = setTimeout(refresh, 1000)
      }
    }
    await refresh()
  }

  onBeforeUnmount(() => { disposed = true; stopRunUpdates() })
  return { run, items, openRunDetails, stopRunUpdates }
}
