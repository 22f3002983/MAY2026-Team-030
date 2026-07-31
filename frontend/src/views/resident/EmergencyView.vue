<script setup>
import { ref, onMounted } from 'vue'   // CHANGED — added onMounted
import { useAuthStore } from '../../stores/auth'
import api from '../../api/axios'

const auth        = useAuthStore()
const showConfirm = ref(false)
const alertSent   = ref(false)
const sosError    = ref('')
const sending      = ref(false)
const alertHistory   = ref([])
const historyLoading = ref(true)

const contacts = [
  { label: 'Security — Gate 1',  num: '+91 91234 00001', icon: '🛡', tint: '#0A4174' },
  { label: 'Society Secretary',  num: '+91 98765 40002', icon: '👤', tint: '#4E8EA2' },
  { label: 'Ambulance',          num: '108',             icon: '📞', tint: '#C43D3D' },
  { label: 'Fire Brigade',       num: '101',             icon: '🚨', tint: '#E0A030' },
]

onMounted(fetchAlerts)   // MOVED — now after fetchAlerts is declared below (hoisting still works either way, but this reads cleaner)

function triggerSOS() {
  showConfirm.value = true
}

async function confirmSOS() {
  sosError.value = ''
  sending.value  = true
  try {
    await api.post('/emergency', {
      type:    'Public',
      message: `SOS triggered by ${auth.name} — Flat ${auth.flatNumber}. Please respond immediately.`,
      severity: 'critical',
    })
    showConfirm.value = false
    alertSent.value   = true
    await fetchAlerts()   // ADDED — refresh "Your alerts" right after sending
    setTimeout(() => alertSent.value = false, 5000)
  } catch (err) {
    sosError.value = err.response?.data?.error || 'Failed to send SOS. Try again.'
  } finally {
    sending.value = false
  }
}   // FIXED — confirmSOS now closes properly here

async function fetchAlerts() {
  historyLoading.value = true
  try {
    const response = await api.get('/emergency')
    alertHistory.value = response.data.alerts.map(a => ({
      id:         a.id,
      type:       a.type,
      msg:        a.message,
      time:       formatTime(a.created_at),
      by:         a.created_by_name || 'Unknown',
      status:     a.status,
      resolvedAt: a.resolved_at,
      resolvedBy: a.resolved_by_name,
    }))
  } catch (err) {
    console.error('Failed to load alert history')
  } finally {
    historyLoading.value = false
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}
</script>   // NO stray trailing } before this

<template>
  <div class="emergency-view">

    <div class="page-header">
      <div>
        <h2>Emergency</h2>
        <p class="page-sub">Alert security and the secretary instantly</p>
      </div>
    </div>

    <!-- alert sent banner -->
    <div v-if="alertSent" class="alert-banner">
      🚨 SOS sent — Security and the secretary have been notified. Help is on the way.
    </div>

    <div class="two-col">

      <!-- left - SOS button -->
      <div class="sos-panel">
        <h3 class="sos-title">Emergency SOS</h3>
        <p class="sos-sub">
          Press to alert security and the secretary with your flat number instantly.
        </p>

        <div class="sos-btn-wrap">
          <button class="sos-btn" @click="triggerSOS">
            SOS
          </button>
        </div>

        <p class="sos-flat">Flat {{ auth.flatNumber }} · {{ auth.name }}</p>
      </div>

      <!-- right - emergency contacts -->
      <div class="contacts-panel">
        <h3 class="contacts-title">Emergency contacts</h3>
        <div class="contacts-list">
          <div
            v-for="contact in contacts"
            :key="contact.label"
            class="contact-card"
          >
            <div class="contact-icon" :style="{ background: contact.tint }">
              {{ contact.icon }}
            </div>
            <div class="contact-info">
              <span class="contact-label">{{ contact.label }}</span>
              <span class="contact-num">{{ contact.num }}</span>
            </div>
            <a :href="'tel:' + contact.num" class="call-btn">📞</a>
          </div>
        </div>
      </div>

      <div class="panel">
        <h3 class="contacts-title">Your alerts</h3>
        <div class="history-list">
          <div v-for="(alert, i) in alertHistory" :key="i" class="history-item">
            <div class="history-meta">
              <span class="history-status" :class="alert.status === 'resolved' ? 'status-resolved' : 'status-active'">
                {{ alert.status === 'resolved' ? 'Resolved' : 'Active' }}
              </span>
              <span class="history-time">{{ alert.time }}</span>
            </div>
            <p class="history-msg">{{ alert.msg }}</p>
            <span v-if="alert.status === 'resolved'" class="history-resolved">
              Resolved by {{ alert.resolvedBy || 'Unknown' }} · {{ formatTime(alert.resolvedAt) }}
            </span>
          </div>
          <div v-if="historyLoading" class="empty-history">Loading...</div>
          <div v-else-if="alertHistory.length === 0" class="empty-history">No alerts yet</div>
        </div>
      </div>

    </div>

    <!-- confirm modal -->
    <div v-if="showConfirm" class="modal-overlay" @click.self="showConfirm = false">
      <div class="confirm-modal">

        <div class="confirm-icon">🚨</div>
        <h3 class="confirm-title">Send emergency alert?</h3>
        <p class="confirm-sub">
          This will immediately notify <strong>security and the secretary</strong>
          with your flat number. Use only for genuine emergencies.
        </p>

        <div class="confirm-preview">
          <p class="sos-flat">Flat {{ auth.flatNumber }} · {{ auth.name }}</p>— Flat A-402. Please respond immediately.
        </div>

        <p v-if="sosError" class="error-msg">{{ sosError }}</p>

        <div class="confirm-actions">
          <button class="cancel-btn" @click="showConfirm = false">Cancel</button>
          <button class="send-btn" @click="confirmSOS" :disabled="sending">
            {{ sending ? 'Sending...' : 'Yes, send now' }}
          </button>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.emergency-view {
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

.alert-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 20px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: start;
}

/* SOS panel */
.sos-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 30px;
  box-shadow: var(--shadow-xs);
  text-align: center;
}

.sos-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 8px;
}

.sos-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 28px;
  max-width: 300px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.5;
}

.sos-btn-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 22px;
}

.sos-btn {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #E8756F, #C43D3D);
  color: #fff;
  font-size: var(--font-size-2xl);
  font-weight: 800;
  box-shadow: 0 12px 30px rgba(196,61,61,0.35);
  animation: pulse 2s infinite;
  transition: opacity var(--transition-fast);
  position: relative; /* needed so the pulse rings below can wrap around it */
}

.sos-btn:hover { opacity: 0.9; }

.sos-btn::before,
.sos-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(196, 61, 61, 0.6);
  animation: sos-ring 2s ease-out infinite;
  pointer-events: none;
}

.sos-btn::after {
  animation-delay: 1s;
}

@keyframes sos-ring {
  0%   { transform: scale(1);   opacity: 0.7; }
  100% { transform: scale(1.6); opacity: 0;   }
}

@keyframes pulse {
  0%   { box-shadow: 0 12px 30px rgba(196,61,61,0.35); }
  50%  { box-shadow: 0 12px 46px rgba(196,61,61,0.55); }
  100% { box-shadow: 0 12px 30px rgba(196,61,61,0.35); }
}

.sos-flat {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* contacts panel */
.contacts-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.contacts-title {
  font-size: var(--font-size-md);
  font-weight: 800;
  color: var(--c-900);
}

.contacts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contact-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  gap: 14px;
}

.contact-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
}

.contact-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.contact-label {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-primary);
}

.contact-num {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.call-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: #E9F4FA;
  color: var(--c-800);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  text-decoration: none;
  transition: background var(--transition-fast);
}

.call-btn:hover { background: #D4EBF7; }

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

.send-btn {
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

.send-btn:hover { opacity: 0.9; }


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
  flex-wrap: wrap;
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

.history-by {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.history-msg {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.5;
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
.empty-history {
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
  text-align: center;
  padding: 24px 0;
}
</style>