import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {

  const user = ref(null)

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role || null)
  const name = computed(() => user.value?.name || '')

  function login(userData) {
    user.value = userData
    localStorage.setItem('niwaas_user', JSON.stringify(userData))
  }

  function logout() {
    user.value = null
    localStorage.removeItem('niwaas_user')
  }

  function restoreSession() {
    const saved = localStorage.getItem('niwaas_user')
    if (saved) user.value = JSON.parse(saved)
  }

  return { user, isLoggedIn, role, name, login, logout, restoreSession }
})