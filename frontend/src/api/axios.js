import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:5000/api',
    withCredentials: true,       // sends session cookie with every request
    headers: {
        'Content-Type': 'application/json',
    },
})

// If the session expires mid-use (not just on page load), any protected
// call now comes back as 401 JSON (see backend unauthorized_handler)
// instead of a redirect. Catch it here so stale auth state gets cleared
// and the user is sent back to login, rather than components like
// NotificationBell silently failing forever on every poll.
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response && error.response.status === 401) {
            const { useAuthStore } = await import('../stores/auth')
            const auth = useAuthStore()
            if (auth.isLoggedIn) {
                auth.user = null
                localStorage.removeItem('niwaas_user')
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login'
                }
            }
        }
        return Promise.reject(error)
    }
)

export default api