<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../../api/axios' // adjust path if this view lives elsewhere

/* ---------------- Filters ---------------- */

const filterStatus   = ref('Open')
const filterCategory = ref('all')
const filterPriority = ref('all')
const sortBy         = ref('priority-desc')
const searchQuery    = ref('')

const statusFilters   = ['All', 'Open', 'In Progress', 'Resolved', 'Rejected']
// ADDED: Security, Gardening, Pest Control — matches the expanded
// CommunityIssue.category enum
const categoryOptions = ['all', 'Plumbing', 'Electrical', 'Cleaning', 'Carpentry', 'Security', 'Gardening', 'Pest Control', 'Other']
const priorityOptions = ['all', 'High', 'Medium', 'Low']
const priorityRank    = { High: 3, Medium: 2, Low: 1 }

const durationOptions = [
  { label: '30 mins', minutes: 30 },
  { label: '1 hr',     minutes: 60 },
  { label: '1.5 hr',   minutes: 90 },
  { label: '2 hr',     minutes: 120 },
  { label: '3 hr',     minutes: 180 },
]

/* ---------------- Backend <-> UI mapping ----------------
   Issue category/priority are just cased differently from the backend
   ('plumbing' -> 'Plumbing'). 'pest_control' needs its own case since it's
   two words. Status needs an explicit map because the backend has no
   'rejected' value — we repurpose 'closed' for it, since CommunityIssue
   .status only has open/in_progress/resolved/closed. */

const STATUS_TO_FRONTEND = { open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', closed: 'Rejected' }

function capitalize(s) {
  if (!s) return s
  if (s === 'pest_control') return 'Pest Control'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// reverse of capitalize — used when sending filters/category back to the API
function toBackendCategory(c) {
  if (!c) return c
  return c.toLowerCase().replace(' ', '_')
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

// the backend returns naive datetime strings with no trailing 'Z'/offset,
// but they're always UTC instants (we only ever send UTC via toISOString())
// — mark them explicitly so `new Date(...)` doesn't misread them as local time
function asUtcIso(s) {
  if (!s) return s
  return /[Zz]|[+-]\d\d:\d\d$/.test(s) ? s : s + 'Z'
}

// a vendor's category is the *profession* ('plumber'); an issue's category is
// the *problem type* ('plumbing') — different enums, so assigning a vendor
// needs this explicit mapping to find who's actually suited to the job
const ISSUE_TO_VENDOR_CATEGORY = {
  Plumbing: 'plumber', Electrical: 'electrician', Carpentry: 'carpenter',
  Cleaning: 'cleaner', Security: 'security', Gardening: 'gardener',
  'Pest Control': 'pest_control', Other: 'other',
}

/* ---------------- Vendors ---------------- */
// engagementType: 'per_job' -> paid per completed task (plumbers, electricians, etc.)
//                 'salaried' -> fixed monthly salary, no per-task payment
const vendors = ref([])

async function fetchVendors() {
  try {
    const res = await api.get('/vendors', { params: { status: 'active' } })
    vendors.value = (res.data.vendors || []).map(v => ({
      id: v.id,
      name: v.name,
      category: v.category,
      engagementType: v.is_salaried ? 'salaried' : 'per_job',
      salary: v.salary,
    }))
  } catch (err) {
    console.error('Failed to load vendors', err)
  }
}

function vendorByName(name) {
  return vendors.value.find(v => v.name === name) || null
}

// Mock AI time estimates per category - replace with real model output in Sprint 1
const estimatedMinutesByCategory = {
  Plumbing: 60,
  Electrical: 45,
  Carpentry: 90,
  Cleaning: 45,
  Security: 30,
  Gardening: 60,
  'Pest Control': 60,
  Other: 90,
}

/* ---------------- Residents (flat lookup for the reports list) ---------------- */

const residentFlats = ref({})

async function fetchResidentFlats() {
  try {
    const res = await api.get('/auth/residents')
    const map = {}
    for (const r of (res.data.residents || [])) map[r.id] = r.flat_number || '—'
    residentFlats.value = map
  } catch (err) {
    console.error('Failed to load resident flats', err)
  }
}

/* ---------------- Funds (paying non-salaried vendors on completion) ----------------
   Same "Operating first, unlock other funds only if Operating can't cover
   it" logic as the Society Funds page's manual transaction form. */

const funds = ref([])

async function fetchFunds() {
  try {
    const res = await api.get('/funds')
    funds.value = res.data.funds || []
  } catch (err) {
    console.error('Failed to load funds', err)
  }
}

function fundLabel(name) {
  const map = { operating: 'Operating Fund', sinking: 'Sinking Fund', contingency: 'Contingency Fund' }
  return map[name] || name
}

/* ---------------- Issues (community / common-area only) ---------------- */
// Personal, inside-the-flat complaints never appear here — they live in the
// resident's own complaint history. Only common-area issues reach this list.
// Multiple residents can report the same issue, so each issue carries a
// `reports` array instead of a single resident.

// CommunityIssue has no payment or rejection-reason columns yet, so both are
// kept client-side only, keyed by issue id — they reset on page reload.
const localPayments     = ref({}) // issueId -> { status, amount, fund }
const rejectionReasons  = ref({}) // issueId -> reason text

const issues = ref([])
const loading = ref(true)
const loadError = ref('')

function mapIssue(i) {
  const vendorObj = vendors.value.find(v => v.id === i.vendor_id)
  const payment = localPayments.value[i.id]
  return {
    id: i.id,
    title: i.title,
    location: i.location || '—',
    category: capitalize(i.category),
    aiCategory: capitalize(i.ai_suggested_category || i.category),
    priority: capitalize(i.priority),
    aiPriority: capitalize(i.ai_suggested_priority || i.priority),
    status: STATUS_TO_FRONTEND[i.status] || i.status,
    vendor: vendorObj ? vendorObj.name : null,
    scheduledStart: asUtcIso(i.vendor_start_time),
    durationMinutes: (i.vendor_start_time && i.vendor_end_time)
      ? Math.round((new Date(asUtcIso(i.vendor_end_time)) - new Date(asUtcIso(i.vendor_start_time))) / 60000)
      : null,
    paymentStatus: payment?.status ?? null,
    paymentAmount: payment?.amount ?? null,
    paymentFund: payment?.fund ?? null,
    date: formatDate(i.created_at),
    aiSummary: i.ai_suggested_description || i.description,
    rejectionReason: rejectionReasons.value[i.id] || null,
    reports: (i.reporters || []).map(r => ({
      resident: r.resident_name || 'Resident',
      flat: residentFlats.value[r.resident_id] || '—',
      desc: r.description,
      date: formatDate(r.created_at),
      residentPriority: null,
    })),
  }
}

async function fetchIssues() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/complaints')
    issues.value = (res.data.complaints || []).map(mapIssue)
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load issues'
    console.error('Failed to load issues', err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchVendors()
  await fetchResidentFlats()
  await fetchFunds()
  await fetchIssues()
})

// FIX: this computed was missing entirely — filtered/openCount/unassignedCount/
// mergeableIssues all depend on it, causing a ReferenceError and blank screen.
const visibleIssues = computed(() => issues.value.filter(i => i.status !== 'Merged'))

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return visibleIssues.value.filter(i => {
    // "Open" pill also includes "In Progress" — secretary wants to see
    // everything still active, not just brand-new unassigned issues.
    const matchesStatus = filterStatus.value === 'All'
      || (filterStatus.value === 'Open'
            ? ['Open', 'In Progress'].includes(i.status)
            : i.status === filterStatus.value)
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

const openCount       = computed(() => visibleIssues.value.filter(i => ['Open', 'In Progress'].includes(i.status)).length)
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
const completeFundName      = ref('operating')
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
  completeFundName.value = 'operating'
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
  if (detailVendor.value && vendorByName(detailVendor.value)?.category !== ISSUE_TO_VENDOR_CATEGORY[detailCategory.value]) {
    detailVendor.value = ''
  }
})

const vendorsForCategory = computed(() =>
  vendors.value.filter(v => v.category === ISSUE_TO_VENDOR_CATEGORY[detailCategory.value])
)

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

async function confirmAssign() {
  if (!detailVendor.value || !proposedSlot.value || conflict.value) return
  const issue = selected.value
  const vendorObj = vendorByName(detailVendor.value)
  if (!vendorObj) return

  const wasUnassigned = !issue.vendor
  const { start, end } = proposedSlot.value

  try {
    await api.patch(`/complaints/${issue.id}/assign`, {
      vendor_id:         vendorObj.id,
      vendor_start_time: start.toISOString(),
      vendor_end_time:   end.toISOString(),
    })
    await fetchIssues()
    showToast(wasUnassigned ? `${issue.title} — vendor assigned` : `${issue.title} — schedule changed`)
    closeDetail()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to assign vendor')
  }
}

/* ---------------- Complete / payment ---------------- */

const completingVendor = computed(() => vendorByName(selected.value?.vendor))
const needsPayment      = computed(() => completingVendor.value?.engagementType === 'per_job')

// Operating is the default source. Other funds unlock only if Operating's
// balance can't cover the amount currently being entered — mirrors the
// Society Funds page's debit-fund logic exactly.
const completeFundOptions = computed(() => {
  const operating = funds.value.find(f => f.fund_name === 'operating')
  const amount = Number(completePaymentAmount.value) || 0
  const operatingInsufficient = !operating || operating.balance < amount
  return operatingInsufficient
  ? [...funds.value].sort((a, b) => (a.fund_name === 'operating' ? -1 : b.fund_name === 'operating' ? 1 : 0))
  : funds.value.filter(f => f.fund_name === 'operating')
})

// Keep the selected fund valid if the available options change (e.g. user
// picked a non-Operating fund, then lowered the amount so Operating becomes
// sufficient again).
watch(completeFundOptions, (options) => {
  if (needsPayment.value && !options.some(f => f.fund_name === completeFundName.value)) {
    completeFundName.value = options[0]?.fund_name || ''
  }
})
const selectedFundInsufficient = computed(() => {
  if (!needsPayment.value || !completeFundName.value) return null
  const fund = funds.value.find(f => f.fund_name === completeFundName.value)
  const amount = Number(completePaymentAmount.value) || 0
  if (!fund || amount <= 0) return null
  return fund.balance < amount
    ? { balance: fund.balance, short: amount - fund.balance }
    : null
})

async function confirmComplete() {
  if (needsPayment.value && (!completePaymentAmount.value || !completeFundName.value)) return
  const issue = selected.value

  try {
    if (needsPayment.value) {
      // debit the chosen fund before closing the issue, same endpoint the
      // Society Funds page uses for manual transactions
      await api.post('/funds/transactions', {
        type: 'debit',
        fund_name: completeFundName.value,
        amount: Number(completePaymentAmount.value),
        description: `Vendor payment — ${completingVendor.value?.name} — ${issue.title} (${issue.id})`,
      })
    }

    await api.patch(`/complaints/${issue.id}/status`, { status: 'resolved' })

    // no payment column on CommunityIssue yet — remembered client-side only
    localPayments.value = {
      ...localPayments.value,
      [issue.id]: needsPayment.value
        ? { status: 'paid', amount: Number(completePaymentAmount.value), fund: completeFundName.value }
        : { status: 'not_applicable', amount: null, fund: null },
    }

    await fetchIssues()
    if (needsPayment.value) await fetchFunds() // balances just changed
    showToast(
      `${issue.title} — closed` +
      (needsPayment.value ? ` and ₹${completePaymentAmount.value} paid from ${fundLabel(completeFundName.value)}` : '')
    )
    closeDetail()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to close issue')
  }
}

/* ---------------- Merge ---------------- */

const mergeableIssues = computed(() =>
  visibleIssues.value.filter(i => i.id !== selected.value?.id && !['Resolved', 'Rejected'].includes(i.status))
)

async function confirmMerge() {
  if (!mergeTarget.value) return
  const target = issues.value.find(i => i.id === mergeTarget.value)
  const current = selected.value
  if (!target || !current) return

  try {
    await api.post(`/complaints/${target.id}/merge`, { other_issue_id: current.id })
    await fetchIssues()
    showToast(`${current.title} merged into ${target.title}`)
    closeDetail()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to merge issues')
  }
}

/* ---------------- Reject ---------------- */

async function confirmReject() {
  if (!rejectReason.value.trim()) return
  const issue = selected.value

  try {
    // backend has no dedicated 'rejected' status — 'closed' is the closest
    // terminal state that isn't 'resolved', so we repurpose it and label it
    // "Rejected" in the UI (see STATUS_TO_FRONTEND)
    await api.patch(`/complaints/${issue.id}/status`, { status: 'closed' })

    // no rejection-reason column on CommunityIssue yet — remembered client-side only
    rejectionReasons.value = { ...rejectionReasons.value, [issue.id]: rejectReason.value.trim() }

    await fetchIssues()
    showToast(`${issue.title} rejected`)
    closeDetail()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to reject issue')
  }
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
                <option v-for="m in mergeableIssues" :key="m.id" :value="m.id">{{ m.title }} - {{ m.id }} </option>
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

              <label>Pay from</label>
              <select v-model="completeFundName" class="n-input">
                <option v-for="f in completeFundOptions" :key="f.fund_name" :value="f.fund_name">{{ fundLabel(f.fund_name) }}</option>
              </select>
              <p v-if="selectedFundInsufficient" class="helper-text" style="color: var(--color-danger-text);">
                {{ fundLabel(completeFundName) }} only has ₹{{ selectedFundInsufficient.balance }} — ₹{{ selectedFundInsufficient.short }} short of ₹{{ completePaymentAmount }}. You can still proceed, or pick a different fund.
              </p>

              <p class="helper-text">{{ completingVendor?.name }} is a per-job vendor — record what was paid before closing.</p>
            </template>
            <template v-else>
              <p class="helper-text">{{ completingVendor?.name }} is salaried staff — no per-task payment needed.</p>
            </template>

            <button
              class="btn-primary btn-complete"
              :disabled="needsPayment && (!completePaymentAmount || !completeFundName)"
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
              <span v-if="selected?.paymentStatus === 'paid'" class="pay-text pay-paid">
                Paid ₹{{ selected?.paymentAmount }}{{ selected?.paymentFund ? ` from ${fundLabel(selected.paymentFund)}` : '' }}
              </span>
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