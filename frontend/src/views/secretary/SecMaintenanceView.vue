<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

const dues = ref([])
const residents = ref([])
const funds = ref([])
const loading = ref(true)
const loadError = ref('')

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [duesRes, residentsRes, fundsRes] = await Promise.all([
      api.get('/dues'),
      api.get('/auth/residents'),
      api.get('/funds'),
    ])
    dues.value = duesRes.data.dues
    residents.value = residentsRes.data.residents
    funds.value = fundsRes.data.funds
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load dues data'
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

function residentById(id) {
  return residents.value.find(r => r.id === id)
}

// months that actually have dues generated, sorted ascending
const generatedMonths = computed(() => {
  const seen = new Map()
  dues.value.forEach(d => {
    if (!seen.has(d.month)) seen.set(d.month, d.month)
  })
  return Array.from(seen.keys()).sort()
})

// the real current calendar month, regardless of what's been generated
const realCurrentMonthISO = computed(() => {
  const now = new Date()
  return isoOf(now.getFullYear(), now.getMonth() + 1)
})

// dropdown options = every generated month, plus the real current month
// even if nothing's been generated for it yet (so "Viewing" always has
// a sane default and an empty state can be shown for it)
const months = computed(() => {
  const set = new Set(generatedMonths.value)
  set.add(realCurrentMonthISO.value)
  return Array.from(set).sort()
})

const selectedMonth = ref('')

const latestMonth = computed(() => generatedMonths.value[generatedMonths.value.length - 1])

const selectedMonthLabel = computed(() =>
  selectedMonth.value ? new Date(selectedMonth.value).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : ''
)

// tag shown next to the dropdown — reflects the real current month,
// not just whichever month happens to be the latest generated one
const isCurrentMonthSelected = computed(() => selectedMonth.value === realCurrentMonthISO.value)

const selectedMonthDues = computed(() =>
  dues.value.filter(d => d.month === selectedMonth.value)
)

function statusLabel(due) {
  if (due.status === 'paid') return 'Paid'
  if (due.status === 'overdue') return 'Overdue'
  return 'Pending'
}
function statusClass(due) { return 'status-' + due.status }

const pendingCount = computed(() => selectedMonthDues.value.filter(d => d.status === 'pending').length)
const overdueCount = computed(() => selectedMonthDues.value.filter(d => d.status === 'overdue').length)

const totalPendingAmount = computed(() =>
  selectedMonthDues.value.filter(d => d.status !== 'paid').reduce((s, d) => s + (d.amount_due - d.amount_paid), 0)
)
const totalCollectedThisMonth = computed(() =>
  selectedMonthDues.value.reduce((s, d) => s + d.amount_paid, 0)
)

function formatAmount(n) { return '₹' + n.toLocaleString('en-IN') }
function formatDate(iso) { return iso ? new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—' }

// ── mark paid ──────────────────────────────────────────────
const markingPaid = ref({})

async function markPaid(due) {
  markingPaid.value[due.id] = true
  try {
    const res = await api.patch(`/dues/${due.id}/pay`, { amount_paid: due.amount_due })
    Object.assign(due, res.data.due)
    showBanner(`Payment recorded for ${residentById(due.resident_id)?.name}`, 'success')
    await refreshFunds()
  } catch (err) {
    showBanner(err.response?.data?.error || 'Failed to record payment', 'warning')
  } finally {
    markingPaid.value[due.id] = false
  }
}

async function refreshFunds() {
  try {
    const res = await api.get('/funds')
    funds.value = res.data.funds
  } catch { /* non-blocking */ }
}

function downloadReceipt(due) {
  window.open(`${api.defaults.baseURL}/dues/${due.id}/receipt`, '_blank')
}

// ── generate dues ──────────────────────────────────────────
const showGenerateModal = ref(false)
const generateAmount = ref(2500)
const generateMonth = ref('') // yyyy-mm-dd, first of month
const generating = ref(false)

function pad2(n) { return String(n).padStart(2, '0') }

function isoOf(y, m) { return `${y}-${pad2(m)}-01` }

// earliest month, starting at the actual current calendar month, that
// doesn't already have dues generated — walks forward past any months
// that are already done instead of blindly assuming "latest + 1", so it
// also self-corrects if a month was skipped earlier
function suggestedGenerateMonth() {
  const now = new Date()
  let y = now.getFullYear()
  let m = now.getMonth() + 1

  while (months.value.includes(isoOf(y, m))) {
    m += 1
    if (m > 12) { m = 1; y += 1 }
  }
  return isoOf(y, m)
}

function onGenerateDuesClick() {
  generateAmount.value = 2500
  generateMonth.value = suggestedGenerateMonth()
  showGenerateModal.value = true
}

// true if the month currently picked in the modal already has dues —
// shown as an inline warning so repeated clicks can't silently sail
// past an already-generated month without the secretary noticing
const generateMonthAlreadyDone = computed(() =>
  !!generateMonth.value && months.value.includes(generateMonth.value)
)

async function confirmGenerateDues() {
  generating.value = true
  try {
    const res = await api.post('/dues/generate', {
      month: generateMonth.value,
      amount_due: generateAmount.value,
    })
    showGenerateModal.value = false
    showBanner(res.data.message, 'success')
    await loadAll()
    selectedMonth.value = generateMonth.value
  } catch (err) {
    showBanner(err.response?.data?.error || 'Failed to generate dues', 'warning')
  } finally {
    generating.value = false
  }
}

// ── reminder ───────────────────────────────────────────────
const showReminderConfirm = ref(false)
const sendingReminder = ref(false)

async function sendReminder() {
  sendingReminder.value = true
  try {
    const res = await api.post('/dues/reminder')
    showReminderConfirm.value = false
    showBanner(res.data.message, 'success')
  } catch (err) {
    showBanner(err.response?.data?.error || 'Failed to send reminders', 'warning')
  } finally {
    sendingReminder.value = false
  }
}

// ── banner ─────────────────────────────────────────────────
const bannerMessage = ref('')
const bannerType = ref('success')
let bannerTimer = null
function showBanner(msg, type = 'success') {
  bannerMessage.value = msg
  bannerType.value = type
  clearTimeout(bannerTimer)
  bannerTimer = setTimeout(() => bannerMessage.value = '', 4500)
}

// ── defaulters (past months) ──────────────────────────────
const defaultersByMonth = computed(() => {
  const pastMonths = months.value.slice(0, -1)
  return [...pastMonths].reverse().map(m => {
    const entries = dues.value
      .filter(d => d.month === m && d.status !== 'paid')
      .map(d => ({ ...d, resident: residentById(d.resident_id) }))
    const total = entries.reduce((s, e) => s + (e.amount_due - e.amount_paid), 0)
    return { month: m, entries, total }
  }).filter(g => g.entries.length > 0)
})

// ── resident profile ───────────────────────────────────────
const showProfileModal = ref(false)
const selectedResidentId = ref(null)

function openProfile(residentId) {
  selectedResidentId.value = residentId
  showProfileModal.value = true
}

const profileResident = computed(() => residentById(selectedResidentId.value))
const profileDues = computed(() =>
  dues.value.filter(d => d.resident_id === selectedResidentId.value).slice().sort((a, b) => (a.month < b.month ? 1 : -1))
)
const profileOutstanding = computed(() =>
  profileDues.value.filter(d => d.status !== 'paid').reduce((s, d) => s + (d.amount_due - d.amount_paid), 0)
)
const profileTotalPaid = computed(() => profileDues.value.reduce((s, d) => s + d.amount_paid, 0))

function fundLabel(name) {
  const map = { operating: 'Operating Fund', sinking: 'Sinking Fund', contingency: 'Contingency Fund' }
  return map[name] || name
}

// default the initial view to the real current month (once, on first load)
import { watch } from 'vue'
watch(months, (m) => { if (m.length && !selectedMonth.value) selectedMonth.value = realCurrentMonthISO.value })
</script>

<template>
  <div class="sec-maintenance">

    <div class="page-header">
      <div>
        <h2>Maintenance & Dues</h2>
        <p class="page-sub">{{ selectedMonthLabel }} · {{ pendingCount }} pending · {{ overdueCount }} overdue</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="showReminderConfirm = true">📢 Send Reminder</button>
        <button class="btn-add" @click="onGenerateDuesClick">+ Generate Dues</button>
      </div>
    </div>

    <transition name="banner-fade">
      <div v-if="bannerMessage" :class="['action-banner', bannerType === 'success' ? 'banner-success' : 'banner-warning']">
        {{ bannerType === 'success' ? '✓' : '⚠' }} {{ bannerMessage }}
      </div>
    </transition>

    <p v-if="loadError" class="error-msg">{{ loadError }}</p>
    <div v-if="loading" class="empty-state"><p>Loading...</p></div>

    <template v-else-if="months.length">
      <div class="month-selector-row">
        <span class="month-selector-label">Viewing</span>
        <select v-model="selectedMonth" class="month-select">
          <option v-for="m in months" :key="m" :value="m">
            {{ new Date(m).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) }}
          </option>
        </select>
        <span v-if="isCurrentMonthSelected" class="current-tag">Current month</span>
      </div>

      <div class="summary-grid">
        <div class="summary-card dark">
          <span class="summary-label">Total pending</span>
          <span class="summary-value">{{ formatAmount(totalPendingAmount) }}</span>
          <span class="summary-sub">{{ pendingCount + overdueCount }} flats yet to pay</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Collected — {{ selectedMonthLabel }}</span>
          <span class="summary-value green">{{ formatAmount(totalCollectedThisMonth) }}</span>
          <span class="summary-sub">{{ selectedMonthDues.filter(d => d.status === 'paid').length }} flats paid</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Overdue</span>
          <span class="summary-value" :class="{ red: overdueCount > 0 }">{{ overdueCount }}</span>
          <span class="summary-sub">flats past due date</span>
        </div>
      </div>

      <div class="table-wrap">
        <div class="table-header-row">
          <span class="table-title">{{ selectedMonthLabel }} — all residents</span>
        </div>
        <table class="dues-table">
          <thead>
            <tr>
              <th>Resident</th><th>Flat</th><th>Amount Due</th><th>Total Amount Due</th><th>Amount Paid</th><th>Status</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="due in selectedMonthDues" :key="due.id">
              <td><button class="resident-link" @click="openProfile(due.resident_id)">{{ residentById(due.resident_id)?.name }}</button></td>
              <td class="flat-cell">{{ residentById(due.resident_id)?.flat_number || '—' }}</td>
              <td class="amount-cell">{{ formatAmount(due.amount_due) }}</td>
              <td class="amount-cell" :title="'Total unpaid across all months, not just ' + selectedMonthLabel">
                {{ residentById(due.resident_id)?.pending_due != null ? formatAmount(residentById(due.resident_id).pending_due) : '—' }}
              </td>
              <td class="amount-cell">{{ formatAmount(due.amount_paid) }}</td>
              <td><span :class="['status-chip', statusClass(due)]">{{ statusLabel(due) }}</span></td>
              <td>
                <button v-if="due.status === 'paid'" class="receipt-btn" @click="downloadReceipt(due)">Receipt</button>
                <button v-else class="mark-paid-btn" :disabled="markingPaid[due.id]" @click="markPaid(due)">
                  {{ markingPaid[due.id] ? 'Saving...' : 'Mark Paid' }}
                </button>
              </td>
            </tr>
            <tr v-if="!selectedMonthDues.length">
              <td colspan="7" class="empty-row">
                No dues generated for {{ selectedMonthLabel }} yet — click "Generate Dues" above to create them.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="defaultersByMonth.length" class="defaulters-section">
        <h3 class="section-heading">Who Hasn't Paid — Past Months</h3>
        <div v-for="group in defaultersByMonth" :key="group.month" class="defaulter-group">
          <div class="defaulter-group-header">
            <span class="defaulter-month">{{ new Date(group.month).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) }}</span>
            <span class="defaulter-count">{{ group.entries.length }} unpaid · {{ formatAmount(group.total) }}</span>
          </div>
          <div class="defaulter-row" v-for="e in group.entries" :key="e.id">
            <button class="resident-link" @click="openProfile(e.resident_id)">{{ e.resident?.name }}</button>
            <span class="defaulter-flat">{{ e.resident?.flat_number }}</span>
            <span class="defaulter-amount">{{ formatAmount(e.amount_due - e.amount_paid) }} owed</span>
          </div>
        </div>
      </div>

      <div class="fund-section">
        <h3 class="fund-title">Society Fund Balances</h3>
        <p class="fund-sub">Live balances from actual dues payments — see the Funds page for split configuration.</p>
        <div class="fund-grid">
          <div v-for="f in funds" :key="f.id" class="fund-card">
            <span class="fund-label">{{ fundLabel(f.fund_name) }}</span>
            <span class="fund-value">{{ formatAmount(f.balance) }}</span>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-state"><p>No dues generated yet — click "Generate Dues" to get started</p></div>

    <div v-if="showReminderConfirm" class="modal-overlay" @click.self="showReminderConfirm = false">
      <div class="confirm-modal">
        <div class="confirm-icon">📢</div>
        <h3 class="confirm-title">Send reminder?</h3>
        <p class="confirm-sub">This sends a maintenance fee reminder to every resident with pending or overdue dues, across all months.</p>
        <div class="confirm-actions">
          <button class="cancel-btn" @click="showReminderConfirm = false">Cancel</button>
          <button class="send-btn" :disabled="sendingReminder" @click="sendReminder">{{ sendingReminder ? 'Sending...' : 'Yes, send now' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showGenerateModal" class="modal-overlay" @click.self="showGenerateModal = false">
      <div class="confirm-modal">
        <div class="confirm-icon">🧾</div>
        <h3 class="confirm-title">Generate dues</h3>
        <label class="generate-label">Month</label>
        <input type="date" v-model="generateMonth" class="generate-input" />
        <p v-if="generateMonthAlreadyDone" class="generate-warning">
          ⚠ Dues already exist for this month — generating again will only fill in any missing residents, not create a new batch.
        </p>
        <label class="generate-label">Amount per flat (₹)</label>
        <input type="number" v-model.number="generateAmount" class="generate-input" min="0" />
        <div class="confirm-actions">
          <button class="cancel-btn" @click="showGenerateModal = false">Cancel</button>
          <button class="send-btn" :disabled="generating || !generateAmount" @click="confirmGenerateDues">
            {{ generating ? 'Generating...' : (generateMonthAlreadyDone ? 'Top Up Missing' : 'Generate Dues') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showProfileModal" class="modal-overlay" @click.self="showProfileModal = false">
      <div class="profile-modal">
        <div class="profile-header">
          <div>
            <h3>{{ profileResident?.name }}</h3>
            <span class="profile-sub">{{ profileResident?.flat_number }}</span>
          </div>
          <button class="close-btn" @click="showProfileModal = false">✕</button>
        </div>
        <div class="profile-stats">
          <div class="profile-stat">
            <span class="profile-stat-value" :class="{ red: profileOutstanding > 0 }">{{ formatAmount(profileOutstanding) }}</span>
            <span class="profile-stat-label">Outstanding now</span>
          </div>
          <div class="profile-stat">
            <span class="profile-stat-value green">{{ formatAmount(profileTotalPaid) }}</span>
            <span class="profile-stat-label">Paid all-time</span>
          </div>
        </div>
        <div class="profile-history">
          <div class="profile-history-row" v-for="d in profileDues" :key="d.id">
            <span class="profile-history-month">{{ new Date(d.month).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) }}</span>
            <span class="profile-history-amount">{{ formatAmount(d.amount_due) }}</span>
            <span :class="['status-chip', statusClass(d)]">{{ statusLabel(d) }}</span>
            <span class="profile-history-date">{{ formatDate(d.paid_date) }}</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.sec-maintenance { max-width: var(--content-max-width); }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.header-actions { display: flex; gap: 10px; flex-shrink: 0; }

.btn-add {
  height: 42px;
  padding: 0 20px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  white-space: nowrap;
  transition: background var(--transition-fast);
}
.btn-add:hover { background: var(--c-900); }

.btn-outline {
  height: 42px;
  padding: 0 18px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}
.btn-outline:hover { border-color: var(--c-600); color: var(--c-800); }

.action-banner {
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 16px;
  border: 1px solid transparent;
}
.banner-success { background: var(--color-success-bg); color: var(--color-success-text); border-color: var(--color-success); }
.banner-warning { background: var(--color-warning-bg); color: var(--color-warning-text); border-color: var(--color-warning); }

.banner-fade-enter-active, .banner-fade-leave-active { transition: opacity var(--transition-fast); }
.banner-fade-enter-from, .banner-fade-leave-to { opacity: 0; }

.month-selector-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.month-selector-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
}

.month-select {
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-primary);
  background: var(--color-surface);
  cursor: pointer;
}

.current-tag {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-success-text);
  background: var(--color-success-bg);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
}

.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }

.summary-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--shadow-xs);
}

.summary-card.dark { background: linear-gradient(155deg, var(--c-900), var(--c-800)); }
.summary-card.dark .summary-label { color: rgba(255,255,255,0.7); }
.summary-card.dark .summary-value { color: #fff; }
.summary-card.dark .summary-sub   { color: rgba(255,255,255,0.6); }

.summary-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-secondary); }
.summary-value { font-size: 30px; font-weight: 800; color: var(--c-900); letter-spacing: -0.5px; line-height: 1; margin-top: 8px; }
.summary-value.green { color: var(--color-success-text); }
.summary-value.red   { color: var(--color-danger-text); }
.summary-sub { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.table-wrap {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
  margin-bottom: 24px;
}

.table-header-row { padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.table-title { font-size: var(--font-size-lg); font-weight: 800; color: var(--c-900); }

.dues-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }

.dues-table th {
  padding: 12px 20px;
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  background: var(--color-surface-soft);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.dues-table td { padding: 14px 20px; border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.dues-table tbody tr:last-child td { border-bottom: none; }
.dues-table tbody tr:hover { background: var(--color-surface-muted); }

.resident-link {
  font-weight: 700;
  color: var(--c-800);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.resident-link:hover { color: var(--c-900); }

.flat-cell   { font-weight: 600; color: var(--color-text-secondary); }
.amount-cell { font-weight: 700; color: var(--color-text-primary); }

.empty-row {
  text-align: center;
  padding: 24px 12px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
.date-cell   { color: var(--color-text-muted); white-space: nowrap; }

.status-chip { padding: 3px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; }
.status-paid    { background: var(--color-success-bg); color: var(--color-success-text); }
.status-pending { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-overdue { background: var(--color-danger-bg);  color: var(--color-danger-text);  }

.receipt-btn {
  font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary);
  background: var(--color-surface-muted); padding: 6px 12px; border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}
.receipt-btn:hover { background: var(--color-border); }

.mark-paid-btn {
  font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800);
  background: #E9F4FA; padding: 6px 12px; border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}
.mark-paid-btn:hover { background: #D4EBF7; }

/* defaulters */
.defaulters-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  box-shadow: var(--shadow-xs);
  margin-bottom: 24px;
}

.section-heading { font-size: var(--font-size-xl); font-weight: 800; color: var(--c-900); margin-bottom: 4px; }
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; }

.defaulter-group { margin-bottom: 14px; }
.defaulter-group:last-child { margin-bottom: 0; }

.defaulter-group-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1.5px solid var(--color-border);
  margin-bottom: 6px;
}
.defaulter-month { font-size: var(--font-size-sm); font-weight: 800; color: var(--c-900); }
.defaulter-count { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-danger-text); }

.defaulter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--color-border);
}
.defaulter-row:last-child { border-bottom: none; }

.defaulter-flat { font-size: var(--font-size-sm); color: var(--color-text-muted); font-weight: 600; }
.defaulter-amount { margin-left: auto; font-size: var(--font-size-sm); font-weight: 700; color: var(--color-danger-text); }

/* fund breakdown */
.fund-section { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 22px; box-shadow: var(--shadow-xs); }
.fund-title { font-size: var(--font-size-xl); font-weight: 800; color: var(--c-900); margin-bottom: 4px; }
.fund-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 20px; }
.fund-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.fund-card { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 16px; display: flex; flex-direction: column; gap: 4px; }
.fund-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-secondary); }
.fund-value { font-size: var(--font-size-2xl); font-weight: 800; color: var(--c-900); letter-spacing: -0.4px; }
.fund-pct { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-bottom: 8px; }
.fund-bar { height: 6px; background: var(--color-border); border-radius: var(--radius-pill); overflow: hidden; }
.fund-fill { height: 100%; border-radius: var(--radius-pill); transition: width var(--transition-slow); }
.fund-fill.operating   { background: var(--c-800); }
.fund-fill.sinking     { background: var(--c-500); }
.fund-fill.contingency { background: var(--c-300); }

/* shared modal overlay */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); padding: 20px; }

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

.confirm-icon { width: 60px; height: 60px; border-radius: 50%; background: var(--color-info-bg); display: flex; align-items: center; justify-content: center; font-size: 26px; }
.confirm-title { font-size: var(--font-size-2xl); font-weight: 800; color: var(--c-900); }
.confirm-sub { font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.55; }

.generate-label { align-self: flex-start; font-size: var(--font-size-sm); font-weight: 700; color: var(--c-800); margin-top: 4px; }

.generate-warning {
  align-self: stretch;
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-align: left;
  line-height: 1.4;
}
.generate-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: 700;
  text-align: center;
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
}
.generate-input:focus { border-color: var(--c-600); }

.confirm-actions { display: flex; gap: 12px; width: 100%; margin-top: 4px; }
.cancel-btn { flex: 1; height: 46px; border-radius: var(--radius-md); background: var(--color-surface-muted); color: var(--color-text-secondary); font-size: var(--font-size-md); font-weight: 700; transition: background var(--transition-fast); }
.cancel-btn:hover { background: var(--color-border); }
.send-btn { flex: 1; height: 46px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; transition: background var(--transition-fast); }
.send-btn:hover:not(:disabled) { background: var(--c-900); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* profile modal */
.profile-modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.profile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
}
.profile-header h3 { font-size: var(--font-size-xl); font-weight: 700; }
.profile-sub { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.close-btn { width: 32px; height: 32px; border-radius: var(--radius-sm); background: var(--color-bg); color: var(--color-text-secondary); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.close-btn:hover { background: var(--color-border); }

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 18px 24px;
  border-bottom: 1px solid var(--color-border);
}
.profile-stat { display: flex; flex-direction: column; gap: 2px; }
.profile-stat-value { font-size: var(--font-size-2xl); font-weight: 800; color: var(--c-900); }
.profile-stat-value.red   { color: var(--color-danger-text); }
.profile-stat-value.green { color: var(--color-success-text); }
.profile-stat-label { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: 600; }

.profile-history { padding: 8px 24px 22px; display: flex; flex-direction: column; }
.profile-history-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}
.profile-history-row:last-child { border-bottom: none; }
.profile-history-month { flex: 1; font-weight: 600; color: var(--color-text-primary); }
.profile-history-amount { font-weight: 700; color: var(--color-text-secondary); }
.profile-history-date { font-size: var(--font-size-xs); color: var(--color-text-muted); white-space: nowrap; }
</style>