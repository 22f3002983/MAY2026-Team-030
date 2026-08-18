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
    // localStorage only tells us who was logged in last time, not whether
    // the server-side session is still valid (it can expire, get wiped by
    // session_protection='strong', or be cleared server-side). Ask the
    // backend so isLoggedIn reflects the real session, not stale cache.
    try {
      const response = await api.get('/auth/me')
      user.value = response.data.user
      localStorage.setItem('niwaas_user', JSON.stringify(response.data.user))
    } catch (err) {
      user.value = null
      localStorage.removeItem('niwaas_user')
    }
  }

  function setUser(updatedUser) {
    user.value = updatedUser
    localStorage.setItem('niwaas_user', JSON.stringify(updatedUser))
  }

  return { user, isLoggedIn, role, name, flatNumber, login, logout, restoreSession, setUser }
})