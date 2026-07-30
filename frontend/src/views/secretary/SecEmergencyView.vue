<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/axios'

const emgType        = ref('Public')
const emgMsg         = ref('')
const showConfirm    = ref(false)
const formError      = ref('')
const sending        = ref(false)
const historyLoading = ref(true)

const typeOptions = [
  { value: 'Public',  label: 'Public',  sub: 'Notify everyone'              },
  { value: 'Private', label: 'Private', sub: 'Secretary + security only'    },
]

const alertHistory = ref([])
const resolvingId  = ref(null)
const resolveError = ref('')

onMounted(fetchAlerts)

async function resolveAlert(id) {
  resolveError.value = ''
  resolvingId.value  = id
  try {
    await api.patch(`/emergency/${id}/resolve`)
    await fetchAlerts()
  } catch (err) {
    resolveError.value = err.response?.data?.error || 'Failed to resolve alert'
  } finally {
    resolvingId.value = null
  }
}

async function fetchAlerts() {
  historyLoading.value = true
  try {
    const response = await api.get('/emergency')
    alertHistory.value = response.data.alerts.map(mapAlert)
  } catch (err) {
    console.error('Failed to load alert history')
  } finally {
    historyLoading.value = false
  }
}

function mapAlert(a) {
  return {
    id:          a.id,
    type:        a.type,
    msg:         a.message,
    time:        formatTime(a.created_at),
    by:          a.created_by_name || 'Unknown',
    status:      a.status,
    resolvedAt:  a.resolved_at,
    resolvedBy:  a.resolved_by_name || 'Unknown',
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

function openConfirm() {
  formError.value = ''
  if (!emgMsg.value.trim()) {
    formError.value = 'Please enter a message before sending'
    return
  }
  showConfirm.value = true
}

async function sendAlert() {
  formError.value = ''
  sending.value    = true
  try {
    await api.post('/emergency', {
      type:    emgType.value,
      message: emgMsg.value,
    })
    emgMsg.value      = ''
    showConfirm.value = false
    await fetchAlerts()
  } catch (err) {
    formError.value    = err.response?.data?.error || 'Failed to send alert'
    showConfirm.value  = false
  } finally {
    sending.value = false
  }
}

function accentColor(type) {
  return type === 'Public' ? '#0A4174' : '#8298AC'
}

function typeBadgeStyle(type) {
  return type === 'Public'
    ? { background: '#DBEAFE', color: '#1E40AF' }
    : { background: '#F3F4F6', color: '#6B7280' }
}
</script>

<template>
  <div class="sec-emergency">

    <div class="page-header">
      <div>
        <h2>Emergency Broadcast</h2>
        <p class="page-sub">Alert residents, security or both in one tap</p>
      </div>
    </div>

    <div class="two-col">

      <!-- left panel - broadcast form -->
      <div class="panel">
        <h3 class="panel-title">Emergency broadcast</h3>
        <p class="panel-sub">Alert residents, security or both in one tap.</p>

        <label>Who should be notified?</label>
        <div class="type-options">
          <button
            v-for="opt in typeOptions"
            :key="opt.value"
            :class="['type-btn', { active: emgType === opt.value }]"
            @click="emgType = opt.value"
          >
            {{ opt.label }}
            <span class="type-sub">{{ opt.sub }}</span>
          </button>
        </div>

        <label>Message</label>
        <textarea
          v-model="emgMsg"
          placeholder="e.g. Fire alarm in B-wing. Please evacuate calmly via the nearest staircase."
          class="emg-textarea"
        />

        <p v-if="formError" class="error-msg">{{ formError }}</p>

        <button class="send-btn" @click="openConfirm" :disabled="sending">
          🚨 Send emergency alert
        </button>
      </div>

      <!-- right panel - alert history -->
      <div class="panel">
        <h3 class="panel-title">Recent alerts</h3>
        <div class="history-list">
          <div
            v-for="(alert, i) in alertHistory"
            :key="i"
            class="history-item"
            :style="{ borderLeftColor: accentColor(alert.type) }"
          >
            <div class="history-meta">
              <span class="history-type" :style="typeBadgeStyle(alert.type)">
                {{ alert.type }}
              </span>
              <span
                class="history-status"
                :class="alert.status === 'resolved' ? 'status-resolved' : 'status-active'"
              >
                {{ alert.status === 'resolved' ? 'Resolved' : 'Active' }}
              </span>
              <span class="history-time">{{ alert.time }}</span>
            </div>
            <p class="history-msg">{{ alert.msg }}</p>
            <div class="history-footer">
              <span class="history-by">by {{ alert.by }}</span>
              <span v-if="alert.status === 'resolved'" class="history-resolved">
                Resolved {{ formatTime(alert.resolvedAt) }}
              </span>
              <button
                v-else
                class="resolve-btn"
                :disabled="resolvingId === alert.id"
                @click="resolveAlert(alert.id)"
              >
                {{ resolvingId === alert.id ? 'Resolving...' : 'Mark resolved' }}
              </button>
            </div>
          </div>

          <p v-if="resolveError" class="error-msg">{{ resolveError }}</p>
          <div v-if="historyLoading" class="empty-history">Loading...</div>
          <div v-else-if="alertHistory.length === 0" class="empty-history">
            No alerts sent yet
          </div>
        </div>
      </div>

    </div>

    <!-- confirm modal -->
    <div v-if="showConfirm" class="modal-overlay" @click.self="showConfirm = false">
      <div class="confirm-modal">

        <div class="confirm-icon">🚨</div>
        <h3 class="confirm-title">Send emergency alert?</h3>
        <p class="confirm-sub">
          This will immediately notify
          <strong>{{ emgType === 'Public' ? 'all residents, security and staff' : 'the secretary and security team' }}</strong>
          across Raghvendra Sai Society. Use only for genuine emergencies.
        </p>

        <div class="confirm-preview">{{ emgMsg }}</div>

        <div class="confirm-actions">
          <button class="cancel-btn" @click="showConfirm = false">Cancel</button>
          <button class="send-confirm-btn" @click="sendAlert" :disabled="sending">
            {{ sending ? 'Sending...' : 'Yes, send now' }}
          </button>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.sec-emergency {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: var(--font-size-3xl);
  font-weight: 800;
  letter-spacing: -0.4px;
}

.page-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-top: 4px;
}

.two-col {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 18px;
  align-items: start;
}

.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-xs);
}

.panel-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 2px;
}

.panel-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 20px;
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--c-800);
  margin-bottom: 9px;
}

.type-options {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.type-btn {
  flex: 1;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-bg);
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  transition: all var(--transition-fast);
}

.type-btn.active {
  border-color: var(--c-800);
  background: #EAF3FB;
  color: var(--c-800);
}

.type-sub {
  font-size: var(--font-size-xs);
  font-weight: 500;
  opacity: 0.75;
}

.emg-textarea {
  width: 100%;
  height: 96px;
  padding: 12px 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  resize: none;
  line-height: 1.5;
  font-family: var(--font-family);
  margin-bottom: 8px;
  transition: border-color var(--transition-fast);
}

.emg-textarea:focus { border-color: var(--c-600); }

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-bottom: 12px;
}

.send-btn {
  width: 100%;
  height: 52px;
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, #D45B5B, #B43333);
  color: #fff;
  font-size: var(--font-size-lg);
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  box-shadow: 0 8px 22px rgba(196,61,61,0.3);
  transition: opacity var(--transition-fast);
  margin-top: 4px;
}

.send-btn:hover { opacity: 0.9; }

/* history */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.history-item {
  border-left: 3px solid #ccc;
  padding: 4px 0 4px 13px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.history-type {
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
}

.history-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.history-msg {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.5;
  margin-bottom: 3px;
}

.history-by {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.history-status {
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
}

.status-active    { background: var(--color-danger-bg);  color: var(--color-danger-text);  }
.status-resolved  { background: var(--color-success-bg); color: var(--color-success-text); }

.history-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 4px;
}

.history-resolved {
  font-size: var(--font-size-xs);
  color: var(--color-success-text);
  font-weight: 600;
}

.resolve-btn {
  height: 26px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--c-700);
  background: transparent;
  color: var(--c-700);
  font-size: var(--font-size-xs);
  font-weight: 700;
  transition: all var(--transition-fast);
}

.resolve-btn:hover:not(:disabled) { background: var(--color-bg); }
.resolve-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.empty-history {
  text-align: center;
  padding: 24px 0;
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
}

/* confirm modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,29,57,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.confirm-modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: 28px;
  width: 100%;
  max-width: 420px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.confirm-icon {
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background: #FBE9E4;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.confirm-title {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--c-900);
}

.confirm-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.confirm-preview {
  width: 100%;
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 13px 15px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  text-align: left;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 12px;
  width: 100%;
  margin-top: 4px;
}

.cancel-btn {
  flex: 1;
  height: 46px;
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.cancel-btn:hover { background: var(--color-border); }

.send-confirm-btn {
  flex: 1;
  height: 46px;
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, #D45B5B, #B43333);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 800;
  box-shadow: 0 6px 16px rgba(196,61,61,0.3);
  transition: opacity var(--transition-fast);
}

.send-confirm-btn:hover { opacity: 0.9; }
</style>