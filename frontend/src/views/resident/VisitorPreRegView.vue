<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'
import { digitsOnly, toStoredPhone, extractDigits } from '../../utils/phone'

const mode         = ref('Pre-register')
const visitorName  = ref('')
const phone        = ref('')   // 10 raw digits; +91 prefix is shown separately

const expectedDate = ref('')
const expectedTime = ref('')
const reason       = ref('')
const formError    = ref('')
const successMsg   = ref('')
const loading      = ref(false)

const visitors        = ref([])
const visitorsLoading  = ref(true)

const modes = ['Pre-register', 'Walk-in']
function onPhoneInput(e) {
  phone.value = e.target.value.replace(/\D/g, '').slice(0, 10)
}

// NOTE: the backend's POST /visitors route only accepts
// name / phone / expected_date / expected_time / reason / vehicle_number.
// There's no separate "walk-in" creation route, and the Visitor model has
// no expiry/duration field at all. So both modes hit the same endpoint —
// "Walk-in" just skips the date/time fields. If you want walk-ins to
// auto-expire, that needs a real column + logic on the backend; the
// duration buttons below are UI-only for now and aren't sent anywhere.
const walkinDurationOptions = [15, 30, 45, 60]
const walkinDuration = ref(15)

const showHistory  = ref(false)
const historyQuery = ref('')
const historyDate  = ref('')

const showRegenerate  = ref(false)
const regenerateQuery = ref('')

const listTab = ref('upcoming')
const listTabs = [
  { value: 'upcoming',    label: 'Upcoming' },
  { value: 'checked_in',  label: 'Checked In' },
  { value: 'active',      label: 'Active Passes' },
]

onMounted(async () => {
  await fetchVisitors()
})

async function fetchVisitors() {
  visitorsLoading.value = true
  try {
    const response = await api.get('/visitors')
    visitors.value = response.data.visitors || []
  } catch (err) {
    console.error('Failed to load visitors', err)
  } finally {
    visitorsLoading.value = false
  }
}

// ── status helpers, built only from real fields ──────────────

const STATUS_LABELS = {
  pre_registered: 'Expected',
  checked_in:     'Checked In',
  checked_out:    'Checked Out',
  rejected:       'Rejected',
  expired:        'Expired',
  revoked:        'Revoked',
}
const STATUS_CLASSES = {
  pre_registered: 'badge-expected',
  checked_in:     'badge-in',
  checked_out:    'badge-out',
  rejected:       'badge-rejected',
  expired:        'badge-expired',
  revoked:        'badge-revoked',
}

// revoked (resident-cancelled) and expired (timed out) are kept as two
// separate states so a resident can tell them apart at a glance — both
// stop the pass from working, but only one was a deliberate cancel.
function displayStatus(v) {
  if (v.revoked) return 'revoked'
  if (v.status === 'pre_registered' && v.is_expired) return 'expired'
  return v.status
}
function statusLabel(v) { return STATUS_LABELS[displayStatus(v)] || v.status }
function statusClass(v) { return STATUS_CLASSES[displayStatus(v)] || 'badge-out' }

function formatDate(dateStr) {
  if (!dateStr) return null
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}
function formatTime(timeStr) {
  if (!timeStr) return null
  return timeStr.slice(0, 5)
}
function formatDateTime(dtStr) {
  if (!dtStr) return ''
  return new Date(dtStr).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

// Distinct wording for each way a pass stops being usable, so "resident
// cancelled it" never looks the same as "it just ran out of time."
function expiryBadgeText(v) {
  if (v.revoked)  return `Revoked ${formatDateTime(v.revoked_at)}`
  if (!v.expires_at) return null
  if (v.is_expired) return `Expired ${formatDateTime(v.expires_at)}`
  return `Expires ${formatDateTime(v.expires_at)}`
}

function visitTypeLabel(v) {
  return v.visit_type === 'walk_in' ? 'Walk-in' : 'Pre-registered'
}

function visitorMeta(v) {
  const parts = []
  const d = formatDate(v.expected_date)
  const t = formatTime(v.expected_time)
  if (d) parts.push(t ? `${d}, ${t}` : d)
  if (v.reason) parts.push(v.reason)
  return parts.length ? parts.join(' · ') : 'No fixed date'
}

// ── tabs ───────────────────────────────────────────────────────

const upcoming = computed(() =>
  visitors.value.filter(v => v.status === 'pre_registered' && !v.is_expired)
)
const checkedIn = computed(() => visitors.value.filter(v => v.status === 'checked_in'))

// Security-flagged unregistered visitors waiting on this resident's
// approval. No separate fetch needed — these come back in the same
// GET /visitors response, just filtered by status.
const pendingApprovals = computed(() =>
  visitors.value.filter(v => v.status === 'awaiting_approval')
)

async function approveGateRequest(v) {
  try {
    await api.patch(`/visitors/${v.id}/approve`)
    await fetchVisitors()
  } catch (err) {
    formError.value = err.response?.data?.error || 'Could not approve visitor'
    setTimeout(() => formError.value = '', 5000)
  }
}

async function denyGateRequest(v) {
  try {
    await api.patch(`/visitors/${v.id}/deny`)
    await fetchVisitors()
  } catch (err) {
    formError.value = err.response?.data?.error || 'Could not deny visitor'
    setTimeout(() => formError.value = '', 5000)
  }
}

// "Active" = still usable right now: not expired, and not in a terminal
// rejected/checked_out state.
const activePasses = computed(() =>
  visitors.value.filter(v => !v.revoked && !v.is_expired && ['pre_registered', 'checked_in'].includes(v.status))
)

const visibleVisitors = computed(() => {
  if (listTab.value === 'upcoming')   return upcoming.value
  if (listTab.value === 'checked_in') return checkedIn.value
  return activePasses.value
})

// ── revoke ─────────────────────────────────────────────────────
// IMPORTANT: there is no /visitors/<id>/revoke route on the backend yet.
// reject_visitor exists but is security-only, so residents get a 403 if
// this hits that route. You'll need to add something like:
//
//   @visitors_bp.route('/<visitor_id>/revoke', methods=['PATCH'])
//   @login_required
//   def revoke_visitor(visitor_id):
//       if current_user.role != 'resident':
//           return jsonify({'error': 'Only residents can revoke their own passes'}), 403
//       visitor = Visitor.query.get_or_404(visitor_id)
//       if visitor.resident_id != current_user.resident.id:
//           return jsonify({'error': 'Not your visitor'}), 403
//       if visitor.status != 'pre_registered':
//           return jsonify({'error': 'Only an upcoming pass can be revoked'}), 400
//       visitor.status = 'rejected'
//       db.session.commit()
//       return jsonify({'message': 'Pass revoked', 'visitor': visitor_to_dict(visitor)}), 200
//
// Until that route exists this call will 404 and the catch below will
// surface a normal error message instead of silently breaking the page.
async function revokeCode(id) {
  try {
    await api.patch(`/visitors/${id}/revoke`)
    await fetchVisitors()
  } catch (err) {
    formError.value = err.response?.data?.error || 'Could not revoke pass — backend route may be missing'
    setTimeout(() => formError.value = '', 5000)
  }
}

// ── create / submit ───────────────────────────────────────────

async function submit() {
  formError.value = ''

  if (!visitorName.value.trim()) { formError.value = 'Visitor name is required'; return }
  if (phone.value && phone.value.length !== 10) { formError.value = 'Phone number must be 10 digits'; return }
  if (mode.value === 'Pre-register' && (!expectedDate.value || !expectedTime.value)) {
    formError.value = 'Expected date and time are required for pre-registration'; return
  }

  loading.value = true
  try {
    const response = await api.post('/visitors', {
      name: visitorName.value,
      phone: phone.value ? `+91-${phone.value}` : null,
      expected_date: mode.value === 'Pre-register' ? (expectedDate.value || null) : null,
      expected_time: mode.value === 'Pre-register' ? (expectedTime.value || null) : null,
      reason: reason.value || null,
      visit_type: mode.value === 'Pre-register' ? 'pre_registered' : 'walk_in',
      duration_minutes: mode.value === 'Walk-in' ? walkinDuration.value : null,
    })

    successMsg.value = `Gate pass ${response.data.pass_code} generated for ${visitorName.value}`
    visitorName.value = ''; phone.value = ''; expectedDate.value = ''; expectedTime.value = ''
    reason.value = ''; walkinDuration.value = 15

    setTimeout(() => successMsg.value = '', 5000)
    await fetchVisitors()
  } catch (err) {
    formError.value = err.response?.data?.error || 'Failed to register visitor'
  } finally {
    loading.value = false
  }
}

// ── search / regenerate ─────────────────────────────────────
// candidates for "generate again": passes that are done and unusable —
// rejected or expired. There's no "revoked" state distinct from
// rejected on the backend, so a revoked pass shows up here as Rejected.

const regenerateCandidates = computed(() => {
  const base = visitors.value.filter(v => ['rejected', 'expired', 'revoked'].includes(displayStatus(v)))
  if (!regenerateQuery.value.trim()) return base
  const q = regenerateQuery.value.toLowerCase()
  return base.filter(v => v.name.toLowerCase().includes(q))
})

function openRegenerate() { regenerateQuery.value = ''; showRegenerate.value = true }

function generatePassAgain(v) {
  mode.value = 'Pre-register'
  visitorName.value = v.name
  phone.value = extractDigits(v.phone)
  reason.value = v.reason || ''
  expectedDate.value = ''; expectedTime.value = ''
  showRegenerate.value = false
}

// ── history ────────────────────────────────────────────────
// Built from real timestamps only: created_at, check_in_time,
// check_out_time. No visit_log array exists on the model (one
// check-in/out pair per visitor row), so this is a single-entry log
// per visitor rather than a repeat-visit history.

const activityLog = computed(() => {
  const events = []
  visitors.value.forEach(v => {
    events.push({ type: 'pass_created', visitor: v.name, at: v.created_at })
    if (v.check_in_time)  events.push({ type: 'checked_in',  visitor: v.name, at: v.check_in_time })
    if (v.check_out_time) events.push({ type: 'checked_out', visitor: v.name, at: v.check_out_time })
    if (v.status === 'rejected') events.push({ type: 'rejected', visitor: v.name, at: v.check_in_time || v.created_at })
    if (v.revoked) events.push({ type: 'revoked', visitor: v.name, at: v.revoked_at })
  })
  return events.filter(e => e.at).sort((a, b) => new Date(b.at) - new Date(a.at))
})

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

const filteredHistory = computed(() => {
  return activityLog.value.filter(e => {
    const matchesName = !historyQuery.value || e.visitor.toLowerCase().includes(historyQuery.value.toLowerCase())
    const matchesDate = !historyDate.value || sameDay(new Date(e.at), new Date(historyDate.value + 'T00:00:00'))
    return matchesName && matchesDate
  })
})

function openHistory(name = '') { historyQuery.value = name; historyDate.value = ''; showHistory.value = true }

const EVENT_TEXT = {
  pass_created: e => `Pass created for ${e.visitor}`,
  checked_in:   e => `${e.visitor} checked in`,
  checked_out:  e => `${e.visitor} checked out`,
  rejected:     e => `${e.visitor}'s pass rejected`,
  revoked:      e => `${e.visitor}'s pass revoked`,
}
const EVENT_DOT_CLASS = { checked_in: 'dot-in', checked_out: 'dot-out', rejected: 'dot-revoked', revoked: 'dot-revoked' }
function eventText(e) { return EVENT_TEXT[e.type](e) }
function eventDotClass(type) { return EVENT_DOT_CLASS[type] || 'dot-created' }
</script>

<template>
  <div class="sec-visitors">

    <div class="page-header">
      <div>
        <h2>Visitors</h2>
        <p class="page-sub">Pre-register guests or log walk-in visitors</p>
      </div>
    </div>

    <div v-if="pendingApprovals.length" class="alerts-panel">
      <div v-for="v in pendingApprovals" :key="v.id" class="alert-row alert-unexpected">
        <div class="alert-info">
          <p class="alert-text"><strong>{{ v.name }}</strong> is at the gate — {{ v.reason }}</p>
          <span class="alert-time">{{ formatDateTime(v.created_at) }}</span>
        </div>
        <div class="alert-actions">
          <button class="btn-mini-primary" @click="approveGateRequest(v)">Approve</button>
          <button class="btn-mini" @click="denyGateRequest(v)">Deny</button>
        </div>
      </div>
    </div>

    <div class="layout">

      <div class="panel">
        <div class="mode-toggle">
          <button v-for="m in modes" :key="m" :class="['mode-btn', { active: mode === m }]" @click="mode = m">{{ m }}</button>
        </div>

        <div v-if="successMsg" class="success-banner">✓ {{ successMsg }}</div>

        <div class="field">
          <label>Visitor name</label>
          <input v-model="visitorName" type="text" placeholder="e.g. Rahul Verma" class="n-input" />
        </div>

        <div class="two-fields">
          <div class="field">
            <label>Phone</label>
            <div class="phone-input-wrap">
              <span class="phone-prefix">+91</span>
              <input
                :value="phone"
                @input="onPhoneInput"
                type="tel"
                inputmode="numeric"
                maxlength="10"
                placeholder="98xxxxxxxx"
                class="n-input phone-input"
              />
            </div>
          </div>
          <div class="field">
            <label>Flat</label>
            <input :value="'A-402'" disabled class="n-input n-disabled" />
          </div>
        </div>

        <div class="field">
          <label>Reason for visit</label>
          <input v-model="reason" type="text" placeholder="e.g. Guest, Doctor, Delivery" class="n-input" />
        </div>

        <template v-if="mode === 'Pre-register'">
          <div class="two-fields">
            <div class="field">
              <label>Expected date</label>
              <input v-model="expectedDate" type="date" class="n-input" />
            </div>
            <div class="field">
              <label>Expected time</label>
              <input v-model="expectedTime" type="time" class="n-input" />
            </div>
          </div>
        </template>

        <div v-if="mode === 'Walk-in'" class="field">
          <label>Pass valid for</label>
          <div class="duration-toggle">
            <button v-for="d in walkinDurationOptions" :key="d" :class="['duration-btn', { active: walkinDuration === d }]" @click="walkinDuration = d">{{ d }}m</button>
          </div>
          <p class="field-hint">Pass auto-expires this many minutes after check-in isn't required — it starts counting down as soon as it's generated.</p>
        </div>

        <p v-if="formError" class="error-msg">{{ formError }}</p>

        <button class="submit-btn" @click="submit" :disabled="loading">
          {{ loading ? 'Registering...' : (mode === 'Pre-register' ? 'Generate gate pass' : 'Log walk-in') }}
        </button>
      </div>

      <div class="visitors-right">
        <div class="list-header">
          <div class="list-tabs">
            <button v-for="t in listTabs" :key="t.value" :class="['list-tab', { active: listTab === t.value }]" @click="listTab = t.value">
              {{ t.label }}
              <span class="tab-count">{{ t.value === 'upcoming' ? upcoming.length : t.value === 'checked_in' ? checkedIn.length : activePasses.length }}</span>
            </button>
          </div>
          <div class="list-header-actions">
            <button class="btn-outline" @click="openRegenerate()">Search visitors</button>
            <button class="btn-outline" @click="openHistory()">View history</button>
          </div>
        </div>

        <div v-if="visitorsLoading" class="empty-state"><p>Loading...</p></div>

        <div v-else class="visitors-list">
          <div v-for="v in visibleVisitors" :key="v.id" class="visitor-card">
            <div class="visitor-avatar">{{ v.name.charAt(0) }}</div>

            <div class="visitor-info">
              <div class="visitor-top">
                <button class="visitor-name name-link" @click="openHistory(v.name)">{{ v.name }}</button>
                <span :class="['visit-type-tag', v.visit_type === 'walk_in' ? 'tag-walkin' : 'tag-prereg']">{{ visitTypeLabel(v) }}</span>
              </div>
              <span class="visitor-meta">{{ visitorMeta(v) }}</span>
              <div class="visitor-badges">
                <span :class="['badge', statusClass(v)]">{{ statusLabel(v) }}</span>
                <span v-if="expiryBadgeText(v)" class="badge-expiry">{{ expiryBadgeText(v) }}</span>
              </div>
            </div>

            <div class="visitor-actions">
              <span class="pass-code">{{ v.pass_code }}</span>
              <div class="action-row">
                <button
                  v-if="!v.revoked && !v.is_expired && v.status === 'pre_registered'"
                  class="revoke-btn"
                  @click="revokeCode(v.id)"
                >
                  Revoke
                </button>
              </div>
            </div>
          </div>

          <div v-if="visibleVisitors.length === 0" class="empty-state">
            <p>
              {{ listTab === 'upcoming' ? 'No upcoming visitors'
                  : listTab === 'checked_in' ? 'No one checked in right now'
                  : 'No active passes' }}
            </p>
          </div>
        </div>
      </div>

    </div>

    <div v-if="showHistory" class="modal-overlay" @click.self="showHistory = false">
      <div class="modal history-modal">
        <div class="modal-header">
          <h3>Visitor history</h3>
          <button class="close-btn" @click="showHistory = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="history-filters">
            <input v-model="historyQuery" type="text" placeholder="Search by visitor name..." class="n-input" />
            <input v-model="historyDate" type="date" class="n-input" />
          </div>
          <div class="history-list">
            <div v-for="(event, i) in filteredHistory" :key="i" class="history-row">
              <span :class="['history-dot', eventDotClass(event.type)]"></span>
              <div class="history-content">
                <span class="history-text">{{ eventText(event) }}</span>
                <span class="history-time">{{ formatDateTime(event.at) }}</span>
              </div>
            </div>
            <div v-if="filteredHistory.length === 0" class="empty-state"><p>No activity found</p></div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showRegenerate" class="modal-overlay" @click.self="showRegenerate = false">
      <div class="modal history-modal">
        <div class="modal-header">
          <h3>Search visitors</h3>
          <button class="close-btn" @click="showRegenerate = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="history-filters">
            <input v-model="regenerateQuery" type="text" placeholder="Search by visitor name..." class="n-input" />
          </div>
          <p class="field-hint" style="margin-bottom: 12px;">Showing visitors whose pass has been rejected/revoked or expired.</p>
          <div class="history-list">
            <div v-for="v in regenerateCandidates" :key="v.id" class="search-row">
              <div class="search-info">
                <span class="visitor-name">{{ v.name }}</span>
                <span class="visitor-meta">{{ visitorMeta(v) }}</span>
                <span :class="['badge', statusClass(v)]">{{ statusLabel(v) }}</span>
              </div>
              <button v-if="displayStatus(v) !== 'expired'" class="btn-mini-primary" @click="generatePassAgain(v)">Generate pass again</button>
            </div>
            <div v-if="regenerateCandidates.length === 0" class="empty-state"><p>No matching visitors</p></div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.sec-visitors { max-width: var(--content-max-width); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; gap: 12px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.btn-outline { height: 38px; padding: 0 16px; border-radius: var(--radius-md); border: 1.5px solid var(--color-border-soft); background: var(--color-surface); color: var(--c-800); font-size: var(--font-size-sm); font-weight: 700; white-space: nowrap; transition: all var(--transition-fast); }
.btn-outline:hover { border-color: var(--c-600); background: var(--color-bg); }

.alerts-panel { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.alert-row { display: flex; align-items: center; gap: 12px; border-radius: var(--radius-md); padding: 12px 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-left: 3px solid; }
.alert-unexpected { border-left-color: var(--color-info-text); }
.alert-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.alert-text { font-size: var(--font-size-sm); color: var(--color-text-primary); line-height: 1.4; }
.alert-time { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.alert-actions { display: flex; gap: 8px; flex-shrink: 0; }

.btn-mini-primary { height: 32px; padding: 0 12px; border-radius: var(--radius-sm); background: var(--c-800); color: #fff; font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; transition: background var(--transition-fast); flex-shrink: 0; }
.btn-mini-primary:hover { background: var(--c-900); }
.btn-mini { height: 32px; padding: 0 12px; border-radius: var(--radius-sm); border: 1.5px solid var(--color-border-soft); background: var(--color-surface); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 600; transition: all var(--transition-fast); }
.btn-mini:hover { border-color: var(--color-danger-text); color: var(--color-danger-text); }

.layout { display: grid; grid-template-columns: 340px 1fr; gap: 20px; align-items: start; }
.panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow-xs); }

.mode-toggle { display: flex; gap: 4px; background: var(--color-bg); border-radius: var(--radius-md); padding: 4px; margin-bottom: 16px; }
.mode-btn { flex: 1; height: 36px; border-radius: var(--radius-sm); font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-secondary); transition: all var(--transition-fast); }
.mode-btn.active { background: var(--color-surface); color: var(--c-800); box-shadow: var(--shadow-xs); }

.duration-toggle { display: flex; gap: 4px; background: var(--color-bg); border-radius: var(--radius-md); padding: 4px; }
.duration-btn { flex: 1; height: 34px; border-radius: var(--radius-sm); font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); transition: all var(--transition-fast); }
.duration-btn.active { background: var(--color-surface); color: var(--c-800); box-shadow: var(--shadow-xs); }

.field-hint { font-size: 11px; color: var(--color-text-muted); margin-top: 6px; }
.success-banner { background: var(--color-success-bg); color: var(--color-success-text); border: 1px solid var(--color-success); border-radius: var(--radius-md); padding: 10px 14px; font-size: var(--font-size-xs); font-weight: 600; margin-bottom: 14px; }

.field { margin-bottom: 14px; }
.field:last-of-type { margin-bottom: 0; }
label { display: block; font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800); margin-bottom: 6px; }
.n-input { width: 100%; height: 42px; padding: 0 12px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); font-size: var(--font-size-sm); background: var(--color-surface-soft); color: var(--color-text-primary); outline: none; font-family: var(--font-family); transition: border-color var(--transition-fast); }
.n-input:focus { border-color: var(--c-600); }
.n-disabled { background: var(--color-bg); color: var(--color-text-muted); cursor: not-allowed; }
.phone-input-wrap { display: flex; align-items: center; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); background: var(--color-surface-soft); overflow: hidden; transition: border-color var(--transition-fast); }
.phone-input-wrap:focus-within { border-color: var(--c-600); }
.phone-prefix { padding: 0 8px 0 12px; font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-muted); border-right: 1.5px solid var(--color-border-soft); height: 42px; display: flex; align-items: center; flex-shrink: 0; }
.phone-input { border: none; background: transparent; height: 42px; }
.two-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.two-fields .field { margin-bottom: 0; }
.error-msg { font-size: var(--font-size-xs); color: var(--color-danger); margin-top: 10px; }

.submit-btn { width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; box-shadow: var(--shadow-btn); transition: background var(--transition-fast); margin-top: 18px; }
.submit-btn:hover { background: var(--c-900); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.visitors-right { display: flex; flex-direction: column; }
.list-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.list-header-actions { display: flex; gap: 8px; }
.list-tabs { display: inline-flex; gap: 4px; background: var(--color-bg); border-radius: var(--radius-md); padding: 4px; }
.list-tab { display: flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border-radius: var(--radius-sm); font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-secondary); transition: all var(--transition-fast); }
.list-tab.active { background: var(--color-surface); color: var(--c-800); box-shadow: var(--shadow-xs); }
.tab-count { font-size: 10px; font-weight: 800; background: var(--c-700); color: #fff; padding: 1px 6px; border-radius: var(--radius-pill); }
.list-tab:not(.active) .tab-count { background: var(--color-border-soft); color: var(--color-text-muted); }

.visitors-list { display: flex; flex-direction: column; gap: 10px; }
.visitor-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 14px 16px; box-shadow: var(--shadow-xs); display: flex; align-items: flex-start; gap: 12px; transition: border-color var(--transition-fast); }
.visitor-card:hover { border-color: var(--color-border-soft); }
.visitor-avatar { width: 40px; height: 40px; flex-shrink: 0; border-radius: var(--radius-md); background: var(--c-500); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: var(--font-size-md); }

.visitor-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.visitor-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.visitor-name { font-size: var(--font-size-md); font-weight: 700; color: var(--color-text-primary); }
.name-link { background: none; border: none; padding: 0; cursor: pointer; text-align: left; }
.name-link:hover { text-decoration: underline; color: var(--c-700); }
.visitor-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.visitor-badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 2px; }

.visit-type-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; padding: 2px 7px; border-radius: var(--radius-pill); }
.tag-prereg { background: var(--color-bg); color: var(--color-text-muted); }
.tag-walkin { background: #FFF3E0; color: #B45309; }

.badge { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: var(--radius-pill); }
.badge-expected { background: var(--color-info-bg); color: var(--color-info-text); }
.badge-in       { background: var(--color-success-bg); color: var(--color-success-text); }
.badge-out      { background: var(--color-bg); color: var(--color-text-muted); }
.badge-rejected { background: var(--color-danger-bg); color: var(--color-danger-text); }
.badge-expired  { background: #FFF3E0; color: #B45309; }
.badge-revoked  { background: var(--color-danger-bg); color: var(--color-danger-text); }
.badge-expiry   { font-size: 11px; color: var(--color-text-muted); }

.visitor-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; flex-shrink: 0; }
.pass-code { font-family: ui-monospace, monospace; font-size: 12px; font-weight: 800; color: var(--c-800); background: #E9F4FA; padding: 4px 9px; border-radius: var(--radius-sm); letter-spacing: 0.5px; }
.action-row { display: flex; align-items: center; gap: 10px; }
.revoke-btn { height: 24px; padding: 0 9px; border-radius: var(--radius-sm); border: 1.5px solid var(--color-danger-text); background: transparent; color: var(--color-danger-text); font-size: 11px; font-weight: 700; transition: all var(--transition-fast); }
.revoke-btn:hover { background: var(--color-danger-bg); }

.empty-state { text-align: center; padding: 40px 20px; color: var(--color-text-muted); font-size: var(--font-size-sm); font-weight: 600; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); }
.modal { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 480px; max-height: 85vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 22px 14px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { font-size: var(--font-size-lg); font-weight: 700; }
.close-btn { width: 30px; height: 30px; border-radius: var(--radius-sm); background: var(--color-bg); color: var(--color-text-secondary); display: flex; align-items: center; justify-content: center; transition: background var(--transition-fast); }
.close-btn:hover { background: var(--color-border); }
.modal-body { padding: 18px 22px 22px; }

.history-filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.history-filters .n-input { flex: 1; min-width: 150px; height: 40px; }
.history-list { display: flex; flex-direction: column; max-height: 380px; overflow-y: auto; }
.history-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--color-border); }
.history-row:last-child { border-bottom: none; }
.history-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.dot-created { background: var(--c-600); }
.dot-in      { background: var(--color-success-text); }
.dot-out     { background: var(--color-info-text); }
.dot-revoked { background: var(--color-danger-text); }
.history-content { display: flex; flex-direction: column; gap: 2px; }
.history-text { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-primary); }
.history-time { font-size: 11px; color: var(--color-text-muted); }

.search-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--color-border); }
.search-row:last-child { border-bottom: none; }
.search-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }

@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
</style>