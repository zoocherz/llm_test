import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/providers',
  },
  {
    path: '/providers',
    name: 'Providers',
    component: () => import('../views/ProvidersView.vue'),
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/TasksView.vue'),
  },
  {
    path: '/runs',
    name: 'TestRuns',
    component: () => import('../views/TestRunsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
