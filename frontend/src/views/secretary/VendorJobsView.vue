<script setup>
import { ref, computed, onMounted } from 'vue'

const API = 'http://localhost:5000/api'

const filterStatus = ref('all')
const searchQuery = ref('')

const statuses = ['all', 'assigned', 'in_progress', 'completed', 'declined']

/* ---------------- Fetch real data ----------------
   Vendor Jobs is a read-only filtered view of CommunityIssue rows that have
   a vendor assigned — no separate backend route needed, it reuses the same
   /api/complaints and /api/vendors endpoints SecComplaintsView.vue uses. */

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s }

// backend datetimes come back naive but are always UTC instants (no 'Z') —
// tag them explicitly so `new Date(...)` doesn't misread them as local time
function asUtcIso(s) {
  if (!s) return s
  return /[Zz]|[+-]\d\d:\d\d$/.test(s) ? s : s + 'Z'
}

function formatDateLong(iso) {
  if (!iso) return '—'
  return new Date(asUtcIso(iso)).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

// CommunityIssue.status has no 'assigned'/'declined' values — reconstruct
// the 4 job states from status + vendor_whatsapp_status instead of adding
// new columns: resolved -> completed, closed -> declined, and whatsapp
// acceptance distinguishes "assigned" (notified, not yet started) from
// "in_progress" (vendor accepted)
function jobStatus(issue) {
  if (issue.status === 'resolved') return 'completed'
  if (issue.status === 'closed') return 'declined'
  if (issue.vendor_whatsapp_status === 'accepted') return 'in_progress'
  return 'assigned'
}

const vendors = ref([])

async function fetchVendors() {
  const res = await fetch(`${API}/vendors?status=`, { credentials: 'include' })
  const data = await res.json()
  vendors.value = data.vendors || []
}

function vendorById(id) {
  return vendors.value.find(v => v.id === id) || null
}

const jobs = ref([])

async function fetchJobs() {
  const res = await fetch(`${API}/complaints`, { credentials: 'include' })
  const data = await res.json()
  jobs.value = (data.complaints || [])
    .filter(i => i.vendor_id)
    .map(i => {
      const vendor = vendorById(i.vendor_id)
      return {
        id: i.id,
        location: i.location || '—',
        // the vendor's profession (plumber, electrician, ...) reads better
        // here than the issue's problem-type category (plumbing, electrical)
        category: vendor ? capitalize(vendor.category) : capitalize(i.category),
        description: i.description,
        vendor_name: vendor ? vendor.name : '—',
        vendor_phone: vendor ? vendor.phone : '—',
        deadline: formatDateLong(i.vendor_end_time),
        status: jobStatus(i),
        whatsapp_status: i.vendor_whatsapp_status || 'no_response',
      }
    })
}

onMounted(async () => {
  await fetchVendors()
  await fetchJobs()
})

const filteredJobs = computed(() => {
  return jobs.value.filter(j => {
    const matchesStatus = filterStatus.value === 'all' || j.status === filterStatus.value
    const q = searchQuery.value.toLowerCase()
    const matchesSearch = !q
      || j.id.toLowerCase().includes(q)
      || j.location.toLowerCase().includes(q)
      || j.vendor_name.toLowerCase().includes(q)
      || j.description.toLowerCase().includes(q)
    return matchesStatus && matchesSearch
  })
})

// summary counts for the top cards
const summary = computed(() => ({
  total:       jobs.value.length,
  assigned:    jobs.value.filter(j => j.status === 'assigned').length,
  in_progress: jobs.value.filter(j => j.status === 'in_progress').length,
  completed:   jobs.value.filter(j => j.status === 'completed').length,
  declined:    jobs.value.filter(j => j.status === 'declined').length,
}))

function statusLabel(status) {
  const map = {
    assigned:    'Assigned',
    in_progress: 'In Progress',
    completed:   'Completed',
    declined:    'Declined',
  }
  return map[status] || status
}

function whatsappLabel(status) {
  const map = {
    notified:  'Notified',
    accepted:  'Accepted',
    declined:  'Declined',
    no_response: 'No Response',
  }
  return map[status] || status
}
</script>

<template>
  <div class="vendor-jobs">

    <!-- header -->
    <div class="page-header">
      <div>
        <h2>Vendor Jobs</h2>
        <p class="page-sub">Track all assigned vendor jobs and their current status</p>
      </div>
    </div>

    <!-- summary cards -->
    <div class="summary-grid">
      <div class="summary-card" @click="filterStatus = 'all'">
        <span class="summary-value">{{ summary.total }}</span>
        <span class="summary-label">Total Jobs</span>
      </div>
      <div class="summary-card assigned" @click="filterStatus = 'assigned'">
        <span class="summary-value">{{ summary.assigned }}</span>
        <span class="summary-label">Assigned</span>
      </div>
      <div class="summary-card in-progress" @click="filterStatus = 'in_progress'">
        <span class="summary-value">{{ summary.in_progress }}</span>
        <span class="summary-label">In Progress</span>
      </div>
      <div class="summary-card completed" @click="filterStatus = 'completed'">
        <span class="summary-value">{{ summary.completed }}</span>
        <span class="summary-label">Completed</span>
      </div>
      <div class="summary-card declined" @click="filterStatus = 'declined'">
        <span class="summary-value">{{ summary.declined }}</span>
        <span class="summary-label">Declined</span>
      </div>
    </div>

    <!-- toolbar -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by complaint ID, flat, vendor..."
        class="search-input"
      />
      <div class="status-filters">
        <button
          v-for="s in statuses"
          :key="s"
          :class="['filter-btn', { active: filterStatus === s }]"
          @click="filterStatus = s"
        >
          {{ s === 'all' ? 'All' : statusLabel(s) }}
        </button>
      </div>
    </div>

    <!-- jobs table -->
    <div class="table-wrap">
      <table class="jobs-table">
        <thead>
          <tr>
            <th>Complaint ID</th>
            <th>Location</th>
            <th>Category</th>
            <th>Description</th>
            <th>Vendor</th>
            <th>WhatsApp</th>
            <th>Deadline</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in filteredJobs" :key="job.id">
            <td class="job-id">{{ job.id }}</td>
            <td class="description-cell">
              <span class="flat-label">{{ job.location }}</span>
            </td>
            <td class="capitalize">{{ job.category }}</td>
            <td class="description-cell">{{ job.description }}</td>
            <td>
              <span class="vendor-label">{{ job.vendor_name }}</span>
              <span class="phone-label">{{ job.vendor_phone }}</span>
            </td>
            <td>
              <span :class="['wa-badge', job.whatsapp_status]">
                {{ whatsappLabel(job.whatsapp_status) }}
              </span>
            </td>
            <td class="deadline-cell">{{ job.deadline }}</td>
            <td>
              <span :class="['status-chip', job.status]">
                {{ statusLabel(job.status) }}
              </span>
            </td>
          </tr>

          <!-- empty state -->
          <tr v-if="filteredJobs.length === 0">
            <td colspan="8" class="empty-row">
              No jobs found for the selected filter
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
.vendor-jobs {
  max-width: var(--content-max-width);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.summary-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: box-shadow var(--transition-fast);
}

.summary-card:hover {
  box-shadow: var(--shadow-md);
}

.summary-value {
  font-size: var(--font-size-4xl);
  font-weight: 800;
  color: var(--color-text-primary);
  letter-spacing: -0.5px;
}

.summary-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 600;
}

.summary-card.assigned    .summary-value { color: var(--c-800); }
.summary-card.in-progress .summary-value { color: var(--color-warning); }
.summary-card.completed   .summary-value { color: var(--color-success); }
.summary-card.declined    .summary-value { color: var(--color-danger); }

.toolbar {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
}

.search-input:focus {
  border-color: var(--c-600);
}

.status-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.filter-btn.active {
  background: var(--c-800);
  border-color: var(--c-800);
  color: #fff;
}

.table-wrap {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.jobs-table thead tr {
  border-bottom: 1px solid var(--color-border);
}

.jobs-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.jobs-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.jobs-table tbody tr:last-child td {
  border-bottom: none;
}

.jobs-table tbody tr:hover {
  background: var(--color-surface-muted);
}

.job-id {
  font-weight: 700;
  color: var(--c-800);
  white-space: nowrap;
}

.flat-label {
  display: block;
  font-weight: 600;
  color: var(--color-text-primary);
}

.block-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.capitalize {
  text-transform: capitalize;
}

.description-cell {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vendor-label {
  display: block;
  font-weight: 600;
}

.phone-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.deadline-cell {
  white-space: nowrap;
  color: var(--color-text-secondary);
}

.wa-badge {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.wa-badge.notified    { background: var(--color-info-bg);    color: var(--color-info-text); }
.wa-badge.accepted    { background: var(--color-success-bg); color: var(--color-success-text); }
.wa-badge.declined    { background: var(--color-danger-bg);  color: var(--color-danger-text); }
.wa-badge.no_response { background: var(--badge-closed-bg);  color: var(--badge-closed-text); }

.status-chip {
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
}

.status-chip.assigned    { background: var(--color-info-bg);    color: var(--color-info-text); }
.status-chip.in_progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-chip.completed   { background: var(--color-success-bg); color: var(--color-success-text); }
.status-chip.declined    { background: var(--color-danger-bg);  color: var(--color-danger-text); }

.empty-row {
  text-align: center;
  color: var(--color-text-muted);
  padding: 40px;
  font-size: var(--font-size-md);
}
</style>