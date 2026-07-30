import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '../api/axios'

export const useAuthStore = defineStore('auth', () => {

  const user = ref(JSON.parse(localStorage.getItem('niwaas_user') || 'null'))

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role || null)
  const name = computed(() => user.value?.name || '')
  const flatNumber = computed(() => user.value?.flat_number || '')

  async function login(email, password, inviteCode = null) {
    const payload = { email, password }
    if (inviteCode) payload.invite_code = inviteCode

    const response = await api.post('/auth/login', payload)
    user.value = response.data.user
    localStorage.setItem('niwaas_user', JSON.stringify(response.data.user))
    return response.data.user
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch (err) {
      // even if API call fails, clear local state
    } finally {
      user.value = null
      localStorage.removeItem('niwaas_user')
    }
  }

  async function restoreSession() {
    const saved = localStorage.getItem('niwaas_user')
    if (saved) user.value = JSON.parse(saved)
  }

  function setUser(updatedUser) {
    user.value = updatedUser
    localStorage.setItem('niwaas_user', JSON.stringify(updatedUser))
  }

  return { user, isLoggedIn, role, name, flatNumber, login, logout, restoreSession, setUser }
})