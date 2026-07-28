<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const API = 'http://127.0.0.1:5000/api'

async function loadVisitors() {
  const res = await fetch(`${API}/visitors`, { credentials: 'include' })
  const data = await res.json()
  // keep using your existing local 'visitors' ref, just refresh it from real data
  return data.visitors || []
}

const mode        = ref('Pre-register')
const visitorName = ref('')
const phone       = ref('')
const expectedDate = ref('')
const expectedTime = ref('')
const purpose     = ref('')
const formError   = ref('')
const successMsg  = ref('')

const modes = ['Pre-register', 'Walk-in']

const walkinDurationOptions = [15, 30, 45, 60]
const walkinDuration = ref(15)

const preregDurationOptions = [
  { value: 'day_of', label: 'Expected day only' },
  { value: 7,   label: '1 week' },
  { value: 14,  label: '2 weeks' },
  { value: 30,  label: '1 month' },
  { value: 90,  label: '3 months' },
  { value: 'custom', label: 'Custom date' },
]
const preregDuration = ref('day_of')
const customExpiryDate = ref('')

const editingId = ref(null)

const showHistory  = ref(false)
const historyQuery = ref('')
const historyDate  = ref('')

const showRegenerate  = ref(false)
const regenerateQuery = ref('')

// CHANGED: added an 'active' tab covering every pass that's still usable
// (expected, checked in, or checked-out-but-valid), separate from the
// narrower Upcoming/Checked In views.
const listTab = ref('upcoming')
const listTabs = [
  { value: 'upcoming',    label: 'Upcoming' },
  { value: 'checked_in',  label: 'Checked In' },
  { value: 'active',      label: 'Active Passes' },
]

let nextId = 7
function generateId() { return nextId++ }

// mock data - replace with API in Sprint 1
const visitors = ref([
  {
    id: 1, name: 'Rahul Verma', phone: '98••• 210', date: '1 Jul', time: '5:30 PM', flat: 'A-402',
    code: 'GATE-7712', status: 'expected', purpose: 'Guest', pass_type: 'pre_register',
    created_at: '2026-07-01T17:30:00', expiry_at: '2026-10-01T23:59:59',
    revoked: false, revoked_at: null, visit_log: [],
  },
  {
    id: 2, name: 'Swiggy Delivery', phone: '—', date: '1 Jul', time: '1:10 PM', flat: 'A-402',
    code: 'GATE-5521', status: 'checked_out', purpose: 'Food delivery', pass_type: 'walk_in',
    created_at: '2026-07-01T13:10:00', expiry_at: '2026-07-01T13:40:00',
    revoked: false, revoked_at: null,
    visit_log: [{ checked_in_at: '2026-07-01T13:12:00', checked_out_at: '2026-07-01T13:20:00' }],
  },
  {
    id: 3, name: 'Dr. Nair', phone: '99••• 004', date: '2 Jul', time: '11:00 AM', flat: 'A-402',
    code: 'GATE-8890', status: 'checked_out', purpose: 'Doctor visit', pass_type: 'pre_register',
    created_at: '2026-07-02T10:45:00', expiry_at: '2026-08-02T11:00:00',
    revoked: false, revoked_at: null,
    visit_log: [
      { checked_in_at: '2026-07-02T11:03:00', checked_out_at: '2026-07-02T11:40:00' },
      { checked_in_at: '2026-07-05T10:58:00', checked_out_at: '2026-07-05T11:20:00' },
    ],
  },
  {
    id: 4, name: 'Priya (sister)', phone: '90123 44556', date: '5 Jul', time: '10:00 AM', flat: 'A-402',
    code: 'GATE-2201', status: 'expected', purpose: 'Guest', pass_type: 'pre_register',
    created_at: '2026-07-04T09:00:00', expiry_at: '2026-10-05T23:59:00',
    revoked: true, revoked_at: '2026-07-06T09:00:00', visit_log: [],
  },
  {
    id: 5, name: 'Amit (cousin)', phone: '90554 33119', date: '3 Jul', time: '7:00 PM', flat: 'A-402',
    code: 'GATE-5520', status: 'expected', purpose: 'Guest', pass_type: 'pre_register',
    created_at: '2026-07-03T18:00:00', expiry_at: '2026-07-03T23:59:00', // no-show, never checked in
    revoked: false, revoked_at: null, visit_log: [],
  },
  {
    id: 6, name: 'Neha (cousin)', phone: '91234 56789', date: '16 Jul', time: '11:00 AM', flat: 'A-402',
    code: 'GATE-4477', status: 'expected', purpose: 'Guest', pass_type: 'pre_register',
    created_at: '2026-07-11T09:30:00', valid_from: '2026-07-16T00:00:00', expiry_at: '2026-07-16T23:59:59',
    revoked: false, revoked_at: null, visit_log: [],
  },
])

const securityAlerts = ref([
  {
    id: 1, type: 'unexpected', visitor_name: 'Unknown visitor', flat: 'A-402', time: '2:15 PM',
    note: 'At the gate without a pass, says they\'re here to see A-402.',
  },
])

function addMinutes(mins) { const d = new Date(); d.setMinutes(d.getMinutes() + mins); return d }
function addDays(days) { const d = new Date(); d.setDate(d.getDate() + days); return d }
function generateCode() { return 'GATE-' + (4000 + Math.floor(Math.random() * 900)) }

// passStatus = is the CODE itself usable right now? Internal only — drives
// Edit/Revoke/regenerate eligibility. Never rendered as its own badge.
function passStatus(v) {
  if (v.revoked) return 'revoked'
  if (v.valid_from && new Date() < new Date(v.valid_from)) return 'valid' // not open yet, but not broken
  if (new Date() > new Date(v.expiry_at)) return 'expired'
  return 'valid'
}

// FIX: single source of truth for what a resident actually SEES on a card.
// Layers revoked/expired on top of the raw workflow status, so there is
// exactly one badge, never two that can disagree.
function displayStatus(v) {
  if (v.revoked) return 'revoked'
  if (v.status === 'expected' && passStatus(v) === 'expired') return 'expired'
  return v.status // expected | checked_in | checked_out | rejected
}

const DISPLAY_LABELS = {
  expected: 'Expected', checked_in: 'Checked In', checked_out: 'Checked Out',
  rejected: 'Rejected', revoked: 'Revoked', expired: 'Expired',
}
const DISPLAY_CLASSES = {
  expected: 'badge-expected', checked_in: 'badge-in', checked_out: 'badge-out',
  rejected: 'badge-rejected', revoked: 'badge-revoked', expired: 'badge-expired',
}
function statusLabel(v) { return DISPLAY_LABELS[displayStatus(v)] }
function statusClass(v) { return DISPLAY_CLASSES[displayStatus(v)] }

function passTypeLabel(v) {
  return v.pass_type === 'pre_register' ? 'Pre-registered' : 'Walk-in'
}

function formatExpiry(v) {
  return new Date(v.expiry_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

// ADDED: single place for the "Opens X" / "Expires X" line, now shown
// consistently across Upcoming, Checked In, and Active Passes.
function expiryBadgeText(v) {
  if (v.valid_from && new Date() < new Date(v.valid_from)) {
    return `Opens ${new Date(v.valid_from).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`
  }
  return `Expires ${formatExpiry(v)}`
}

function formatShort(date) {
  if (!date) return ''
  return date.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

// CHANGED: Upcoming now shows only visitors who haven't arrived yet — no
// checked-in, no checked-out. Those live in their own tabs now.
const upcoming = computed(() =>
  visitors.value.filter(v => displayStatus(v) === 'expected')
)

const checkedIn = computed(() => visitors.value.filter(v => v.status === 'checked_in'))

// ADDED: Active Passes — every pass that's still usable right now (not
// revoked, not expired), regardless of where the visitor is in their visit.
// This is what gives residents a place to revoke a pass that isn't sitting
// in Upcoming anymore (e.g. a multi-entry pass mid-visit or checked out).
const activePasses = computed(() =>
  visitors.value.filter(v => passStatus(v) === 'valid')
)

const visibleVisitors = computed(() => {
  if (listTab.value === 'upcoming')   return upcoming.value
  if (listTab.value === 'checked_in') return checkedIn.value
  return activePasses.value
})

function revokeCode(id) {
  const v = visitors.value.find(v => v.id === id)
  if (v) { v.revoked = true; v.revoked_at = new Date().toISOString() }
}

function editVisitor(v) {
  editingId.value        = v.id
  mode.value              = 'Pre-register'
  visitorName.value       = v.name
  phone.value             = v.phone === '—' ? '' : v.phone
  purpose.value           = v.purpose
  expectedDate.value      = ''
  expectedTime.value      = ''
  preregDuration.value    = 'day_of'
  customExpiryDate.value  = ''
  formError.value         = ''
}

function cancelEdit() {
  editingId.value = null
  visitorName.value = ''
  phone.value = ''
  purpose.value = ''
  expectedDate.value = ''
  expectedTime.value = ''
  preregDuration.value = 'day_of'
  customExpiryDate.value = ''
  formError.value = ''
}

function dismissAlert(id) {
  securityAlerts.value = securityAlerts.value.filter(a => a.id !== id)
}

function approveUnexpected(alert) {
  visitors.value.unshift({
    id: generateId(), name: alert.visitor_name, phone: '—', date: 'Today', time: 'Now', flat: alert.flat,
    code: generateCode(), status: 'expected', purpose: 'Approved at gate', pass_type: 'walk_in',
    created_at: new Date().toISOString(), expiry_at: addMinutes(15).toISOString(),
    revoked: false, revoked_at: null, visit_log: [],
  })
  dismissAlert(alert.id)
}

async function submit() {
  formError.value = ''

  if (!visitorName.value.trim()) { formError.value = 'Visitor name is required'; return }
  if (mode.value === 'Pre-register' && preregDuration.value === 'day_of' && (!expectedDate.value || !expectedTime.value)) {
    formError.value = 'Expected date and time are required for a single-day pass'; return
  }
  if (mode.value === 'Pre-register' && preregDuration.value === 'custom' && !customExpiryDate.value) {
    formError.value = 'Please select a valid-until date'; return
  }

  let expiry_at
  if (mode.value === 'Walk-in') {
    expiry_at = addMinutes(walkinDuration.value)
  } else if (preregDuration.value === 'day_of') {
    expiry_at = new Date(expectedDate.value + 'T23:59:59')
  } else if (preregDuration.value === 'custom') {
    expiry_at = new Date(customExpiryDate.value + 'T23:59:59')
  } else {
    expiry_at = addDays(Number(preregDuration.value))
  }

  if (editingId.value) {
    const v = visitors.value.find(v => v.id === editingId.value)
    if (v) {
      v.name = visitorName.value
      v.phone = phone.value || '—'
      v.date = expectedDate.value || v.date
      v.time = expectedTime.value || v.time
      v.purpose = purpose.value || v.purpose
      v.expiry_at = expiry_at.toISOString()
    }
    successMsg.value = `Pass updated for ${visitorName.value}`
    editingId.value = null
  } else {
    const res = await fetch(`${API}/visitors`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: visitorName.value,
        phone: phone.value,
        expected_date: expectedDate.value || null,
        expected_time: expectedTime.value || null,
        reason: purpose.value,
      }),
    })
    const data = await res.json()
    successMsg.value = `Gate pass ${data.pass_code} generated for ${visitorName.value}`
    // refresh the list from real data instead of pushing a fake local object
    visitors.value = await loadVisitors()
  }
  visitorName.value = ''; phone.value = ''; expectedDate.value = ''; expectedTime.value = ''
  purpose.value = ''; walkinDuration.value = 15; preregDuration.value = 'day_of'; customExpiryDate.value = ''
  setTimeout(() => successMsg.value = '', 5000)
}

function visitorMeta(v) {
  if (v.date && v.date !== 'No fixed date') {
    return `${v.time ? `${v.date}, ${v.time}` : v.date} · ${v.purpose}`
  }
  return `No fixed date · ${v.purpose}`
}

// FIX: candidates now use displayStatus, matching the single badge shown
// everywhere else, instead of a second independent passStatus check
const regenerateCandidates = computed(() => {
  const base = visitors.value.filter(v =>
    v.pass_type === 'pre_register' &&
    (displayStatus(v) === 'revoked' || displayStatus(v) === 'expired')
  )
  if (!regenerateQuery.value.trim()) return base
  const q = regenerateQuery.value.toLowerCase()
  return base.filter(v => v.name.toLowerCase().includes(q))
})

function openRegenerate() { regenerateQuery.value = ''; showRegenerate.value = true }

function generatePassAgain(v) {
  editingId.value = null
  mode.value = 'Pre-register'
  visitorName.value = v.name
  phone.value = v.phone === '—' ? '' : v.phone
  purpose.value = v.purpose
  expectedDate.value = ''; expectedTime.value = ''
  preregDuration.value = 'day_of'; customExpiryDate.value = ''
  showRegenerate.value = false
}

const activityLog = computed(() => {
  const events = []
  visitors.value.forEach(v => {
    events.push({ type: 'pass_created', visitor: v.name, flat: v.flat, at: v.created_at })
    ;(v.visit_log || []).forEach(entry => {
      events.push({ type: 'checked_in', visitor: v.name, flat: v.flat, at: entry.checked_in_at })
      if (entry.checked_out_at) events.push({ type: 'checked_out', visitor: v.name, flat: v.flat, at: entry.checked_out_at })
    })
    if (v.revoked_at) events.push({ type: 'revoked', visitor: v.name, flat: v.flat, at: v.revoked_at })
  })
  return events.sort((a, b) => new Date(b.at) - new Date(a.at))
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
  pass_created: e => `Pass created for ${e.visitor} · ${e.flat}`,
  checked_in:   e => `${e.visitor} checked in · ${e.flat}`,
  checked_out:  e => `${e.visitor} checked out · ${e.flat}`,
  revoked:      e => `${e.visitor}'s pass revoked · ${e.flat}`,
}
const EVENT_DOT_CLASS = { checked_in: 'dot-in', checked_out: 'dot-out', revoked: 'dot-revoked' }
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

    <div v-if="securityAlerts.length" class="alerts-panel">
      <div v-for="alert in securityAlerts" :key="alert.id" class="alert-row alert-unexpected">
        <div class="alert-info">
          <p class="alert-text"><strong>{{ alert.visitor_name }}</strong> · {{ alert.flat }} — {{ alert.note }}</p>
          <span class="alert-time">{{ alert.time }}</span>
        </div>
        <div class="alert-actions">
          <button class="btn-mini-primary" @click="approveUnexpected(alert)">Approve</button>
          <button class="btn-mini" @click="dismissAlert(alert.id)">Deny</button>
        </div>
      </div>
    </div>

    <div class="layout">

      <div class="panel">
        <div class="mode-toggle">
          <button v-for="m in modes" :key="m" :class="['mode-btn', { active: mode === m }]" @click="mode = m">{{ m }}</button>
        </div>

        <div v-if="successMsg" class="success-banner">✓ {{ successMsg }}</div>
        <div v-if="editingId" class="edit-banner">
          Editing an existing pass.
          <button class="edit-cancel-link" @click="cancelEdit">Cancel</button>
        </div>

        <div class="field">
          <label>Visitor name</label>
          <input v-model="visitorName" type="text" placeholder="e.g. Rahul Verma" class="n-input" />
        </div>

        <div class="two-fields">
          <div class="field">
            <label>Phone</label>
            <input v-model="phone" type="text" placeholder="98xxx xxxxx" class="n-input" />
          </div>
          <div class="field">
            <label>Flat</label>
            <input :value="'A-402'" disabled class="n-input n-disabled" />
          </div>
        </div>

        <template v-if="mode === 'Pre-register'">
          <div class="field">
            <label>Purpose of visit</label>
            <input v-model="purpose" type="text" placeholder="e.g. Guest, Doctor, Delivery" class="n-input" />
          </div>

          <div class="two-fields">
            <div class="field">
              <label>Expected date {{ preregDuration !== 'day_of' ? '(optional)' : '' }}</label>
              <input v-model="expectedDate" type="date" class="n-input" />
            </div>
            <div class="field">
              <label>Expected time {{ preregDuration !== 'day_of' ? '(optional)' : '' }}</label>
              <input v-model="expectedTime" type="time" class="n-input" />
            </div>
          </div>

          <div class="field">
            <label>Pass validity</label>
            <select v-model="preregDuration" class="n-input">
              <option v-for="o in preregDurationOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
            <p class="field-hint">
              {{ preregDuration === 'day_of'
                  ? 'Single day — works only on the expected date above, any number of times that day.'
                  : 'Multi-entry — valid for repeat visits any day until it expires.' }}
            </p>
          </div>

          <div v-if="preregDuration === 'custom'" class="field">
            <label>Valid until</label>
            <input v-model="customExpiryDate" type="date" class="n-input" />
          </div>
        </template>

        <div v-if="mode === 'Walk-in'" class="field">
          <label>Pass valid for</label>
          <div class="duration-toggle">
            <button v-for="d in walkinDurationOptions" :key="d" :class="['duration-btn', { active: walkinDuration === d }]" @click="walkinDuration = d">{{ d }}m</button>
          </div>
        </div>

        <p v-if="formError" class="error-msg">{{ formError }}</p>

        <button class="submit-btn" @click="submit">
          {{ editingId ? 'Save changes' : (mode === 'Pre-register' ? 'Generate gate pass' : 'Log walk-in') }}
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

        <div class="visitors-list">
          <div v-for="v in visibleVisitors" :key="v.id" class="visitor-card">
            <div class="visitor-avatar">{{ v.name.charAt(0) }}</div>

            <div class="visitor-info">
              <div class="visitor-top">
                <button class="visitor-name name-link" @click="openHistory(v.name)">{{ v.name }}</button>
                <span class="pass-type-tag">{{ passTypeLabel(v) }}</span>
              </div>
              <span class="visitor-meta">{{ visitorMeta(v) }}</span>
              <div class="visitor-badges">
                <!-- FIX: exactly one status badge now, no contradiction possible -->
                <span :class="['badge', statusClass(v)]">{{ statusLabel(v) }}</span>
                <!-- CHANGED: expiry/opens line now shown on every tab (Upcoming,
                     Checked In, Active Passes), not just Upcoming -->
                <span v-if="!v.revoked" class="badge-expiry">{{ expiryBadgeText(v) }}</span>
              </div>
            </div>

            <div class="visitor-actions">
              <span class="pass-code">{{ v.code }}</span>
              <div class="action-row">
                <button v-if="listTab === 'upcoming' && displayStatus(v) === 'expected'" class="action-link" @click="editVisitor(v)">Edit</button>
                <!-- CHANGED: revoke now also available from the Active Passes tab,
                     for any pass that's still valid (expected, checked in, or
                     checked-out-but-valid), not just ones sitting in Upcoming -->
                <button v-if="passStatus(v) === 'valid' && (listTab === 'active' || displayStatus(v) === 'expected')" class="revoke-btn" @click="revokeCode(v.id)">Revoke</button>
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
                <span class="history-time">{{ formatShort(new Date(event.at)) }}</span>
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
          <p class="field-hint" style="margin-bottom: 12px;">Showing pre-registered visitors whose pass has been revoked or expired.</p>
          <div class="history-list">
            <div v-for="v in regenerateCandidates" :key="v.id" class="search-row">
              <div class="search-info">
                <span class="visitor-name">{{ v.name }}</span>
                <span class="visitor-meta">{{ visitorMeta(v) }}</span>
                <span :class="['badge', statusClass(v)]">{{ statusLabel(v) }}</span>
              </div>
              <button class="btn-mini-primary" @click="generatePassAgain(v)">Generate pass again</button>
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
.edit-banner { display: flex; align-items: center; justify-content: space-between; gap: 10px; background: var(--color-info-bg); color: var(--color-info-text); border: 1px solid var(--color-info-text); border-radius: var(--radius-md); padding: 10px 14px; font-size: var(--font-size-xs); font-weight: 600; margin-bottom: 14px; }
.edit-cancel-link { font-size: var(--font-size-xs); font-weight: 700; color: inherit; background: none; border: none; text-decoration: underline; cursor: pointer; }

.field { margin-bottom: 14px; }
.field:last-of-type { margin-bottom: 0; }
label { display: block; font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800); margin-bottom: 6px; }
.n-input { width: 100%; height: 42px; padding: 0 12px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); font-size: var(--font-size-sm); background: var(--color-surface-soft); color: var(--color-text-primary); outline: none; font-family: var(--font-family); transition: border-color var(--transition-fast); }
.n-input:focus { border-color: var(--c-600); }
.n-disabled { background: var(--color-bg); color: var(--color-text-muted); cursor: not-allowed; }
.two-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.two-fields .field { margin-bottom: 0; }
.error-msg { font-size: var(--font-size-xs); color: var(--color-danger); margin-top: 10px; }

.submit-btn { width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; box-shadow: var(--shadow-btn); transition: background var(--transition-fast); margin-top: 18px; }
.submit-btn:hover { background: var(--c-900); }

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
.pass-type-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; color: var(--color-text-muted); }
.visitor-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.visitor-badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 2px; }

.badge { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: var(--radius-pill); }
.badge-expected { background: var(--color-info-bg); color: var(--color-info-text); }
.badge-in       { background: var(--color-success-bg); color: var(--color-success-text); }
.badge-out      { background: var(--color-bg); color: var(--color-text-muted); }
.badge-rejected { background: var(--color-danger-bg); color: var(--color-danger-text); }
.badge-expired  { background: var(--color-danger-bg); color: var(--color-danger-text); }
.badge-revoked  { background: var(--color-danger-bg); color: var(--color-danger-text); }
.badge-expiry   { font-size: 11px; color: var(--color-text-muted); }

.visitor-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; flex-shrink: 0; }
.pass-code { font-family: ui-monospace, monospace; font-size: 12px; font-weight: 800; color: var(--c-800); background: #E9F4FA; padding: 4px 9px; border-radius: var(--radius-sm); letter-spacing: 0.5px; }
.action-row { display: flex; align-items: center; gap: 10px; }
.action-link { font-size: 11px; font-weight: 700; color: var(--c-700); background: none; border: none; cursor: pointer; padding: 0; }
.action-link:hover { text-decoration: underline; }
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