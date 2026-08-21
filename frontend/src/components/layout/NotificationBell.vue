<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api/axios'

const notifications = ref([])
const unreadCount = ref(0)
const showPanel = ref(false)
const loading = ref(false)

async function fetchUnreadCount() {
  try {
    const res = await api.get('/notifications/unread-count')
    unreadCount.value = res.data.count
  } catch (err) {
    // non-blocking — badge just stays at whatever it last was
  }
}

async function fetchNotifications() {
  loading.value = true
  try {
    const res = await api.get('/notifications')
    notifications.value = res.data.notifications
  } catch (err) {
    // non-blocking
  } finally {
    loading.value = false
  }
}

async function togglePanel() {
  showPanel.value = !showPanel.value
  if (showPanel.value) {
    await fetchNotifications()
  }
}

async function markRead(n) {
  if (n.is_read) return
  // optimistic update
  n.is_read = true
  unreadCount.value = Math.max(0, unreadCount.value - 1)
  try {
    await api.patch(`/notifications/${n.id}/read`)
  } catch (err) {
    // revert on failure
    n.is_read = false
    unreadCount.value += 1
  }
}

async function markAllRead() {
  if (!unreadCount.value) return
  const previous = notifications.value.map(n => n.is_read)
  notifications.value.forEach(n => { n.is_read = true })
  unreadCount.value = 0
  try {
    await api.patch('/notifications/read-all')
  } catch (err) {
    // revert on failure
    notifications.value.forEach((n, i) => { n.is_read = previous[i] })
    await fetchUnreadCount()
  }
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const mins = Math.floor((Date.now() - d.getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

const hasUnread = computed(() => unreadCount.value > 0)

const POLL_INTERVAL_MS = 30000
let pollTimer = null

onMounted(() => {
  fetchUnreadCount()
  pollTimer = setInterval(() => {
    fetchUnreadCount()
    // if the panel is already open, keep its contents fresh too —
    // otherwise a resident staring at an open panel wouldn't see a
    // reminder that arrived while they had it open
    if (showPanel.value) fetchNotifications()
  }, POLL_INTERVAL_MS)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="bell-wrap">
    <button
      class="bell-btn"
      @click="togglePanel"
      :aria-label="hasUnread ? `Notifications, ${unreadCount} unread` : 'Notifications'"
    >
      🔔
      <span v-if="hasUnread" class="bell-badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <div v-if="showPanel" class="bell-overlay" @click="showPanel = false"></div>

    <div v-if="showPanel" class="bell-panel">
      <div class="bell-panel-header">
        <span class="bell-panel-title">Notifications</span>
        <button v-if="hasUnread" class="mark-all-btn" @click="markAllRead">Mark all read</button>
      </div>

      <div v-if="loading" class="bell-empty">Loading...</div>
      <div v-else-if="!notifications.length" class="bell-empty">No notifications yet</div>

      <div v-else class="bell-list">
        <button
          v-for="n in notifications"
          :key="n.id"
          class="bell-item"
          :class="{ unread: !n.is_read }"
          @click="markRead(n)"
        >
          <span class="bell-dot" v-if="!n.is_read"></span>
          <span class="bell-text">
            <span class="bell-message">{{ n.message }}</span>
            <span class="bell-time">{{ formatTime(n.created_at) }}</span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bell-wrap { position: relative; }

.bell-btn {
  position: relative;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--color-surface-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  transition: background var(--transition-fast);
}
.bell-btn:hover { background: var(--color-border); }

.bell-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  border: 2px solid var(--color-surface);
}

.bell-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-header, 10);
}

.bell-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 340px;
  max-height: 420px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: calc(var(--z-header, 10) + 1);
}

.bell-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.bell-panel-title { font-size: var(--font-size-md); font-weight: 800; color: var(--c-900); }

.mark-all-btn {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
}
.mark-all-btn:hover { text-decoration: underline; }

.bell-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.bell-list {
  overflow-y: auto;
}

.bell-item {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  transition: background var(--transition-fast);
}
.bell-item:last-child { border-bottom: none; }
.bell-item:hover { background: var(--color-surface-muted); }
.bell-item.unread { background: var(--color-info-bg); }
.bell-item.unread:hover { background: var(--color-info-bg); filter: brightness(0.97); }

.bell-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-600);
  flex-shrink: 0;
  margin-top: 6px;
}

.bell-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bell-message {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.bell-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
</style>