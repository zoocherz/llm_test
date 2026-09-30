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
    await route.fulfill({ json: [{ id: 'synthetic-model', display_name: 'Synthetic model', is_free: null }] })
  })
  await page.route('**/api/v1/model-routes', async route => {
    if (route.request().method() === 'POST') { saved = route.request().postDataJSON(); await route.fulfill({ json: { ...saved, id: 'synthetic-route' } }) }
    else await route.fulfill({ json: [] })
  })
  await page.goto('/models')
  await page.locator('.route-form .el-select').first().click()
  await page.getByRole('option', { name: 'ЦРТ МКО — без авторизации' }).click()
  await expect(page.locator('.model-picker')).toContainText('Synthetic model')
  await expect(page.getByText('Имя переменной с ключом', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText('Подтвердите передачу текстов по HTTP.', { exact: true })).toBeVisible()
  expect(saved).toBeUndefined()
  await page.getByText('Разрешаю передачу выбранных данных по HTTP', { exact: true }).click()
  await expect(page.getByRole('checkbox', { name: 'Разрешаю передачу выбранных данных по HTTP' })).toBeChecked()
  await page.getByRole('button', { name: 'Сохранить подключение', exact: true }).click()
  await expect(page.getByText(/Подключение сохранено:/)).toBeVisible()
  expect(saved.credential_ref).toBeNull()
  expect(saved.capabilities.allow_insecure_http).toBe(true)
  expect(saved.provider_name).toBe('crt_mko')
})
