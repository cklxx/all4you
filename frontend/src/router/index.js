import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import DataManagement from '../pages/DataManagement.vue'
import Training from '../pages/Training.vue'
import Models from '../pages/Models.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/data',
    name: 'data',
    component: DataManagement
  },
  {
    path: '/training',
    name: 'training',
    component: Training
  },
  {
    path: '/models',
    name: 'models',
    component: Models
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
