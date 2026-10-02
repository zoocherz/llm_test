import { test, expect } from '@playwright/test'

const makeRun = (id, status) => ({
  id, status, created_at: '2026-09-18T10:00:00Z',
  progress_json: { total: 1, completed: status === 'completed' ? 1 : 0, failed: 0 },
  snapshot_json: { routes: [{ id: 'deleted-route', provider_name: 'offline', model_identifier: 'snapshot-model' }] },
})

async function mockLists(page) {
  await page.route('**/api/v1/runs/*/evaluations', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/v1/model-routes', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/v1/runs', (route) => route.fulfill({ json: [makeRun('run-a', 'running'), makeRun('run-b', 'completed')] }))
  await page.route('**/api/v1/runs/*/details', (route) => route.fulfill({ json: [] }))
}

test('history refreshes a running result, retries a network failure and stops at completion', async ({ page }) => {
  await mockLists(page)
  let calls = 0
  await page.route('**/api/v1/runs/run-a', (route) => {
    calls += 1
    if (calls === 2) return route.fulfill({ status: 503, json: { detail: 'temporary test failure' } })
    return route.fulfill({ json: makeRun('run-a', calls === 1 ? 'running' : 'completed') })
  })
  await page.goto('/runs/run-a')
  const status = page.locator('.el-descriptions')
  await expect(status.getByText('running', { exact: true })).toBeVisible()
  await expect(page.getByText('temporary test failure', { exact: true })).toBeVisible()
  await expect(status.getByText('completed', { exact: true })).toBeVisible()
  await expect(page.getByText('temporary test failure', { exact: true })).toHaveCount(0)
  await page.waitForTimeout(1500)
  expect(calls).toBe(3)
})

test('a late response cannot replace the newly selected run', async ({ page }) => {
  await mockLists(page)
  let releaseOldResponse
  const gate = new Promise((resolve) => { releaseOldResponse = resolve })
  let oldRequested = false
  await page.route('**/api/v1/runs/run-a', async (route) => {
    oldRequested = true
    await gate
    await route.fulfill({ json: makeRun('run-a', 'running') })
  })
  await page.route('**/api/v1/runs/run-b', (route) => route.fulfill({ json: makeRun('run-b', 'completed') }))
  await page.goto('/runs/run-a')
  await expect.poll(() => oldRequested).toBe(true)
  await page.locator('.runs-view .el-table').first().getByRole('row').filter({ hasText: 'run-b' }).click()
  await expect(page).toHaveURL(/\/runs\/run-b$/)
  await expect(page.locator('.el-card__header').getByText('Run run-b', { exact: true })).toBeVisible()
  releaseOldResponse()
  await page.waitForTimeout(1500)
  await expect(page.locator('.el-card__header').getByText('Run run-b', { exact: true })).toBeVisible()
  await expect(page.locator('.el-descriptions').getByText('completed', { exact: true })).toBeVisible()
})

test('leaving the runs section stops updates', async ({ page }) => {
  await mockLists(page)
  let calls = 0
  await page.route('**/api/v1/runs/run-a', (route) => {
    calls += 1
    return route.fulfill({ json: makeRun('run-a', 'running') })
  })
  await page.goto('/runs/run-a')
  await expect(page.locator('.el-descriptions').getByText('running', { exact: true })).toBeVisible()
  await page.getByRole('menuitem', { name: 'Датасеты', exact: true }).click()
  await expect(page).toHaveURL(/\/datasets$/)
  const afterLeaving = calls
  await page.waitForTimeout(1500)
  expect(calls).toBe(afterLeaving)
})


test('live progress is visible outside history and answers render as text', async ({ page }) => {
  await mockLists(page)
  const run = { ...makeRun('run-a', 'running'), kind: 'evaluation', progress_json: { total: 4, completed: 2, failed: 1, active_item_id: 'item-a', attempt: 2, http_attempt: 1, active_started_at: new Date().toISOString(), timeout_seconds: 120 } }
  const details = [{ id: 'item-a', dataset_item: { external_id: 'example-a' }, route_id: 'deleted-route', status: 'running', attempts: [{ id: 'attempt-a', route_snapshot_json: { http_attempts: 1 }, latency_ms: null }] }, { id: 'item-b', dataset_item: { external_id: 'example-b' }, route_id: 'deleted-route', status: 'completed', output_json: { text: 'first line\nsecond line', raw_text: '<thought>synthetic hidden reasoning</thought>first line\nsecond line' }, attempts: [] }]
  await page.route('**/api/v1/runs', route => route.fulfill({ json: [run] }))
  await page.route('**/api/v1/runs/run-a', route => route.fulfill({ json: run }))
  await page.route('**/api/v1/runs/run-a/details', route => route.fulfill({ json: details }))
  await page.goto('/runs/run-a')
  const progress = page.locator('.sticky-progress')
  await expect(progress.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
  await expect(progress).toContainText('попытка 2')
  await expect(page.locator('.row-spinner')).toHaveCount(1)
  await page.screenshot({ path: 'test-results/live-progress.png', fullPage: true })
  await page.getByRole('row').filter({ hasText: 'example-b' }).getByRole('button', { name: 'Открыть', exact: true }).click()
  await expect(page.locator('.answer-text')).toHaveText('first line\nsecond line')
  await expect(page.locator('.answer-text')).not.toContainText('thought')
  await page.locator('.el-drawer__close-btn').click()
  await page.getByRole('menuitem', { name: 'Модели', exact: true }).click()
  await expect(page.getByRole('complementary', { name: 'Активные запуски' })).toContainText('run-a')
  await expect(page.getByRole('complementary', { name: 'Активные запуски' }).getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
})
