export const providerErrorMessages = {
  endpoint_required: 'Укажите адрес API ЦРТ МКО в подключении и создайте новый запуск. Старый snapshot не содержит адреса.',
  invalid_json: 'Сервис вернул не JSON: проверьте адрес API и журнал сервера.',
  provider_error: 'Сервис сообщил об ошибке внутри ответа HTTP 200. Проверьте журнал сервера.',
  invalid_judge_response: 'Судья вернул неверный JSON или оценки вне шкал критериев. Баллы не рассчитаны; см. ответ в истории попыток.',
  truncated_response: 'Ответ оборван по лимиту токенов. Создайте запуск с большим лимитом ответа.',
  blocked_response: 'Провайдер заблокировал ответ; оценка не вычислена.',
  credential_unavailable: 'Ключ не найден. Проверьте имя переменной окружения и перезапустите приложение.',
  http_402: 'Провайдер отклонил запрос: требуется пополнить баланс или включить биллинг (HTTP 402).',
  http_429: 'Провайдер временно ограничил запросы: исчерпана квота или превышен лимит (HTTP 429).',
  timeout: 'Провайдер не ответил вовремя. Повторите позже или увеличьте максимальное ожидание.',
  network_error: 'Не удалось связаться с провайдером. Проверьте сеть и повторите запуск.',
  invalid_response: 'Провайдер вернул ответ без ожидаемого текста.',
}
export function explain(cause, fallback) {
  const detail = cause?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const labels = { name: 'Название', template: 'Текст инструкции', definition: 'Схема обработки', criteria: 'Критерии', weight: 'Вес', quality_threshold: 'Порог', key: 'Код критерия' }
    return detail.map((item) => {
      const field = (item.loc || []).filter((part) => part !== 'body').map((part) => typeof part === 'number' ? String(part + 1) : labels[part] || part).join(' → ')
      const message = item.type === 'missing' ? 'Обязательное поле не заполнено.' : String(item.msg || 'Проверьте значение.').replace(/^Value error, /, '')
      return (field ? field + ': ' : '') + message
    }).join('; ')
  }
  if (detail?.code && providerErrorMessages[detail.code]) return providerErrorMessages[detail.code]
  return detail?.message || cause?.message || fallback
}
