import axios from 'axios'
const api = axios.create({ baseURL: '/api' })
export const providersApi = {
  getAll: () => api.get('/providers'), getById: (id) => api.get('/providers/' + id), create: (data) => api.post('/providers', data),
  update: (id, data) => api.put('/providers/' + id, data), delete: (id) => api.delete('/providers/' + id), test: (id) => api.post('/providers/' + id + '/test'),
  validatePool: () => api.get('/providers/pool/validate'), getTypes: () => api.get('/providers/types'),
}
export const tasksApi = {
  getAll: () => api.get('/tasks'), getById: (id) => api.get('/tasks/' + id), create: (data) => api.post('/tasks', data),
  update: (id, data) => api.put('/tasks/' + id, data), delete: (id) => api.delete('/tasks/' + id),
  getTestCases: (taskId) => api.get('/tasks/' + taskId + '/test-cases'), createTestCase: (taskId, data) => api.post('/tasks/' + taskId + '/test-cases', data),
  deleteTestCase: (id) => api.delete('/tasks/test-cases/' + id), runTest: (data, judgeModel) => api.post('/tasks/run', data, { params: { judge_model: judgeModel } }),
  getRuns: (params) => api.get('/tasks/runs', { params }), getRunById: (id) => api.get('/tasks/runs/' + id),
  getRunResults: (id) => api.get('/tasks/runs/' + id + '/results'), exportResults: (id, format) => api.get('/tasks/runs/' + id + '/export', { params: { format }, responseType: 'blob' }),
}
export const evaluationApi = {
  listProviderPresets: () => api.get('/v1/provider-presets'),
  previewPrompt: (data) => api.post('/v1/prompts:preview', data),
  createEvaluation: (id, data) => api.post('/v1/runs/' + id + '/evaluations', data),
  listEvaluations: (id) => api.get('/v1/runs/' + id + '/evaluations'),
  createDataset: (data) => api.post('/v1/datasets', data), createDatasetVersion: (datasetId, data) => api.post('/v1/datasets/' + datasetId + '/versions', data), listDatasetVersions: () => api.get('/v1/dataset-versions'),
  listDatasetItems: (id, params) => api.get('/v1/dataset-versions/' + id + '/items', { params }),
  previewItems: (data) => api.post('/v1/datasets/items:preview', data),
  previewImport: (file, mapping) => { const form = new FormData(); form.append('file', file); if (mapping) form.append('mapping_json', JSON.stringify(mapping)); return api.post('/v1/datasets/import:preview', form) },
  commitItems: (id, data) => api.post('/v1/datasets/' + id + '/items:commit', data),
  commitImport: (id, file, mapping) => { const form = new FormData(); form.append('file', file); if (mapping) form.append('mapping_json', JSON.stringify(mapping)); return api.post('/v1/datasets/' + id + '/items:import', form) },
  publishDataset: (id) => api.post('/v1/datasets/' + id + ':publish'),
  createPrompt: (data) => api.post('/v1/prompts', data), listPrompts: () => api.get('/v1/prompts'),
  createPipeline: (data) => api.post('/v1/pipelines', data), listPipelines: () => api.get('/v1/pipelines'),
  createRoute: (data) => api.post('/v1/model-routes', data), updateRoute: (id, data) => api.put('/v1/model-routes/' + id, data), deleteRoute: (id) => api.delete('/v1/model-routes/' + id),
  listRoutes: () => api.get('/v1/model-routes'), listProviderModels: (providerName, credentialRef, endpoint = {}) => api.get('/v1/provider-models', { params: { provider_name: providerName, credential_ref: credentialRef || undefined, ...endpoint } }),
  createSuite: (data) => api.post('/v1/evaluation-suites', data), listSuites: () => api.get('/v1/evaluation-suites'),
  estimateRun: (data) => api.post('/v1/runs:estimate', data), createRun: (data) => api.post('/v1/runs', data),
  listRuns: () => api.get('/v1/runs'), getRun: (id) => api.get('/v1/runs/' + id), getRunItems: (id) => api.get('/v1/runs/' + id + '/items'),
  getRunDetails: (id) => api.get('/v1/runs/' + id + '/details'),
  retryRun: (id, itemIds) => api.post('/v1/runs/' + id + ':retry', { item_ids: itemIds }),
  cancelRun: (id) => api.post('/v1/runs/' + id + ':cancel'),
  importPrompt: (data) => api.post('/v1/prompts:import', data),
  exportRun: (id, format) => api.get('/v1/runs/' + id + '/export', { params: { format }, responseType: 'blob' }),
}
