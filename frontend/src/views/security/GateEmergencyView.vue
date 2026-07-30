<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

const selectedType   = ref(null)
const showConfirm    = ref(false)
const sending        = ref(false)
const sendError      = ref('')
const historyLoading = ref(true)
const resolvingId  = ref(null)
const resolveError = ref('')

// ADDED: optional context captured before sending — description only makes
// sense for 'Other' (the other types are already self-explanatory), location
// applies to every type since it always helps responders find the scene faster.
const otherDescription = ref('')
const locationTower = ref('')
const locationFloor = ref('')
const locationUnit  = ref('')

const alertTypes = [
  { label: 'Fire / Evacuate', icon: '🔥', bg: '#FBE9E4', color: '#B4442F', audience: 'all residents, security and staff'         },
  { label: 'Intruder',        icon: '🛡', bg: '#FBF1DE', color: '#9A6412', audience: 'the secretary and security team'            },
  { label: 'Medical',         icon: '📞', bg: '#E9F4FA', color: '#0A4174', audience: 'the secretary and security team'            },
  { label: 'Other',           icon: '🔔', bg: '#EAF0F4', color: '#49769F', audience: 'the secretary and security team'            },
]

// mock alert history - replace with API in Sprint 1
const alertHistory = ref([])

onMounted(fetchAlerts)

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
    id:          a.id,           // ADDED — needed to resolve
    type:        a.type,
    msg:         a.message,
    time:        formatTime(a.created_at),
    by:          a.created_by_name || 'Unknown',
    status:      a.status,               // ADDED
    resolvedAt:  a.resolved_at,          // ADDED
    resolvedBy:  a.resolved_by_name,     // ADDED
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

// ADDED: builds "Tower A, Floor 3, Unit 402" style fragment from whichever
// of the three optional fields were actually filled in
const locationText = computed(() => {
  const parts = []
  if (locationTower.value.trim()) parts.push(`Tower ${locationTower.value.trim()}`)
  if (locationFloor.value.trim()) parts.push(`Floor ${locationFloor.value.trim()}`)
  if (locationUnit.value.trim())  parts.push(`Unit ${locationUnit.value.trim()}`)
  return parts.join(', ')
})

// ADDED: message preview now reacts to description/location instead of being
// a fixed string, so what's shown before sending matches what actually sends
const previewText = computed(() => {
  if (!selectedType.value) return ''
  let msg = `${selectedType.value.label} alert raised from gate by security.`
  if (selectedType.value.label === 'Other' && otherDescription.value.trim()) {
    msg += ` ${otherDescription.value.trim()}.`
  }
  if (locationText.value) {
    msg += ` Location: ${locationText.value}.`
  }
  msg += ' Please respond immediately.'
  return msg
})

function openConfirm(type) {
  selectedType.value     = type
  otherDescription.value = ''
  locationTower.value    = ''
  locationFloor.value    = ''
  locationUnit.value     = ''
  showConfirm.value      = true
}

// ADDED: shared close/reset so Cancel and the overlay click both leave a
// clean slate for the next alert, instead of only resetting on next open
function closeConfirm() {
  showConfirm.value      = false
  selectedType.value     = null
  otherDescription.value = ''
  locationTower.value    = ''
  locationFloor.value    = ''
  locationUnit.value     = ''
  sendError.value        = ''
}

async function sendAlert() {
  sendError.value = ''
  sending.value   = true
  try {
    await api.post('/emergency', {
      type:    selectedType.value.label === 'Fire / Evacuate' ? 'Public' : 'Private',
      message: previewText.value,
    })
    await fetchAlerts()
    closeConfirm()
  } catch (err) {
    sendError.value = err.response?.data?.error || 'Failed to send alert'
  } finally {
    sending.value = false
  }
}
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

function accentColor(type) {
  return type === 'Public' ? '#0A4174' : '#8298AC'
}
</script>

<template>
  <div class="gate-emergency">

    <div class="page-header">
      <div>
        <h2>Emergency</h2>
        <p class="page-sub">Raise a gate alert or view recent alert history</p>
      </div>
    </div>

    <div class="two-col">

      <!-- left panel - raise alert -->
      <div class="panel">
        <h3 class="panel-title">Raise gate alert</h3>
        <div class="alert-grid">
          <button
            v-for="type in alertTypes"
            :key="type.label"
            class="alert-btn"
            :style="{ background: type.bg, color: type.color }"
            @click="openConfirm(type)"
          >
            <span class="alert-icon">{{ type.icon }}</span>
            {{ type.label }}
          </button>
        </div>
      </div>

      <!-- right panel - alert history -->
      <div class="panel">
        <h3 class="panel-title">Alert history</h3>
        <div class="history-list">
          <div
            v-for="(alert, i) in alertHistory"
            :key="i"
            class="history-item"
            :style="{ borderLeftColor: accentColor(alert.type) }"
          >
            <div class="history-meta">
              <span
                class="history-type"
                :style="{ background: alert.type === 'Public' ? '#DBEAFE' : '#F3F4F6', color: alert.type === 'Public' ? '#1E40AF' : '#6B7280' }"
              >
                {{ alert.type }}
              </span>
              <span class="history-time">{{ alert.time }}</span>
              <span class="history-by">by {{ alert.by }}</span>
            </div>
            <p class="history-msg">{{ alert.msg }}</p>
              <div class="history-footer">
                <span v-if="alert.status === 'resolved'" class="history-resolved">
                  Resolved by {{ alert.resolvedBy || 'Unknown' }} · {{ formatTime(alert.resolvedAt) }}
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

            <p v-if="resolveError" class="error-msg">{{ resolveError }}</p>
          </div>

          <div v-if="historyLoading" class="empty-history">Loading...</div>
          <div v-else-if="alertHistory.length === 0" class="empty-history">
            No alerts raised yet
          </div>
        </div>
      </div>

    </div>

    <!-- confirm modal -->
    <div v-if="showConfirm" class="modal-overlay" @click.self="closeConfirm">
      <div class="confirm-modal">

        <div class="confirm-icon">🚨</div>
        <h3 class="confirm-title">Send emergency alert?</h3>
        <p class="confirm-sub">
          This will immediately notify
          <strong>{{ selectedType?.audience }}</strong>
          across Raghvendra Sai Society. Use only for genuine emergencies.
        </p>

        <!-- ADDED: only for 'Other', since that type has no built-in context -->
        <div v-if="selectedType?.label === 'Other'" class="confirm-field">
          <label>Description <span class="optional">(optional)</span></label>
          <textarea
            v-model="otherDescription"
            class="n-textarea"
            rows="2"
            placeholder="Briefly describe what's happening..."
          ></textarea>
        </div>

        <!-- ADDED: optional location, shown for every alert type -->
        <div class="confirm-field">
          <label>Location <span class="optional">(optional)</span></label>
          <div class="location-grid">
            <input v-model="locationTower" type="text" placeholder="Tower" class="n-input-sm" />
            <input v-model="locationFloor" type="text" placeholder="Floor" class="n-input-sm" />
            <input v-model="locationUnit"  type="text" placeholder="Unit"  class="n-input-sm" />
          </div>
        </div>

        <div class="confirm-preview">
          {{ previewText }}
        </div>

        <p v-if="sendError" class="error-msg" style="width:100%; text-align:left;">{{ sendError }}</p>

        <div class="confirm-actions">
          <button class="cancel-btn" @click="closeConfirm">Cancel</button>
          <button class="send-btn" @click="sendAlert" :disabled="sending">
            {{ sending ? 'Sending...' : 'Yes, send now' }}
          </button>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.gate-emergency {
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
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: start;
}

.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-xs);
}

.panel-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 16px;
}

.alert-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.alert-btn {
  padding: 20px;
  border-radius: var(--radius-lg);
  font-weight: 800;
  font-size: var(--font-size-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  transition: opacity var(--transition-fast);
}

.alert-btn:hover { opacity: 0.85; }

.alert-icon { font-size: 28px; }

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
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
  text-align: center;
  padding: 24px 0;
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

/* ADDED: description + location fields inside the confirm modal */
.confirm-field {
  width: 100%;
  text-align: left;
}

.confirm-field label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
  margin-bottom: 6px;
}

.optional {
  font-weight: 500;
  color: var(--color-text-muted);
}

.n-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.n-textarea:focus { border-color: var(--c-600); }

.location-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.n-input-sm {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  font-family: var(--font-family);
  transition: border-color var(--transition-fast);
}

.n-input-sm:focus { border-color: var(--c-600); }

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
</style>