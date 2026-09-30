import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  { path: '/', name: 'Home', component: () => import('../views/EvaluationWorkbenchView.vue') },
  { path: '/evaluation', redirect: '/experiments' },
  { path: '/experiments', name: 'Experiments', component: () => import('../views/EvaluationWorkbenchView.vue'), props: { experimentMode: true } },
  { path: '/datasets', name: 'Datasets', component: () => import('../views/DatasetsView.vue') },
  { path: '/models', name: 'Models', component: () => import('../views/ModelsView.vue') },
  { path: '/runs', name: 'Runs', component: () => import('../views/RunsView.vue') },
  { path: '/runs/:runId', name: 'RunDetails', component: () => import('../views/RunsView.vue') },
  { path: '/providers', redirect: '/legacy/providers' },
  { path: '/tasks', redirect: '/legacy/tasks' },
  { path: '/legacy/providers', name: 'LegacyProviders', component: () => import('../views/ProvidersView.vue') },
  { path: '/legacy/tasks', name: 'LegacyTasks', component: () => import('../views/TasksView.vue') },
  { path: '/legacy/test-runs', name: 'LegacyTestRuns', component: () => import('../views/TestRunsView.vue') },
]
export default createRouter({ history: createWebHistory(), routes })
