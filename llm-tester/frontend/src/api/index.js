import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const providersApi = {
  getAll: () => api.get('/providers'),
  getById: (id) => api.get(`/providers/${id}`),
  create: (data) => api.post('/providers', data),
  update: (id, data) => api.put(`/providers/${id}`, data),
  delete: (id) => api.delete(`/providers/${id}`),
  test: (id) => api.post(`/providers/${id}/test`),
  validatePool: () => api.get('/providers/pool/validate'),
  getTypes: () => api.get('/providers/types'),
}

export const tasksApi = {
  getAll: () => api.get('/tasks'),
  getById: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  getTestCases: (taskId) => api.get(`/tasks/${taskId}/test-cases`),
  createTestCase: (taskId, data) => api.post(`/tasks/${taskId}/test-cases`, data),
  deleteTestCase: (id) => api.delete(`/tasks/test-cases/${id}`),
  runTest: (data, judgeModel) => api.post('/tasks/run', data, { params: { judge_model: judgeModel } }),
  getRuns: (params) => api.get('/tasks/runs', { params }),
  getRunById: (id) => api.get(`/tasks/runs/${id}`),
  getRunResults: (id) => api.get(`/tasks/runs/${id}/results`),
  exportResults: (id, format) => api.get(`/tasks/runs/${id}/export`, { 
    params: { format },
    responseType: 'blob',
  }),
}
