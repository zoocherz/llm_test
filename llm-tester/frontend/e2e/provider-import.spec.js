import { test, expect } from '@playwright/test'

test('YAML import previews text without auto-saving service configuration', async ({ page, request }) => {
  const name = 'yaml-preview-' + Date.now()
  await page.goto('/experiments?view=settings')
  const editor = page.locator('.prompt-editor')
  await editor.locator('input[type=file]').setInputFiles({ name: 'prompt.yaml', mimeType: 'application/yaml', buffer: Buffer.from(`name: ${name}\nprompt: Summarize\ninstructions: Be brief\nengine: ignored\n`) })
  await expect(editor.getByRole('textbox', { name: 'Текст инструкции', exact: true })).toHaveValue('Summarize\n\nBe brief')
  await expect(editor.getByText(/Не применены поля: engine/)).toBeVisible()
  const prompts = await (await request.get('/api/v1/prompts')).json()
  expect(prompts.some(p => p.name === name)).toBeFalsy()
  await editor.getByRole('button', { name: 'Добавить подстановку текста датасета' }).click()
  await expect(editor.getByRole('textbox', { name: 'Текст инструкции', exact: true })).toHaveValue(/\{\{text\}\}/)
})

test('CRT catalog needs no key and saving requires explicit HTTP consent', async ({ page }) => {
  let saved
  await page.route('**/api/v1/provider-models?**', async route => {
    expect(route.request().url()).not.toContain('credential_ref')
    expect(new URL(route.request().url()).searchParams.get('base_url')).toBe('http://mko.test:8088/api/v1')
    await route.fulfill({ json: [{ id: 'synthetic-model', display_name: 'Synthetic model', is_free: null }] })
  })
  await page.route('**/api/v1/model-routes', async route => {
    if (route.request().method() === 'POST') { saved = route.request().postDataJSON(); await route.fulfill({ json: { ...saved, id: 'synthetic-route' } }) }
    else await route.fulfill({ json: [] })
  })
  await page.goto('/models')
  await page.locator('.route-form .el-select').first().click()
  await page.getByRole('option', { name: 'ЦРТ МКО — без авторизации' }).click()
  await page.getByRole('textbox', { name: 'Адрес API ЦРТ МКО', exact: true }).fill('http://mko.test:8088/api/v1')
  await page.locator('.model-picker .el-select').click()
  await page.locator('.model-picker input').fill('synthetic-model')
  await page.getByRole('option', { name: 'synthetic-model', exact: true }).click()
  await expect(page.getByText('Имя переменной с ключом', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText('Подтвердите передачу текстов по HTTP.', { exact: true })).toBeVisible()
  expect(saved).toBeUndefined()
  await page.getByText('Разрешаю передачу выбранных данных по HTTP', { exact: true }).click()
  await expect(page.getByRole('checkbox', { name: 'Разрешаю передачу выбранных данных по HTTP' })).toBeChecked()
  await page.getByRole('button', { name: 'Обновить список', exact: true }).click()
  await expect(page.locator('.model-picker')).toContainText('Synthetic model')
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText(/Подключение сохранено:/)).toBeVisible()
  expect(saved.credential_ref).toBeNull()
  expect(saved.capabilities.allow_insecure_http).toBe(true)
  expect(saved.provider_name).toBe('crt_mko')
  expect(saved.capabilities.base_url).toBe('http://mko.test:8088/api/v1')
})


test('CRT existing connection can switch server and use HTTPS without HTTP consent', async ({ page }) => {
  let saved
  const existing = { id: 'route-existing', provider_name: 'crt_mko', model_identifier: 'synthetic-model', capabilities_json: {}, timeout_seconds: 120, credential_available: true }
  await page.route('**/api/v1/model-routes', route => route.fulfill({ json: [existing] }))
  await page.route('**/api/v1/model-routes/route-existing', async route => { saved = route.request().postDataJSON(); await route.fulfill({ json: { ...saved, id: existing.id } }) })
  await page.route('**/api/v1/provider-models?**', route => route.fulfill({ json: [] }))
  await page.goto('/models')
  await page.getByRole('button', { name: 'Изменить', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Адрес API ЦРТ МКО', exact: true })).toHaveValue('')
  await page.getByRole('textbox', { name: 'Адрес API ЦРТ МКО', exact: true }).fill('https://other.test:9443/custom/api')
  await expect(page.getByRole('checkbox', { name: 'Разрешаю передачу выбранных данных по HTTP' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Сохранить изменения', exact: true }).click()
  await expect(page.getByText(/Подключение обновлено:/)).toBeVisible()
  expect(saved.capabilities.base_url).toBe('https://other.test:9443/custom/api')
  expect(saved.capabilities.allow_insecure_http).toBe(false)
})

test('all additional services expose configuration and preserve Yandex connection edits', async ({ page, request }) => {
  const presets = await (await request.get('/api/v1/provider-presets')).json()
  expect(presets).toHaveLength(12)
  let catalogCalls = 0
  let saved
  let rows = []
  await page.route('**/api/v1/provider-models?**', route => { catalogCalls++; return route.fulfill({ json: [] }) })
  await page.route('**/api/v1/model-routes', async route => {
    if (route.request().method() === 'POST') {
      saved = route.request().postDataJSON()
      rows = [{ ...saved, id: 'additional-test', capabilities_json: saved.capabilities }]
      await route.fulfill({ json: rows[0] })
    } else await route.fulfill({ json: rows })
  })
  await page.goto('/models')
  const selectProvider = async label => {
    await page.locator('.route-form .el-select').first().click()
    await page.getByRole('option', { name: label, exact: true }).click()
  }
  for (const preset of presets) {
    await selectProvider(preset.label)
    await expect(page.getByRole('textbox', { name: 'Имя переменной с ключом', exact: true })).toHaveValue(preset.secret_name)
    await expect(page.getByRole('textbox', { name: 'Адрес API сервиса', exact: true })).toHaveValue(preset.base_url)
    await expect(page.getByRole('button', { name: 'Обновить список', exact: true })).toHaveCount(preset.catalog ? 1 : 0)
  }
  expect(catalogCalls).toBe(0)
  await selectProvider('GigaChat')
  await expect(page.getByText('Тип ключа GigaChat', { exact: true })).toBeVisible()
  await expect(page.getByText('Scope GigaChat', { exact: true })).toBeVisible()
  await selectProvider('Yandex AI Studio')
  await page.getByRole('textbox', { name: 'Модель', exact: true }).fill('gpt://test-folder/test-model/latest')
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText('Укажите ID каталога Yandex Cloud.', { exact: true })).toBeVisible()
  expect(saved).toBeUndefined()
  await page.getByRole('textbox', { name: 'ID каталога Yandex Cloud', exact: true }).fill('test-folder')
  await page.getByRole('textbox', { name: 'Адрес API сервиса', exact: true }).fill('https://custom.test:9443/v1')
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText(/Подключение сохранено:/)).toBeVisible()
  expect(saved.credential_ref).toBe('env:YANDEX_API_KEY')
  expect(saved.capabilities.folder_id).toBe('test-folder')
  expect(saved.capabilities.base_url).toBe('https://custom.test:9443/v1')
  await selectProvider('OpenAI')
  await page.getByRole('button', { name: 'Изменить', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Адрес API сервиса', exact: true })).toHaveValue('https://custom.test:9443/v1')
  await expect(page.getByRole('textbox', { name: 'ID каталога Yandex Cloud', exact: true })).toHaveValue('test-folder')
  expect(catalogCalls).toBe(0)
})