<script setup>
import { ref, computed } from 'vue'

const filterStatus = ref('all')
const searchQuery = ref('')

const statuses = ['all', 'assigned', 'in_progress', 'completed', 'declined']

// mock data - replace with API call in Sprint 1
const jobs = ref([
  {
    id: 'CMP-2043',
    flat: 'A-402',
    block: 'A Wing',
    category: 'plumber',
    description: 'Water leakage under kitchen sink',
    vendor_name: 'Kishore Plumbing',
    vendor_phone: '+91 98480 11223',
    assigned_date: '28 Jun 2026',
    deadline: '30 Jun 2026',
    status: 'in_progress',
    whatsapp_status: 'accepted',
  },
  {
    id: 'CMP-2044',
    flat: 'B-201',
    block: 'B Wing',
    category: 'electrician',
    description: 'Main switch tripping repeatedly',
    vendor_name: 'Raju Electricals',
    vendor_phone: '+91 97400 33441',
    assigned_date: '29 Jun 2026',
    deadline: '1 Jul 2026',
    status: 'assigned',
    whatsapp_status: 'notified',
  },
  {
    id: 'CMP-2040',
    flat: 'C-105',
    block: 'C Wing',
    category: 'carpenter',
    description: 'Bedroom door hinge broken',
    vendor_name: 'Suresh Carpentry',
    vendor_phone: '+91 96300 22110',
    assigned_date: '25 Jun 2026',
    deadline: '27 Jun 2026',
    status: 'completed',
    whatsapp_status: 'accepted',
  },
  {
    id: 'CMP-2038',
    flat: 'D-303',
    block: 'D Wing',
    category: 'plumber',
    description: 'Low water pressure in bathroom',
    vendor_name: 'Kishore Plumbing',
    vendor_phone: '+91 98480 11223',
    assigned_date: '24 Jun 2026',
    deadline: '26 Jun 2026',
    status: 'declined',
    whatsapp_status: 'declined',
  },
  {
    id: 'CMP-2050',
    flat: 'A-110',
    block: 'A Wing',
    category: 'electrician',
    description: 'Ceiling fan not working in living room',
    vendor_name: 'Raju Electricals',
    vendor_phone: '+91 97400 33441',
    assigned_date: '30 Jun 2026',
    deadline: '2 Jul 2026',
    status: 'assigned',
    whatsapp_status: 'notified',
  },
])

const filteredJobs = computed(() => {
  return jobs.value.filter(j => {
    const matchesStatus = filterStatus.value === 'all' || j.status === filterStatus.value
    const matchesSearch = j.id.toLowerCase().includes(searchQuery.value.toLowerCase())
      || j.flat.toLowerCase().includes(searchQuery.value.toLowerCase())
      || j.vendor_name.toLowerCase().includes(searchQuery.value.toLowerCase())
      || j.description.toLowerCase().includes(searchQuery.value.toLowerCase())
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
            <th>Flat</th>
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
            <td>
              <span class="flat-label">{{ job.flat }}</span>
              <span class="block-label">{{ job.block }}</span>
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