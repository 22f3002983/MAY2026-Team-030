<script setup>
import { ref } from 'vue'

/* ---------------------------------------------------------------
   Documents — Resident view.
   Frontend-only mock; replace with API calls when the backend is ready.
--------------------------------------------------------------- */

const successMsg    = ref('')
const submitting    = ref(false)
const formError     = ref('')
const downloadError = ref('')

const form = ref({
  type:   'noc',
  reason: '',
})

const typeOptions = [
  { value: 'noc',             label: 'NOC' },
  { value: 'payment_receipt', label: 'Payment Receipt' },
  { value: 'other',           label: 'Other' },
]

// Mock data
const requests = ref([
  { id: 1, type: 'NOC',             reason: 'Bank loan application', status: 'ready',     requested_at: '10 Jul 2026' },
  { id: 2, type: 'Payment Receipt', reason: 'Tax filing',            status: 'requested', requested_at: '15 Jul 2026' },
])

function submitRequest() {
  formError.value  = ''
  successMsg.value = ''

  if (!form.value.reason.trim()) {
    formError.value = 'Please describe why you need this document'
    return
  }

  submitting.value = true
  // mock "submit" — simulate a short delay and add the row locally
  setTimeout(() => {
    requests.value.unshift({
      id: requests.value.length + 1,
      type: typeLabel(form.value.type),
      reason: form.value.reason.trim(),
      status: 'requested',
      requested_at: 'Today',
    })
    form.value = { type: 'noc', reason: '' }
    submitting.value = false
    successMsg.value = 'Document request submitted successfully'
    setTimeout(() => successMsg.value = '', 5000)
  }, 500)
}

function typeLabel(type) {
  return typeOptions.find(t => t.value === type)?.label || type
}

function statusLabel(status) {
  const map = {
    requested:   'Requested',
    in_progress: 'In Progress',
    ready:       'Ready',
    delivered:   'Delivered',
  }
  return map[status] || status
}

function statusClass(status) {
  return 'status-' + status
}

function downloadFile(r) {
  downloadError.value = ''
  // mock download — no real file behind this in the frontend-only version
  downloadError.value = `Downloading ${r.type} isn't available in this preview`
  setTimeout(() => downloadError.value = '', 5000)
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

    <!-- request form -->
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

    <!-- request list -->
    <div class="section-title">Your requests</div>

    <p v-if="downloadError" class="error-msg">{{ downloadError }}</p>

    <div v-if="requests.length === 0" class="empty-state">
      <p>No document requests yet</p>
    </div>

    <div v-else class="table-wrap">
      <table class="requests-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Reason</th>
            <th>Requested</th>
            <th>Status</th>
            <th>Document</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in requests" :key="r.id">
            <td class="type-cell">{{ r.type }}</td>
            <td class="reason-cell">{{ r.reason || '—' }}</td>
            <td class="date-cell">{{ r.requested_at }}</td>
            <td>
              <span :class="['status-badge', statusClass(r.status)]">{{ statusLabel(r.status) }}</span>
            </td>
            <td>
              <button
                v-if="r.status === 'ready' || r.status === 'delivered'"
                class="download-link"
                @click="downloadFile(r)"
              >Download</button>
              <button v-else class="download-btn" disabled>Download</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
.documents-view { max-width: var(--content-max-width); }

.page-header { margin-bottom: 24px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.form-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-xs);
  margin-bottom: 28px;
  max-width: 480px;
}

.form-title { font-size: var(--font-size-lg); font-weight: 800; color: var(--c-900); margin-bottom: 4px; }

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 14px;
  margin-bottom: 5px;
}

.n-input {
  width: 100%;
  padding: 0 13px;
  height: 42px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  font-family: var(--font-family);
  transition: border-color var(--transition-fast);
}

.n-textarea {
  height: auto;
  padding: 10px 13px;
  resize: vertical;
  min-height: 80px;
}

.n-input:focus { border-color: var(--c-600); }

.error-msg { font-size: var(--font-size-sm); color: var(--color-danger); margin-top: 10px; }
.success-msg { font-size: var(--font-size-sm); color: var(--color-success-text); margin-top: 10px; font-weight: 600; }

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
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.section-title { font-size: var(--font-size-xl); font-weight: 700; margin-bottom: 14px; }

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
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

.type-cell { font-weight: 700; color: var(--color-text-primary); white-space: nowrap; }
.reason-cell { color: var(--color-text-secondary); max-width: 260px; }
.date-cell { color: var(--color-text-secondary); white-space: nowrap; }

.status-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
}

.status-badge.status-requested   { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-badge.status-in_progress { background: var(--color-info-bg);    color: var(--color-info-text);    }
.status-badge.status-ready       { background: var(--color-success-bg); color: var(--color-success-text); }
.status-badge.status-delivered   { background: var(--badge-closed-bg);  color: var(--badge-closed-text);  }

.download-link {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: #fff;
  background: var(--c-800);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.download-link:hover { background: var(--c-900); }

.download-btn {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>