<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

const activeTab     = ref('all')
const selectedFiles = ref({})
const uploading     = ref({})
const rowError      = ref({})
const loading       = ref(true)
const loadError     = ref('')

const tabs = [
  { value: 'all',       label: 'All' },
  { value: 'requested', label: 'Requested' },
  { value: 'ready',     label: 'Ready' },
  { value: 'delivered', label: 'Delivered' },
]

const requests = ref([])

async function loadRequests() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/document-requests')
    requests.value = res.data.requests
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load requests'
  } finally {
    loading.value = false
  }
}

onMounted(loadRequests)

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

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload  = () => resolve(reader.result.split(',')[1]) // strip the data: prefix
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function markReady(r) {
  rowError.value[r.id] = ''
  const file = selectedFiles.value[r.id]

  if (!file) {
    rowError.value[r.id] = 'Choose a file first'
    return
  }

  uploading.value[r.id] = true
  try {
    const base64 = await fileToBase64(file)
    const res = await api.patch(`/document-requests/${r.id}/upload`, {
      filename: file.name,
      file_data: base64,
    })
    Object.assign(r, res.data.request)
    delete selectedFiles.value[r.id]
  } catch (err) {
    rowError.value[r.id] = err.response?.data?.error || 'Upload failed'
  } finally {
    uploading.value[r.id] = false
  }
}

async function markDelivered(r) {
  rowError.value[r.id] = ''
  try {
    const res = await api.patch(`/document-requests/${r.id}/deliver`)
    Object.assign(r, res.data.request)
  } catch (err) {
    rowError.value[r.id] = err.response?.data?.error || 'Failed to mark delivered'
  }
}

function statusLabel(status) {
  const map = { requested: 'Requested', in_progress: 'In Progress', ready: 'Ready', delivered: 'Delivered' }
  return map[status] || status
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
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

    <p v-if="loadError" class="row-error">{{ loadError }}</p>

    <div v-if="loading" class="empty-row"><p>Loading...</p></div>

    <div v-else class="table-wrap">
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
              {{ r.resident_name }}
              <span class="flat-tag">{{ r.flat_number || '—' }}</span>
            </td>
            <td>{{ r.type }}</td>
            <td class="reason-cell">{{ r.reason || '—' }}</td>
            <td class="date-cell">{{ formatDate(r.requested_at) }}</td>
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

          <tr v-if="filtered.length === 0 && !loading">
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