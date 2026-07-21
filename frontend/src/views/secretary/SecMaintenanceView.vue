<script setup>
import { ref, computed } from 'vue'

/* ---------------- Roster & standard amount ---------------- */

const residents = [
  { id: 'r1', name: 'Ravi Kumar',   flat: 'A-402' },
  { id: 'r2', name: 'Priya Menon',  flat: 'B-201' },
  { id: 'r3', name: 'Arjun Nair',   flat: 'C-105' },
  { id: 'r4', name: 'Sana Iqbal',   flat: 'A-108' },
  { id: 'r5', name: 'Meena Sharma', flat: 'B-301' },
  { id: 'r6', name: 'Anil Reddy',   flat: 'D-201' },
]

const STANDARD_AMOUNT = 2500

function residentById(id) {
  return residents.find(r => r.id === id)
}

/* ---------------- Months & mock history ---------------- */
// mock data - replace with API in Sprint 1
// one row per (resident, month) — mirrors the shape the resident-side Dues view already uses

const initialMonths = [
  { key: '2026-03', label: 'March 2026', dueDate: '5 Mar 2026' },
  { key: '2026-04', label: 'April 2026', dueDate: '5 Apr 2026' },
  { key: '2026-05', label: 'May 2026',   dueDate: '5 May 2026' },
  { key: '2026-06', label: 'June 2026',  dueDate: '5 Jun 2026' },
  { key: '2026-07', label: 'July 2026',  dueDate: '5 Jul 2026' },
]

const months = ref([...initialMonths])

// 'ontime' | 'late' (paid, but after due date) | 'unpaid'  — indices line up with initialMonths
const paymentPatterns = {
  r1: ['ontime', 'ontime', 'late',   'ontime', 'unpaid'],
  r2: ['ontime', 'ontime', 'ontime', 'ontime', 'ontime'],
  r3: ['unpaid', 'unpaid', 'late',   'unpaid', 'unpaid'],
  r4: ['ontime', 'ontime', 'ontime', 'ontime', 'ontime'],
  r5: ['late',   'unpaid', 'ontime', 'ontime', 'unpaid'],
  r6: ['ontime', 'ontime', 'ontime', 'unpaid', 'unpaid'],
}

const lateCells = {
  'r1_2026-05': '14 May 2026',
  'r3_2026-05': '20 May 2026',
  'r5_2026-03': '15 Mar 2026',
}

const dues = ref(
  residents.flatMap(r =>
    initialMonths.map((m, idx) => {
      const pattern = paymentPatterns[r.id][idx]
      const key = `${r.id}_${m.key}`
      if (pattern === 'unpaid') {
        return { id: key, residentId: r.id, month: m.key, amount_due: STANDARD_AMOUNT, amount_paid: 0, due_date: m.dueDate, paid_date: null, paidLate: false }
      }
      const late = pattern === 'late'
      return {
        id: key, residentId: r.id, month: m.key,
        amount_due: STANDARD_AMOUNT, amount_paid: STANDARD_AMOUNT,
        due_date: m.dueDate,
        paid_date: late ? (lateCells[key] || m.dueDate) : m.dueDate,
        paidLate: late,
      }
    })
  )
)

/* ---------------- Month selector (history browsing) ---------------- */

const selectedMonth = ref(initialMonths[initialMonths.length - 1].key)

const latestMonth = computed(() => months.value[months.value.length - 1])
const isCurrentMonthSelected = computed(() => selectedMonth.value === latestMonth.value.key)

const selectedMonthLabel = computed(() =>
  months.value.find(m => m.key === selectedMonth.value)?.label || ''
)

const selectedMonthDues = computed(() =>
  dues.value.filter(d => d.month === selectedMonth.value)
)

function getStatus(due) {
  if (due.amount_paid >= due.amount_due) return 'paid'
  if (new Date(due.due_date) < new Date()) return 'overdue'
  return 'pending'
}

function statusLabel(due) {
  const s = getStatus(due)
  if (s === 'paid')    return 'Paid'
  if (s === 'overdue') return 'Overdue'
  return 'Pending'
}

function statusClass(due) {
  const s = getStatus(due)
  if (s === 'paid')    return 'status-paid'
  if (s === 'overdue') return 'status-overdue'
  return 'status-pending'
}

const pendingCount = computed(() => selectedMonthDues.value.filter(d => getStatus(d) === 'pending').length)
const overdueCount = computed(() => selectedMonthDues.value.filter(d => getStatus(d) === 'overdue').length)

const totalPendingAmount = computed(() =>
  selectedMonthDues.value.filter(d => getStatus(d) !== 'paid').reduce((s, d) => s + (d.amount_due - d.amount_paid), 0)
)

const totalCollectedThisMonth = computed(() =>
  selectedMonthDues.value.reduce((s, d) => s + d.amount_paid, 0)
)

function formatAmount(n) {
  return '₹' + n.toLocaleString('en-IN')
}

function markPaid(due) {
  due.amount_paid = due.amount_due
  due.paid_date = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  due.paidLate = new Date(due.due_date) < new Date()
}

/* ---------------- Generate Dues (guarded by month-end) ---------------- */

function monthEndDate(key) {
  const [y, m] = key.split('-').map(Number)
  return new Date(y, m, 0) // last day of the calendar month represented by key
}

function addMonthKey(key) {
  const [y, m] = key.split('-').map(Number)
  const ny = m === 12 ? y + 1 : y
  const nm = m === 12 ? 1 : m + 1
  return `${ny}-${String(nm).padStart(2, '0')}`
}

function monthKeyLabel(key) {
  const [y, m] = key.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
}

function monthKeyDueDateLabel(key) {
  const [y, m] = key.split('-').map(Number)
  return new Date(y, m - 1, 5).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

const monthHasEnded = computed(() => new Date() > monthEndDate(latestMonth.value.key))
const nextMonthKey   = computed(() => addMonthKey(latestMonth.value.key))
const nextMonthLabel = computed(() => monthKeyLabel(nextMonthKey.value))

const showGenerateModal = ref(false)
const generateAmount    = ref(STANDARD_AMOUNT)

function onGenerateDuesClick() {
  if (!monthHasEnded.value) {
    const endLabel = monthEndDate(latestMonth.value.key).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    showBanner(`${latestMonth.value.label} hasn't ended yet — dues can be generated after ${endLabel}.`, 'warning')
    return
  }
  generateAmount.value = STANDARD_AMOUNT
  showGenerateModal.value = true
}

function confirmGenerateDues() {
  if (!generateAmount.value) return
  const key = nextMonthKey.value
  const label = nextMonthLabel.value
  const dueDateLabel = monthKeyDueDateLabel(key)

  residents.forEach(r => {
    dues.value.push({
      id: `${r.id}_${key}`, residentId: r.id, month: key,
      amount_due: Number(generateAmount.value), amount_paid: 0,
      due_date: dueDateLabel, paid_date: null, paidLate: false,
    })
  })
  months.value.push({ key, label, dueDate: dueDateLabel })
  selectedMonth.value = key
  showGenerateModal.value = false
  showBanner(`Dues generated for ${label} — ${residents.length} residents, ${formatAmount(Number(generateAmount.value))} each`, 'success')
}

/* ---------------- Bulk reminder ---------------- */

const showReminderConfirm = ref(false)

function sendReminder() {
  showReminderConfirm.value = false
  showBanner(`Reminder sent to all residents with pending or overdue dues for ${selectedMonthLabel.value}`, 'success')
}

/* ---------------- Banner ---------------- */

const bannerMessage = ref('')
const bannerType     = ref('success')
let bannerTimer = null

function showBanner(msg, type = 'success') {
  bannerMessage.value = msg
  bannerType.value = type
  clearTimeout(bannerTimer)
  bannerTimer = setTimeout(() => { bannerMessage.value = '' }, 4500)
}

/* ---------------- Defaulters (past months only) ---------------- */

const defaultersByMonth = computed(() => {
  const pastMonths = months.value.slice(0, -1)
  return [...pastMonths].reverse()
    .map(m => {
      const entries = dues.value
        .filter(d => d.month === m.key && d.amount_paid < d.amount_due)
        .map(d => ({ ...d, resident: residentById(d.residentId) }))
      const total = entries.reduce((s, e) => s + (e.amount_due - e.amount_paid), 0)
      return { month: m, entries, total }
    })
    .filter(g => g.entries.length > 0)
})

/* ---------------- Resident profile ---------------- */

const showProfileModal  = ref(false)
const selectedResidentId = ref(null)

function openProfile(residentId) {
  selectedResidentId.value = residentId
  showProfileModal.value = true
}

const profileResident = computed(() => residentById(selectedResidentId.value))

const profileDues = computed(() =>
  dues.value
    .filter(d => d.residentId === selectedResidentId.value)
    .slice()
    .sort((a, b) => (a.month < b.month ? 1 : -1))
)

const profileLateCount = computed(() =>
  profileDues.value.filter(d => d.amount_paid < d.amount_due || d.paidLate).length
)

const profileOutstanding = computed(() =>
  profileDues.value.filter(d => d.amount_paid < d.amount_due).reduce((s, d) => s + (d.amount_due - d.amount_paid), 0)
)

const profileTotalPaid = computed(() =>
  profileDues.value.reduce((s, d) => s + d.amount_paid, 0)
)

function monthLabelForKey(key) {
  return months.value.find(m => m.key === key)?.label || key
}

/* ---------------- Society fund — all-time, not month-scoped ---------------- */

const fundSplit = { operating: 70, sinking: 20, contingency: 10 }

const totalCollectedAllTime = computed(() =>
  dues.value.reduce((sum, d) => sum + d.amount_paid, 0)
)

const fundBalances = computed(() => ({
  operating:   Math.round(totalCollectedAllTime.value * fundSplit.operating   / 100),
  sinking:     Math.round(totalCollectedAllTime.value * fundSplit.sinking     / 100),
  contingency: Math.round(totalCollectedAllTime.value * fundSplit.contingency / 100),
}))
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

    <!-- month selector -->
    <div class="month-selector-row">
      <span class="month-selector-label">Viewing</span>
      <select v-model="selectedMonth" class="month-select">
        <option v-for="m in months" :key="m.key" :value="m.key">{{ m.label }}</option>
      </select>
      <span v-if="isCurrentMonthSelected" class="current-tag">Current month</span>
    </div>

    <!-- summary cards -->
    <div class="summary-grid">
      <div class="summary-card dark">
        <span class="summary-label">Total pending</span>
        <span class="summary-value">{{ formatAmount(totalPendingAmount) }}</span>
        <span class="summary-sub">{{ pendingCount + overdueCount }} flats yet to pay</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Collected — {{ selectedMonthLabel }}</span>
        <span class="summary-value green">{{ formatAmount(totalCollectedThisMonth) }}</span>
        <span class="summary-sub">{{ selectedMonthDues.filter(d => getStatus(d) === 'paid').length }} flats paid</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Overdue</span>
        <span class="summary-value" :class="{ red: overdueCount > 0 }">{{ overdueCount }}</span>
        <span class="summary-sub">flats past due date</span>
      </div>
    </div>

    <!-- dues table -->
    <div class="table-wrap">
      <div class="table-header-row">
        <span class="table-title">{{ selectedMonthLabel }} — all residents</span>
      </div>
      <table class="dues-table">
        <thead>
          <tr>
            <th>Resident</th>
            <th>Flat</th>
            <th>Amount Due</th>
            <th>Amount Paid</th>
            <th>Due Date</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="due in selectedMonthDues" :key="due.id">
            <td>
              <button class="resident-link" @click="openProfile(due.residentId)">
                {{ residentById(due.residentId)?.name }}
              </button>
            </td>
            <td class="flat-cell">{{ residentById(due.residentId)?.flat }}</td>
            <td class="amount-cell">{{ formatAmount(due.amount_due) }}</td>
            <td class="amount-cell">{{ formatAmount(due.amount_paid) }}</td>
            <td class="date-cell">{{ due.due_date }}</td>
            <td><span :class="['status-chip', statusClass(due)]">{{ statusLabel(due) }}</span></td>
            <td>
              <button v-if="getStatus(due) === 'paid'" class="receipt-btn">Receipt</button>
              <button v-else class="mark-paid-btn" @click="markPaid(due)">Mark Paid</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- defaulters -->
    <div v-if="defaultersByMonth.length" class="defaulters-section">
      <h3 class="section-heading">Who Hasn't Paid — Past Months</h3>
      <p class="section-sub">Grouped by month, most recent first. Click a resident to see their full payment record.</p>

      <div v-for="group in defaultersByMonth" :key="group.month.key" class="defaulter-group">
        <div class="defaulter-group-header">
          <span class="defaulter-month">{{ group.month.label }}</span>
          <span class="defaulter-count">{{ group.entries.length }} unpaid · {{ formatAmount(group.total) }}</span>
        </div>
        <div class="defaulter-row" v-for="e in group.entries" :key="e.id">
          <button class="resident-link" @click="openProfile(e.residentId)">{{ e.resident.name }}</button>
          <span class="defaulter-flat">{{ e.resident.flat }}</span>
          <span class="defaulter-amount">{{ formatAmount(e.amount_due - e.amount_paid) }} owed</span>
        </div>
      </div>
    </div>

    <!-- society fund breakdown -->
    <div class="fund-section">
      <h3 class="fund-title">Society Fund Breakdown</h3>
      <p class="fund-sub">All-time collections: {{ formatAmount(totalCollectedAllTime) }} · Split: {{ fundSplit.operating }}% operating / {{ fundSplit.sinking }}% sinking / {{ fundSplit.contingency }}% contingency</p>
      <div class="fund-grid">
        <div class="fund-card">
          <span class="fund-label">Operating Fund</span>
          <span class="fund-value">{{ formatAmount(fundBalances.operating) }}</span>
          <span class="fund-pct">{{ fundSplit.operating }}% of collections</span>
          <div class="fund-bar"><div class="fund-fill operating" :style="{ width: fundSplit.operating + '%' }"></div></div>
        </div>
        <div class="fund-card">
          <span class="fund-label">Sinking Fund</span>
          <span class="fund-value">{{ formatAmount(fundBalances.sinking) }}</span>
          <span class="fund-pct">{{ fundSplit.sinking }}% of collections</span>
          <div class="fund-bar"><div class="fund-fill sinking" :style="{ width: fundSplit.sinking + '%' }"></div></div>
        </div>
        <div class="fund-card">
          <span class="fund-label">Contingency Fund</span>
          <span class="fund-value">{{ formatAmount(fundBalances.contingency) }}</span>
          <span class="fund-pct">{{ fundSplit.contingency }}% of collections</span>
          <div class="fund-bar"><div class="fund-fill contingency" :style="{ width: fundSplit.contingency + '%' }"></div></div>
        </div>
      </div>
    </div>

    <!-- reminder confirm modal -->
    <div v-if="showReminderConfirm" class="modal-overlay" @click.self="showReminderConfirm = false">
      <div class="confirm-modal">
        <div class="confirm-icon">📢</div>
        <h3 class="confirm-title">Send reminder?</h3>
        <p class="confirm-sub">
          This will send a maintenance fee reminder to all
          <strong>{{ pendingCount + overdueCount }} residents</strong>
          with pending or overdue dues for {{ selectedMonthLabel }}.
        </p>
        <div class="confirm-actions">
          <button class="cancel-btn" @click="showReminderConfirm = false">Cancel</button>
          <button class="send-btn" @click="sendReminder">Yes, send now</button>
        </div>
      </div>
    </div>

    <!-- generate dues modal -->
    <div v-if="showGenerateModal" class="modal-overlay" @click.self="showGenerateModal = false">
      <div class="confirm-modal">
        <div class="confirm-icon">🧾</div>
        <h3 class="confirm-title">Generate {{ nextMonthLabel }} dues?</h3>
        <p class="confirm-sub">This creates a due record for all <strong>{{ residents.length }} residents</strong>.</p>
        <label class="generate-label">Amount per flat (₹)</label>
        <input type="number" v-model="generateAmount" class="generate-input" min="0" />
        <div class="confirm-actions">
          <button class="cancel-btn" @click="showGenerateModal = false">Cancel</button>
          <button class="send-btn" :disabled="!generateAmount" @click="confirmGenerateDues">Generate Dues</button>
        </div>
      </div>
    </div>

    <!-- resident profile modal -->
    <div v-if="showProfileModal" class="modal-overlay" @click.self="showProfileModal = false">
      <div class="profile-modal">
        <div class="profile-header">
          <div>
            <h3>{{ profileResident?.name }}</h3>
            <span class="profile-sub">{{ profileResident?.flat }}</span>
          </div>
          <button class="close-btn" @click="showProfileModal = false">✕</button>
        </div>

        <div class="profile-stats">
          <div class="profile-stat">
            <span class="profile-stat-value" :class="{ red: profileLateCount > 0 }">{{ profileLateCount }}</span>
            <span class="profile-stat-label">Times not on time</span>
          </div>
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
            <span class="profile-history-month">{{ monthLabelForKey(d.month) }}</span>
            <span class="profile-history-amount">{{ formatAmount(d.amount_due) }}</span>
            <span :class="['status-chip', statusClass(d)]">{{ statusLabel(d) }}</span>
            <span class="profile-history-date">{{ d.paid_date || '—' }}</span>
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