<script setup>
import { ref, computed } from 'vue'

/* ---------------------------------------------------------------
   Document Requests — Secretary view.
   Frontend-only mock; replace with API calls when the backend is ready.
--------------------------------------------------------------- */

const activeTab     = ref('all')
const selectedFiles = ref({})
const uploading     = ref({})
const rowError      = ref({})

const tabs = [
  { value: 'all',       label: 'All' },
  { value: 'requested', label: 'Requested' },
  { value: 'ready',     label: 'Ready' },
  { value: 'delivered', label: 'Delivered' },
]

// Mock data for sec doc view
const requests = ref([
  { id: 1, resident: 'Ravi Kumar',   flat: 'A-402', type: 'NOC',             reason: 'Bank loan application', status: 'ready',     requested_at: '10 Jul 2026' },
  { id: 2, resident: 'Jatin Kumar',  flat: 'B-201', type: 'Payment Receipt', reason: 'Tax filing',            status: 'requested', requested_at: '15 Jul 2026' },
  { id: 3, resident: 'Meena Sharma', flat: 'B-301', type: 'Other',           reason: 'Society membership',    status: 'delivered', requested_at: '5 Jul 2026'  },
])

const filtered = computed(() => {
  if (activeTab.value === 'all') return requests.value
  return requests.value.filter(r => r.status === activeTab.value)
})

const countFor = (status) =>
  status === 'all' ? requests.value.length : requests.value.filter(r => r.status === status).length

function onFileSelected(r, event) {
  selectedFiles.value[r.id] = event.target.files[0] || null
  rowError.value[r.id] = ''
}

function markReady(r) {
  rowError.value[r.id] = ''
  const file = selectedFiles.value[r.id]

  if (!file) {
    rowError.value[r.id] = 'Choose a file first'
    return
  }

  uploading.value[r.id] = true
  // mock "upload" — just simulate a short delay and flip status locally
  setTimeout(() => {
    r.status = 'ready'
    r.file_name = file.name
    delete selectedFiles.value[r.id]
    uploading.value[r.id] = false
  }, 500)
}

function markDelivered(r) {
  r.status = 'delivered'
}

function statusLabel(status) {
  const map = { requested: 'Requested', in_progress: 'In Progress', ready: 'Ready', delivered: 'Delivered' }
  return map[status] || status
}
</script>

<template>
  <div class="sec-documents">

    <div class="page-header">
      <div>
        <h2>Document Requests</h2>
        <p class="page-sub">Review resident document requests and mark them ready</p>
      </div>
    </div>

    <div class="tab-bar">
      <button
        v-for="t in tabs"
        :key="t.value"
        :class="['tab-btn', { active: activeTab === t.value }]"
        @click="activeTab = t.value"
      >
        {{ t.label }}
        <span class="tab-count">{{ countFor(t.value) }}</span>
      </button>
    </div>

    <div class="table-wrap">
      <table class="requests-table">
        <thead>
          <tr>
            <th>Resident</th>
            <th>Type</th>
            <th>Reason</th>
            <th>Requested</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filtered" :key="r.id">
            <td class="resident-cell">
              {{ r.resident }}
              <span class="flat-tag">{{ r.flat }}</span>
            </td>
            <td>{{ r.type }}</td>
            <td class="reason-cell">{{ r.reason || '—' }}</td>
            <td class="date-cell">{{ r.requested_at }}</td>
            <td>
              <span :class="['status-chip', 'status-' + r.status]">{{ statusLabel(r.status) }}</span>
            </td>
            <td class="action-cell">
              <div v-if="r.status === 'requested'" class="upload-row">
                <input
                  type="file"
                  accept=".pdf,image/*"
                  class="file-input"
                  @change="onFileSelected(r, $event)"
                />
                <button class="ready-btn" :disabled="uploading[r.id]" @click="markReady(r)">
                  {{ uploading[r.id] ? 'Uploading...' : 'Mark Ready' }}
                </button>
              </div>
              <button v-else-if="r.status === 'ready'" class="deliver-btn" @click="markDelivered(r)">
                Mark Delivered
              </button>
              <span v-else class="done-label">—</span>
              <p v-if="rowError[r.id]" class="row-error">{{ rowError[r.id] }}</p>
            </td>
          </tr>

          <tr v-if="filtered.length === 0">
            <td colspan="6" class="empty-row">No document requests</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
.sec-documents { max-width: var(--content-max-width); }

.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-muted);
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
}

.tab-btn:hover { color: var(--c-800); }

.tab-btn.active {
  color: var(--c-800);
  border-bottom-color: var(--c-800);
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.tab-btn.active .tab-count {
  background: var(--c-800);
  color: #fff;
}

.table-wrap {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
}

.requests-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }

.requests-table th {
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

.requests-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.requests-table tbody tr:last-child td { border-bottom: none; }
.requests-table tbody tr:hover { background: var(--color-surface-muted); }

.resident-cell { font-weight: 700; color: var(--color-text-primary); white-space: nowrap; }

.flat-tag {
  margin-left: 8px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
}

.reason-cell { color: var(--color-text-secondary); max-width: 240px; }
.date-cell { color: var(--color-text-secondary); white-space: nowrap; }

.status-chip {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
}

.status-chip.status-requested   { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-chip.status-in_progress { background: var(--color-info-bg);    color: var(--color-info-text);    }
.status-chip.status-ready       { background: var(--color-success-bg); color: var(--color-success-text); }
.status-chip.status-delivered   { background: var(--badge-closed-bg);  color: var(--badge-closed-text);  }

.action-cell { min-width: 260px; }

.upload-row { display: flex; gap: 8px; align-items: center; }

.file-input {
  flex: 1;
  min-width: 160px;
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
}

.ready-btn {
  height: 36px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.ready-btn:hover:not(:disabled) { background: var(--c-900); }
.ready-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.deliver-btn {
  height: 36px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  background: var(--color-success);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 700;
  transition: opacity var(--transition-fast);
}

.deliver-btn:hover { opacity: 0.9; }

.done-label { color: var(--color-text-muted); }

.row-error { font-size: var(--font-size-xs); color: var(--color-danger); margin-top: 6px; }

.empty-row { text-align: center; color: var(--color-text-muted); padding: 40px; font-size: var(--font-size-md); }
</style>