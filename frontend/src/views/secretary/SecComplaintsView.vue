<script setup>
import { ref, computed, watch } from 'vue'

/* ---------------- Filters ---------------- */

const filterStatus   = ref('All')
const filterCategory = ref('all')
const filterPriority = ref('all')
const sortBy         = ref('priority-desc')
const searchQuery    = ref('')

const statusFilters   = ['All', 'Open', 'In Progress', 'Resolved', 'Rejected']
const categoryOptions = ['all', 'Plumbing', 'Electrical', 'Cleaning', 'Carpentry', 'Security', 'Gardening', 'Other']
const priorityOptions = ['all', 'High', 'Medium', 'Low']
const priorityRank    = { High: 3, Medium: 2, Low: 1 }

const durationOptions = [
  { label: '30 mins', minutes: 30 },
  { label: '1 hr',     minutes: 60 },
  { label: '1.5 hr',   minutes: 90 },
  { label: '2 hr',     minutes: 120 },
  { label: '3 hr',     minutes: 180 },
]

/* ---------------- Vendors ---------------- */
// engagementType: 'per_job' -> paid per completed task (plumbers, electricians, etc.)
//                 'salaried' -> fixed monthly salary (security, gardeners), no per-task payment
const vendors = [
  { name: 'Kishore Plumbing', category: 'Plumbing',   engagementType: 'per_job' },
  { name: 'Raju Electricals', category: 'Electrical', engagementType: 'per_job' },
  { name: 'Suresh Carpentry', category: 'Carpentry',  engagementType: 'per_job' },
  { name: 'Clean Society',    category: 'Cleaning',   engagementType: 'per_job' },
  { name: 'OtisCare Lifts',   category: 'Other',      engagementType: 'per_job' },
  { name: 'Ramesh Yadav',     category: 'Security',   engagementType: 'salaried', salary: 18000 },
  { name: 'Ganesh Mali',      category: 'Gardening',  engagementType: 'salaried', salary: 12000 },
]

function vendorByName(name) {
  return vendors.find(v => v.name === name) || null
}

// Mock AI time estimates per category - replace with real model output in Sprint 1
const estimatedMinutesByCategory = {
  Plumbing: 60,
  Electrical: 45,
  Carpentry: 90,
  Cleaning: 45,
  Security: 30,
  Gardening: 60,
  Other: 90,
}

/* ---------------- Issues (community / common-area only) ---------------- */
// Personal, inside-the-flat complaints never appear here — they live in the
// resident's own complaint history. Only common-area issues reach this list.
// Multiple residents can report the same issue, so each issue carries a
// `reports` array instead of a single resident.

const issues = ref([
  {
    id: 'ISS-2039',
    title: 'Corridor light flickering',
    location: '4th floor corridor, Tower A',
    category: 'Electrical',
    aiCategory: 'Electrical',
    priority: 'Medium',
    aiPriority: 'Medium',
    status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null, paymentStatus: null, paymentAmount: null,
    date: '27 Jun',
    aiSummary: 'Residents report a flickering light on the 4th floor corridor landing in Tower A.',
    reports: [
      { resident: 'Ravi Kumar', flat: 'A-402', desc: 'Corridor light flickering on the 4th floor landing', date: '27 Jun', residentPriority: 'High' },
    ],
  },
  {
    id: 'ISS-2046',
    title: 'Lift lobby light flickering',
    location: '4th floor corridor, Tower A',
    category: 'Electrical',
    aiCategory: 'Electrical',
    priority: 'Medium',
    aiPriority: 'Medium',
    status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null, paymentStatus: null, paymentAmount: null,
    date: '29 Jun',
    aiSummary: 'A second, separate report of a flickering light near the 4th floor lift lobby in Tower A — likely the same fault as ISS-2039.',
    reports: [
      { resident: 'Meena Sharma', flat: 'A-405', desc: 'Lift lobby light on the 4th floor keeps flickering, happened twice this week', date: '29 Jun', residentPriority: 'Medium' },
    ],
  },
  {
    id: 'ISS-2050',
    title: 'Terrace water tank overflowing',
    location: 'Terrace, Tower B',
    category: 'Plumbing',
    aiCategory: 'Plumbing',
    priority: 'High',
    aiPriority: 'High',
    status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null, paymentStatus: null, paymentAmount: null,
    date: '30 Jun',
    aiSummary: 'The terrace water tank in Tower B is overflowing, wasting water and posing a slip risk below.',
    reports: [
      { resident: 'Karan Mehta', flat: 'B-304', desc: 'Water overflowing from the terrace tank, wasting a lot of water', date: '30 Jun', residentPriority: 'High' },
    ],
  },
  {
    id: 'ISS-2028',
    title: 'Lift grinding noise',
    location: 'Lift 2, Tower A (between floors 3–5)',
    category: 'Other',
    aiCategory: 'Other',
    priority: 'Medium',
    aiPriority: 'Medium',
    status: 'In Progress',
    vendor: 'OtisCare Lifts', scheduledStart: '2026-06-22T14:00', durationMinutes: 120,
    paymentStatus: 'pending', paymentAmount: null,
    date: '22 Jun',
    aiSummary: 'Lift 2 in Tower A makes a grinding noise while travelling between the 3rd and 5th floors.',
    reports: [
      { resident: 'Sana Iqbal', flat: 'A-108', desc: 'Lift making grinding noise between floors 3 and 5', date: '22 Jun', residentPriority: 'High' },
    ],
  },
  {
    id: 'ISS-2031',
    title: 'Garbage not collected',
    location: 'B-wing basement',
    category: 'Cleaning',
    aiCategory: 'Cleaning',
    priority: 'Low',
    aiPriority: 'Low',
    status: 'Resolved',
    vendor: 'Clean Society', scheduledStart: '2026-06-24T09:00', durationMinutes: 60,
    paymentStatus: 'paid', paymentAmount: 800,
    date: '24 Jun',
    aiSummary: 'Garbage was not collected from the B-wing basement collection point.',
    reports: [
      { resident: 'Meena Sharma', flat: 'B-201', desc: 'Garbage not collected from B-wing basement', date: '24 Jun', residentPriority: 'Low' },
    ],
  },
])

const visibleIssues = computed(() => issues.value.filter(i => i.status !== 'Merged'))

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return visibleIssues.value.filter(i => {
    const matchesStatus   = filterStatus.value === 'All' || i.status === filterStatus.value
    const matchesCategory = filterCategory.value === 'all' || i.category === filterCategory.value
    const matchesPriority = filterPriority.value === 'all' || i.priority === filterPriority.value
    const matchesSearch   = !q
      || i.title.toLowerCase().includes(q)
      || i.location.toLowerCase().includes(q)
      || i.id.toLowerCase().includes(q)
      || i.reports.some(r => r.resident.toLowerCase().includes(q) || r.desc.toLowerCase().includes(q))
    return matchesStatus && matchesCategory && matchesPriority && matchesSearch
  })
})

const openCount       = computed(() => visibleIssues.value.filter(i => i.status === 'Open').length)
const unassignedCount = computed(() => visibleIssues.value.filter(i => !i.vendor && i.status !== 'Resolved').length)

const sortedFiltered = computed(() => {
  const arr = [...filtered.value]
  switch (sortBy.value) {
    case 'priority-asc':  return arr.sort((a, b) => priorityRank[a.priority] - priorityRank[b.priority])
    case 'priority-desc': return arr.sort((a, b) => priorityRank[b.priority] - priorityRank[a.priority])
    case 'reports-asc':   return arr.sort((a, b) => a.reports.length - b.reports.length)
    case 'reports-desc':  return arr.sort((a, b) => b.reports.length - a.reports.length)
    default:              return arr
  }
})

/* ---------------- Detail modal ---------------- */

const showDetail = ref(false)
const selected   = ref(null)

const detailCategory = ref('')
const detailVendor   = ref('')
const detailDate     = ref('')
const detailTime     = ref('')
const detailDuration = ref(60)
const completePaymentAmount = ref('')
const mergeTarget    = ref('')
const lastAiNote      = ref('')
const rejectReason    = ref('')

/* ---------------- Toast ---------------- */

const toastVisible = ref(false)
const toastText    = ref('')
let toastTimer = null

function showToast(text) {
  toastText.value = text
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2600)
}

function openDetail(issue) {
  selected.value = issue
  detailCategory.value = issue.category
  detailVendor.value   = issue.vendor || ''
  if (issue.scheduledStart) {
    const [d, t] = issue.scheduledStart.split('T')
    detailDate.value = d
    detailTime.value = t
  } else {
    detailDate.value = ''
    detailTime.value = ''
  }
  detailDuration.value = issue.durationMinutes || 60
  completePaymentAmount.value = ''
  mergeTarget.value = ''
  lastAiNote.value = ''
  rejectReason.value = ''
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selected.value = null
}

// If the category changes, drop a vendor that no longer matches it
watch(detailCategory, () => {
  if (detailVendor.value && vendorByName(detailVendor.value)?.category !== detailCategory.value) {
    detailVendor.value = ''
  }
})

const vendorsForCategory = computed(() => vendors.filter(v => v.category === detailCategory.value))

function suggestVendorAI() {
  const candidates = vendorsForCategory.value
  if (!candidates.length) return
  const loadOf = (v) => issues.value.filter(i =>
    i.vendor === v.name && i.status === 'In Progress' && i.id !== selected.value?.id
  ).length
  const best = [...candidates].sort((a, b) => loadOf(a) - loadOf(b))[0]
  detailVendor.value = best.name
  detailDuration.value = estimatedMinutesByCategory[detailCategory.value] || 60
  lastAiNote.value = `AI suggested ${best.name} · ~${durationOptions.find(d => d.minutes === detailDuration.value)?.label || detailDuration.value + ' min'}`
}

function slotRange(startIso, minutes) {
  const start = new Date(startIso)
  return { start, end: new Date(start.getTime() + minutes * 60000) }
}

const proposedSlot = computed(() => {
  if (!detailDate.value || !detailTime.value) return null
  return slotRange(`${detailDate.value}T${detailTime.value}`, detailDuration.value)
})

const conflict = computed(() => {
  if (!detailVendor.value || !proposedSlot.value) return null
  const { start, end } = proposedSlot.value
  return issues.value.find(i => {
    if (i.id === selected.value?.id) return false
    if (i.vendor !== detailVendor.value) return false
    if (i.status !== 'In Progress') return false
    if (!i.scheduledStart || !i.durationMinutes) return false
    const existing = slotRange(i.scheduledStart, i.durationMinutes)
    return start < existing.end && end > existing.start
  }) || null
})

function formatSlot(iso, minutes) {
  if (!iso) return ''
  const d = new Date(iso)
  const datePart = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
  const timePart = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  const durLabel = durationOptions.find(o => o.minutes === minutes)?.label || `${minutes}m`
  return `${datePart}, ${timePart} · ${durLabel}`
}

function confirmAssign() {
  if (!detailVendor.value || !proposedSlot.value || conflict.value) return
  const issue = selected.value
  const wasUnassigned = !issue.vendor

  issue.category         = detailCategory.value
  issue.vendor           = detailVendor.value
  issue.scheduledStart   = `${detailDate.value}T${detailTime.value}`
  issue.durationMinutes  = detailDuration.value
  if (issue.status === 'Open') issue.status = 'In Progress'

  const vendorMeta = vendorByName(detailVendor.value)
  issue.paymentStatus = vendorMeta?.engagementType === 'per_job' ? 'pending' : 'not_applicable'

  showToast(wasUnassigned ? `${issue.id} updated — vendor assigned` : `${issue.id} updated — schedule changed`)
  closeDetail()
}

/* ---------------- Complete / payment ---------------- */

const completingVendor = computed(() => vendorByName(selected.value?.vendor))
const needsPayment      = computed(() => completingVendor.value?.engagementType === 'per_job')

function confirmComplete() {
  if (needsPayment.value && !completePaymentAmount.value) return
  const issue = selected.value
  issue.status        = 'Resolved'
  issue.paymentStatus = needsPayment.value ? 'paid' : 'not_applicable'
  issue.paymentAmount = needsPayment.value ? Number(completePaymentAmount.value) : null

  showToast(`${issue.id} updated — closed${needsPayment.value ? ' and payment recorded' : ''}`)
  closeDetail()
}

/* ---------------- Merge ---------------- */

const mergeableIssues = computed(() =>
  visibleIssues.value.filter(i => i.id !== selected.value?.id && !['Resolved', 'Rejected'].includes(i.status))
)

function confirmMerge() {
  if (!mergeTarget.value) return
  const target = issues.value.find(i => i.id === mergeTarget.value)
  const current = selected.value
  if (!target || !current) return

  target.reports.push(...current.reports)
  if (priorityRank[current.priority] > priorityRank[target.priority]) {
    target.priority = current.priority
  }
  current.status = 'Merged'

  showToast(`${current.id} merged into ${target.id}`)
  closeDetail()
}

/* ---------------- Reject ---------------- */

function confirmReject() {
  if (!rejectReason.value.trim()) return
  const issue = selected.value
  issue.status = 'Rejected'
  issue.rejectionReason = rejectReason.value.trim()

  showToast(`${issue.id} rejected`)
  closeDetail()
}

/* ---------------- Badge helpers ---------------- */

function priorityClass(p) {
  if (p === 'High')   return 'pri-high'
  if (p === 'Medium') return 'pri-medium'
  return 'pri-low'
}

function statusClass(s) {
  if (s === 'Open')        return 'status-open'
  if (s === 'In Progress') return 'status-progress'
  if (s === 'Resolved')    return 'status-resolved'
  if (s === 'Rejected')    return 'status-rejected'
  return ''
}
</script>

<template>
  <div class="sec-issues">

    <!-- header -->
    <div class="page-header">
      <div>
        <h2>Community Issues</h2>
        <p class="page-sub">{{ visibleIssues.length }} total · {{ openCount }} open · {{ unassignedCount }} unassigned</p>
      </div>
    </div>

    <!-- toolbar -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search issue, location, ID, resident..."
        class="search-input"
      />
      <div class="toolbar-row">
        <div class="status-pill-group">
          <button
            v-for="s in statusFilters"
            :key="s"
            :class="['status-pill', { active: filterStatus === s }]"
            @click="filterStatus = s"
          >
            {{ s }}
          </button>
        </div>
        <div class="right-filters">
          <select v-model="filterCategory" class="filter-select">
            <option value="all">All categories</option>
            <option v-for="c in categoryOptions.slice(1)" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="filterPriority" class="filter-select">
            <option value="all">All priority</option>
            <option v-for="p in priorityOptions.slice(1)" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="sortBy" class="filter-select">
            <option value="priority-desc">Priority: High → Low</option>
            <option value="priority-asc">Priority: Low → High</option>
            <option value="reports-asc">Reports: Fewest first</option>
            <option value="reports-desc">Reports: Most first</option>
          </select>
        </div>
      </div>
    </div>

    <!-- issues table -->
    <div class="table-wrap">
      <table class="issues-table">
        <thead>
          <tr>
            <th>Issue</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Vendor</th>
            <th>Reports</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in sortedFiltered" :key="i.id" class="issue-row" @click="openDetail(i)">

            <td>
              <span class="issue-title">{{ i.title }}</span>
              <span class="issue-meta">{{ i.location }} · {{ i.id }}</span>
            </td>

            <td><span class="category-badge">{{ i.category }}</span></td>

            <td><span :class="['priority-badge', priorityClass(i.priority)]">{{ i.priority }}</span></td>

            <td><span :class="['status-badge', statusClass(i.status)]">{{ i.status }}</span></td>

            <td>
              <div v-if="i.vendor" class="vendor-cell">
                <span class="vendor-name">{{ i.vendor }}</span>
                <span class="slot-text">{{ formatSlot(i.scheduledStart, i.durationMinutes) }}</span>
              </div>
              <span v-else class="unassigned-text">Unassigned</span>
            </td>

            <td><span class="reports-badge">{{ i.reports.length }}</span></td>

            <td class="date-cell">{{ i.date }}</td>

          </tr>

          <tr v-if="sortedFiltered.length === 0">
            <td colspan="7" class="empty-row">No issues match the selected filters</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- issue detail modal -->
    <div v-if="showDetail" class="modal-overlay" @click.self="closeDetail">
      <div class="modal modal-lg">

        <div class="modal-header">
          <div>
            <h3>{{ selected?.title }}</h3>
            <span class="modal-sub">{{ selected?.id }} · {{ selected?.location }}</span>
          </div>
          <button class="close-btn" @click="closeDetail">✕</button>
        </div>

        <div class="modal-body">

          <div class="badges-row">
            <span class="category-badge">{{ selected?.category }}</span>
            <span :class="['priority-badge', priorityClass(selected?.priority)]">{{ selected?.priority }}</span>
            <span :class="['status-badge', statusClass(selected?.status)]">{{ selected?.status }}</span>
          </div>

          <div v-if="selected?.status === 'Open'" class="ai-chip">
            ✨ AI suggested {{ selected?.aiCategory }} · {{ selected?.aiPriority }} priority
          </div>

          <!-- AI summary + individual reports -->
          <div class="section">
            <span class="section-label">AI Summary · Reported by {{ selected?.reports.length }}</span>
            <p class="ai-summary">{{ selected?.aiSummary }}</p>
            <div class="reports-list">
              <div v-for="(r, idx) in selected?.reports" :key="idx" class="report-card">
                <div class="report-head">
                  <span class="report-resident">{{ r.resident }} · {{ r.flat }}</span>
                  <span class="report-date">{{ r.date }}</span>
                </div>
                <p class="report-desc">{{ r.desc }}</p>
                <span v-if="r.residentPriority" class="resident-priority-tag">
                  Resident marked this {{ r.residentPriority }}
                </span>
              </div>
            </div>
          </div>

          <!-- merge -->
          <div v-if="!['Resolved', 'Rejected'].includes(selected?.status)" class="section merge-section">
            <span class="section-label">Duplicate of another issue?</span>
            <div class="merge-row">
              <select v-model="mergeTarget" class="n-input">
                <option value="">Select an issue to merge into...</option>
                <option v-for="m in mergeableIssues" :key="m.id" :value="m.id">{{ m.id }} — {{ m.title }}</option>
              </select>
              <button class="btn-outline" :disabled="!mergeTarget" @click="confirmMerge">Merge</button>
            </div>
          </div>

          <!-- assign / reschedule -->
          <div v-if="!['Resolved', 'Rejected'].includes(selected?.status)" class="section">
            <span class="section-label">{{ selected?.vendor ? 'Vendor & Schedule' : 'Assign Vendor' }}</span>

            <label>Category</label>
            <select v-model="detailCategory" class="n-input">
              <option v-for="c in categoryOptions.slice(1)" :key="c" :value="c">{{ c }}</option>
            </select>

            <div class="vendor-row">
              <div class="vendor-select-wrap">
                <label>Vendor</label>
                <select v-model="detailVendor" class="n-input">
                  <option value="" disabled>Choose a vendor...</option>
                  <option v-for="v in vendorsForCategory" :key="v.name" :value="v.name">{{ v.name }}</option>
                </select>
              </div>
              <button class="btn-outline ai-suggest-btn" @click="suggestVendorAI">✨ AI Suggest</button>
            </div>
            <p v-if="lastAiNote" class="ai-note">{{ lastAiNote }}</p>

            <div class="slot-row">
              <div class="slot-field">
                <label>Date</label>
                <input type="date" v-model="detailDate" class="n-input" />
              </div>
              <div class="slot-field">
                <label>Time</label>
                <input type="time" v-model="detailTime" class="n-input" />
              </div>
              <div class="slot-field">
                <label>Duration</label>
                <select v-model.number="detailDuration" class="n-input">
                  <option v-for="d in durationOptions" :key="d.minutes" :value="d.minutes">{{ d.label }}</option>
                </select>
              </div>
            </div>

            <div v-if="conflict" class="conflict-warning">
              {{ detailVendor }} is already booked {{ formatSlot(conflict.scheduledStart, conflict.durationMinutes) }}
              for {{ conflict.id }}. Pick a different slot or vendor.
            </div>

            <button
              class="btn-primary"
              :disabled="!detailVendor || !proposedSlot || !!conflict"
              @click="confirmAssign"
            >
              {{ selected?.vendor ? 'Update Assignment' : 'Assign Vendor' }}
            </button>
          </div>

          <!-- complete -->
          <div v-if="selected?.status === 'In Progress'" class="section">
            <span class="section-label">Mark Complete</span>

            <template v-if="needsPayment">
              <label>Payment amount (₹)</label>
              <input type="number" v-model="completePaymentAmount" class="n-input" placeholder="e.g. 800" min="0" />
              <p class="helper-text">{{ completingVendor?.name }} is a per-job vendor — record what was paid before closing.</p>
            </template>
            <template v-else>
              <p class="helper-text">{{ completingVendor?.name }} is salaried staff — no per-task payment needed.</p>
            </template>

            <button
              class="btn-primary btn-complete"
              :disabled="needsPayment && !completePaymentAmount"
              @click="confirmComplete"
            >
              {{ needsPayment ? 'Record Payment & Close' : 'Close Issue' }}
            </button>
          </div>

          <!-- resolved summary -->
          <div v-if="selected?.status === 'Resolved'" class="section">
            <span class="section-label">Resolved</span>
            <div class="resolved-card">
              <span class="vendor-name">{{ selected?.vendor }}</span>
              <span class="slot-text">{{ formatSlot(selected?.scheduledStart, selected?.durationMinutes) }}</span>
              <span v-if="selected?.paymentStatus === 'paid'" class="pay-text pay-paid">Paid ₹{{ selected?.paymentAmount }}</span>
              <span v-else class="pay-text">No payment applicable</span>
            </div>
          </div>

          <!-- reject -->
          <div v-if="selected?.status === 'Open' || selected?.status === 'In Progress'" class="section reject-section">
            <span class="section-label">Reject this issue</span>
            <textarea
              v-model="rejectReason"
              class="n-input n-textarea"
              rows="2"
              placeholder="Reason — invalid, duplicate, not RWA's responsibility, etc."
            ></textarea>
            <button class="btn-outline btn-reject" :disabled="!rejectReason.trim()" @click="confirmReject">
              Reject Issue
            </button>
          </div>

          <!-- rejected summary -->
          <div v-if="selected?.status === 'Rejected'" class="section">
            <span class="section-label">Rejected</span>
            <div class="resolved-card">
              <p class="report-desc">{{ selected?.rejectionReason }}</p>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- toast -->
    <transition name="toast-fade">
      <div v-if="toastVisible" class="toast">
        <span class="toast-check">✓</span>
        <span>{{ toastText }}</span>
      </div>
    </transition>

  </div>
</template>

<style scoped>
.sec-issues {
  max-width: var(--content-max-width);
}

.page-header { margin-bottom: 20px; }

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

/* toolbar */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-input {
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  width: 100%;
  transition: border-color var(--transition-fast);
}

.search-input:focus { border-color: var(--c-600); }

.status-pill-group {
  display: flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 4px;
}

.status-pill {
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.status-pill.active { background: var(--c-800); color: #fff; }

.right-filters {
  display: flex;
  gap: 8px;
  margin-left: auto;
  flex-wrap: wrap;
}

.filter-select {
  height: 36px;
  padding: 0 10px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  outline: none;
  cursor: pointer;
}

/* table */
.table-wrap {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
}

.issues-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.issues-table thead tr { border-bottom: 1px solid var(--color-border); }

.issues-table th {
  padding: 12px 20px;
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  background: var(--color-surface-soft);
  white-space: nowrap;
}

.issues-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.issues-table tbody tr:last-child td { border-bottom: none; }

.issue-row { cursor: pointer; transition: background var(--transition-fast); }
.issue-row:hover { background: var(--color-surface-muted); }

.issue-title {
  display: block;
  font-weight: 700;
  color: var(--color-text-primary);
}

.issue-meta {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 2px;
}

.category-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  background: var(--color-surface-soft);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.priority-badge, .status-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.pri-high   { background: var(--color-danger-bg);  color: var(--color-danger-text);  }
.pri-medium { background: var(--color-warning-bg); color: var(--color-warning-text); }
.pri-low    { background: var(--color-success-bg); color: var(--color-success-text); }

.status-open     { background: var(--color-info-bg);    color: var(--color-info-text);    }
.status-progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-resolved { background: var(--color-success-bg); color: var(--color-success-text); }
.status-rejected { background: var(--color-danger-bg);  color: var(--color-danger-text);  }

.vendor-cell { display: flex; flex-direction: column; gap: 2px; }

.vendor-name { font-weight: 700; color: var(--color-text-primary); }

.slot-text {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text-muted);
}

.unassigned-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.reports-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-secondary);
}

.date-cell { color: var(--color-text-muted); white-space: nowrap; }

.empty-row {
  text-align: center;
  color: var(--color-text-muted);
  padding: 40px;
  font-size: var(--font-size-md);
}

/* modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: 20px;
}

.modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 460px;
  box-shadow: var(--shadow-lg);
}

.modal-lg {
  max-width: 560px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.modal-header h3 { font-size: var(--font-size-xl); font-weight: 700; }

.modal-sub {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 3px;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.close-btn:hover { background: var(--color-border); }

.modal-body {
  padding: 20px 24px 26px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.badges-row { display: flex; gap: 8px; flex-wrap: wrap; }

.ai-chip {
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  background: #F1EAFB;
  color: #6B3FA0;
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.section {
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.section-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 10px;
}

.ai-summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-style: italic;
  line-height: 1.5;
  margin-bottom: 12px;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-card {
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.report-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
}

.report-resident {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-primary);
}

.report-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.report-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.resident-priority-tag {
  display: inline-block;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  font-style: italic;
}

.merge-section { background: transparent; }

.merge-row { display: flex; gap: 8px; }

.merge-row .n-input { flex: 1; }

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
  margin-bottom: 6px;
}

.section > label:first-of-type { margin-top: 0; }

.n-input {
  width: 100%;
  height: 42px;
  padding: 0 13px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  font-family: var(--font-family);
  transition: border-color var(--transition-fast);
}

.n-input:focus { border-color: var(--c-600); }

.n-textarea {
  height: auto;
  min-height: 64px;
  padding: 10px 13px;
  resize: vertical;
  line-height: 1.5;
}

.btn-reject {
  margin-top: 10px;
  width: 100%;
  border-color: var(--color-danger-text);
  color: var(--color-danger-text);
}

.btn-reject:hover:not(:disabled) {
  background: var(--color-danger-bg);
}

.vendor-row { display: flex; align-items: flex-end; gap: 8px; }

.vendor-select-wrap { flex: 1; min-width: 0; }

.ai-suggest-btn { height: 42px; white-space: nowrap; }

.ai-note {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: #6B3FA0;
  margin-top: 8px;
}

.slot-row { display: flex; gap: 10px; margin-top: 4px; }

.slot-field { flex: 1; min-width: 0; }

.conflict-warning {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  font-size: var(--font-size-xs);
  font-weight: 600;
  line-height: 1.5;
}

.helper-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 6px;
  margin-bottom: 12px;
  line-height: 1.5;
}

.btn-primary {
  width: 100%;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 14px;
  transition: background var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: var(--c-900); }

.btn-complete { margin-top: 0; }

.btn-outline {
  height: 42px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--c-800);
  font-size: var(--font-size-sm);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.btn-outline:hover:not(:disabled) { border-color: var(--c-600); background: var(--color-surface-soft); }
.btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }

.resolved-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}

.pay-text { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted); }
.pay-paid { color: var(--color-success-text); }

/* toast */
.toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: var(--radius-md);
  background: var(--color-success-bg);
  color: var(--color-success-text);
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: var(--shadow-lg);
  z-index: var(--z-modal);
}

.toast-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-success-text);
  color: #fff;
  font-size: 11px;
  flex-shrink: 0;
}

.toast-fade-enter-active, .toast-fade-leave-active {
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.toast-fade-enter-from, .toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
}
</style>