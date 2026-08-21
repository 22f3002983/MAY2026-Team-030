<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

const successMsg = ref('')
const submitting = ref(false)
const formError  = ref('')
const loadError  = ref('')
const loading    = ref(true)

const form = ref({ type: 'noc', reason: '' })

const typeOptions = [
  { value: 'noc',             label: 'NOC' },
  { value: 'payment_receipt', label: 'Payment Receipt' },
  { value: 'other',           label: 'Other' },
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

async function submitRequest() {
  formError.value  = ''
  successMsg.value = ''

  if (!form.value.reason.trim()) {
    formError.value = 'Please describe why you need this document'
    return
  }

  submitting.value = true
  try {
    await api.post('/document-requests', {
      type: form.value.type,
      reason: form.value.reason.trim(),
    })
    form.value = { type: 'noc', reason: '' }
    successMsg.value = 'Document request submitted successfully'
    await loadRequests()
    setTimeout(() => successMsg.value = '', 5000)
  } catch (err) {
    formError.value = err.response?.data?.error || 'Failed to submit request'
  } finally {
    submitting.value = false
  }
}

// ADDED — status filter for the requests panel
const statusFilters = [
  { value: 'all',         label: 'All' },
  { value: 'requested',   label: 'Requested' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'ready',       label: 'Ready' },
  { value: 'delivered',   label: 'Delivered' },
]
const filterStatus = ref('all')

const filteredRequests = computed(() => {
  if (filterStatus.value === 'all') return requests.value
  return requests.value.filter(r => r.status === filterStatus.value)
})

function typeLabel(type) {
  return typeOptions.find(t => t.value === type)?.label || type
}

function statusLabel(status) {
  const map = { requested: 'Requested', in_progress: 'In Progress', ready: 'Ready', delivered: 'Delivered' }
  return map[status] || status
}

function statusClass(status) {
  return 'status-' + status
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function downloadFile(r) {
  window.open(`http://localhost:5000/api/document-requests/${r.id}/download`, '_blank')
}
</script>

<template>
  <div class="documents-view">

    <div class="page-header">
      <div>
        <h2>Documents</h2>
        <p class="page-sub">Request official documents from your secretary</p>
      </div>
    </div>

    <div class="two-col">

      <!-- left: new request form -->
      <div class="form-card">
        <h3 class="form-title">New request</h3>

        <label>Document type</label>
        <select v-model="form.type" class="n-input">
          <option v-for="t in typeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>

        <label>Reason</label>
        <textarea
          v-model="form.reason"
          class="n-input n-textarea"
          placeholder="Briefly describe why you need this document"
          rows="3"
        ></textarea>

        <p v-if="formError" class="error-msg">{{ formError }}</p>
        <p v-if="successMsg" class="success-msg">✓ {{ successMsg }}</p>

        <button class="submit-btn" :disabled="submitting" @click="submitRequest">
          {{ submitting ? 'Submitting...' : 'Submit request' }}
        </button>
      </div>

      <!-- right: requests panel, filterable by status -->
      <div class="requests-panel">
        <div class="panel-header">
          <span class="section-title">Your requests</span>
          <span class="requests-count">{{ filteredRequests.length }}</span>
        </div>

        <div class="status-pill-group">
          <button
            v-for="s in statusFilters" :key="s.value"
            :class="['status-pill', { active: filterStatus === s.value }]"
            @click="filterStatus = s.value"
          >{{ s.label }}</button>
        </div>

        <p v-if="loadError" class="error-msg">{{ loadError }}</p>

        <div v-if="loading" class="empty-state"><p>Loading...</p></div>

        <div v-else-if="filteredRequests.length === 0" class="empty-state">
          <p>{{ filterStatus === 'all' ? 'No document requests yet' : 'No requests with this status' }}</p>
        </div>

        <div v-else class="requests-list">
          <div v-for="r in filteredRequests" :key="r.id" class="request-card">
            <div class="request-top">
              <span class="type-badge">{{ typeLabel(r.type) }}</span>
              <span :class="['status-badge', statusClass(r.status)]">{{ statusLabel(r.status) }}</span>
            </div>
            <p class="request-reason">{{ r.reason || '—' }}</p>
            <div class="request-bottom">
              <span class="request-date">Requested {{ formatDate(r.requested_at) }}</span>
              <button
                v-if="r.status === 'delivered'"
                class="download-link"
                @click="downloadFile(r)"
              >Download</button>
            </div>
          </div>
        </div>
      </div>

    </div>

  </div>
</template>

<style scoped>
.documents-view {
  max-width: var(--content-max-width);
}

.page-header {
  margin-bottom: 20px;
}

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

.two-col {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 18px;
  align-items: start;
}

@media (max-width: 768px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}

/* left: form */
.form-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-xs);
}

.form-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 4px;
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 14px;
  margin-bottom: 6px;
}

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
  min-height: 74px;
  padding: 10px 13px;
  resize: vertical;
  line-height: 1.5;
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-top: 10px;
}

.success-msg {
  font-size: var(--font-size-sm);
  color: var(--color-success-text);
  margin-top: 10px;
  font-weight: 600;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 16px;
  transition: background var(--transition-fast);
}

.submit-btn:hover:not(:disabled) { background: var(--c-900); }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* right: requests panel */
.requests-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-xs);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
}

.requests-count {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-secondary);
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  padding: 2px 10px;
}

.status-pill-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.status-pill {
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.status-pill.active {
  background: var(--c-800);
  border-color: var(--c-800);
  color: #fff;
}

.requests-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.request-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  background: var(--color-surface-soft);
}

.request-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.type-badge {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
  background: #EAF3FB;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
}

.status-badge {
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
}

.status-requested   { background: var(--color-info-bg);    color: var(--color-info-text);    }
.status-in_progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-ready        { background: var(--color-success-bg); color: var(--color-success-text); }
.status-delivered    { background: var(--color-bg);         color: var(--color-text-muted);   }

.request-reason {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.request-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.request-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.download-link {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
}

.download-link:hover { text-decoration: underline; }

.empty-state {
  text-align: center;
  padding: 40px 10px;
}

.empty-state p {
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
}
</style>