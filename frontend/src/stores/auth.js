import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '../api/axios'

export const useAuthStore = defineStore('auth', () => {

  const user = ref(JSON.parse(localStorage.getItem('niwaas_user') || 'null'))
  // tracks whether we've verified the session with the backend at least once
  // this app load — the router guard uses this to avoid re-awaiting a full
  // network round trip on every single navigation
  const sessionChecked = ref(false)
  // bumped by login/logout so an in-flight background restoreSession() from
  // an older navigation can detect it's stale and avoid overwriting newer
  // state (e.g. it resolves *after* the user has since logged out, and
  // would otherwise silently resurrect the cleared session)
  let sessionVersion = 0

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role || null)
  const name = computed(() => user.value?.name || '')
  const flatNumber = computed(() => user.value?.flat_number || '')

  async function login(email, password, inviteCode = null) {
    const payload = { email, password }
    if (inviteCode) payload.invite_code = inviteCode

    const response = await api.post('/auth/login', payload)
    sessionVersion++
    user.value = response.data.user
    localStorage.setItem('niwaas_user', JSON.stringify(response.data.user))
    return response.data.user
  }

  async function logout() {
    sessionVersion++
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
    const versionAtStart = sessionVersion
    try {
      const response = await api.get('/auth/me')
      // a login/logout happened while this request was in flight — that
      // newer state is authoritative, so don't stomp on it with a
      // response that was already out of date the moment it landed
      if (sessionVersion !== versionAtStart) return
      user.value = response.data.user
      localStorage.setItem('niwaas_user', JSON.stringify(response.data.user))
    } catch (err) {
      if (sessionVersion !== versionAtStart) return
      user.value = null
      localStorage.removeItem('niwaas_user')
    } finally {
      sessionChecked.value = true
    }
  }

  function setUser(updatedUser) {
    user.value = updatedUser
    localStorage.setItem('niwaas_user', JSON.stringify(updatedUser))
  }

  return { user, isLoggedIn, role, name, flatNumber, sessionChecked, login, logout, restoreSession, setUser }
})