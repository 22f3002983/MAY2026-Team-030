<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/axios'

const loading = ref(true)
const submitting = ref(false)
const showAddModal = ref(false)
const formError = ref('')

const bills = ref([])

const newBill = ref({
  month: '',
  total_units: null,
  total_amount: null,
})

async function fetchBills() {
  loading.value = true
  try {
    const res = await api.get('/electricity-bills')
    bills.value = res.data.bills
  } catch (err) {
    console.error('Failed to load electricity bills', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchBills)

function monthLabel(monthStr) {
  if (!monthStr) return '—'
  const d = new Date(monthStr)
  return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
}

async function addBill() {
  formError.value = ''

  if (!newBill.value.month || newBill.value.total_units === null || newBill.value.total_amount === null) {
    formError.value = 'Month, total units and total amount are required'
    return
  }
  if (newBill.value.total_units <= 0 || newBill.value.total_amount <= 0) {
    formError.value = 'Total units and total amount must be greater than 0'
    return
  }

  const payload = {
    month: newBill.value.month,
    total_units: newBill.value.total_units,
    total_amount: newBill.value.total_amount,
  }

  // close the modal right away and show an optimistic card with the
  // analysis section spinning, since the real POST covers both saving the
  // bill AND generating the AI analysis in one round trip
  const tempId = `pending-${Date.now()}`
  bills.value.unshift({
    id: tempId,
    month: `${payload.month}-01`,
    total_units: payload.total_units,
    total_amount: payload.total_amount,
    ai_analysis: null,
    analyzing: true,
  })
  showAddModal.value = false
  newBill.value = { month: '', total_units: null, total_amount: null }

  submitting.value = true
  try {
    const res = await api.post('/electricity-bills', payload)
    const idx = bills.value.findIndex(b => b.id === tempId)
    if (idx !== -1) {
      bills.value[idx] = { ...res.data.bill, analyzing: false }
    }
  } catch (err) {
    bills.value = bills.value.filter(b => b.id !== tempId)
    alert(err.response?.data?.error || 'Failed to upload electricity bill')
  } finally {
    submitting.value = false
  }
}const retryingAnalysis = ref(new Set())

async function retryAnalysis(bill) {
  if (retryingAnalysis.value.has(bill.id)) return
  retryingAnalysis.value = new Set(retryingAnalysis.value).add(bill.id)
  try {
    const res = await api.post(`/electricity-bills/${bill.id}/retry-analysis`)
    const idx = bills.value.findIndex(b => b.id === bill.id)
    if (idx !== -1) bills.value[idx] = { ...res.data.bill, analyzing: false }
  } catch (err) {
    console.error('Failed to retry bill analysis', err)
  } finally {
    const next = new Set(retryingAnalysis.value)
    next.delete(bill.id)
    retryingAnalysis.value = next
  }
}
</script>

<template>
  <div class="elec-bills">

    <div class="page-header">
      <div>
        <h2>Electricity Bills</h2>
        <p class="page-sub">{{ bills.length }} bill{{ bills.length === 1 ? '' : 's' }} on record</p>
      </div>
      <button class="btn-add" @click="showAddModal = true">+ Add Bill</button>
    </div>

    <div v-if="loading" class="empty-state">Loading...</div>
    <div v-else-if="bills.length === 0" class="empty-state">No electricity bills uploaded yet</div>

    <div v-else class="bill-grid">
      <div v-for="b in bills" :key="b.id" class="bill-card">
        <div class="bill-card-header">
          <span class="bill-month">{{ monthLabel(b.month) }}</span>
        </div>
        <div class="bill-stats">
          <div class="bill-stat">
            <span class="stat-label">Units</span>
            <span class="stat-value">{{ b.total_units }}</span>
          </div>
          <div class="bill-stat">
            <span class="stat-label">Amount</span>
            <span class="stat-value">₹{{ Number(b.total_amount).toLocaleString('en-IN') }}</span>
          </div>
        </div>

        <div class="analysis-section">
          <div class="analysis-label">AI Analysis</div>
          <div v-if="b.analyzing" class="analysis-loading">
            <span class="spinner"></span> Analysing usage...
          </div>
          <p v-else-if="b.ai_analysis" class="analysis-text">{{ b.ai_analysis }}</p>
          <div v-else class="analysis-pending-row">
            <p class="analysis-pending">Analysis pending</p>
            <button
              class="ai-retry-btn"
              title="Retry AI analysis now"
              :disabled="retryingAnalysis.has(b.id)"
              @click="retryAnalysis(b)"
            >{{ retryingAnalysis.has(b.id) ? '⏳' : '↻ Retry now' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- add bill modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Add Electricity Bill</h3>
          <button class="close-btn" @click="showAddModal = false">✕</button>
        </div>

        <div class="modal-body">
          <label>Month *</label>
          <input v-model="newBill.month" type="month" class="n-input" />

          <label>Total units (kWh) *</label>
          <input v-model.number="newBill.total_units" type="number" min="0" step="0.01" placeholder="e.g. 4500" class="n-input" />

          <label>Total amount (₹) *</label>
          <input v-model.number="newBill.total_amount" type="number" min="0" step="0.01" placeholder="e.g. 38000" class="n-input" />

          <p v-if="formError" class="error-msg">{{ formError }}</p>

          <div class="invite-note">
            After saving, the AI will compare this bill against the last 3 months on record and generate a short analysis automatically.
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn-primary" :disabled="submitting" @click="addBill">
            Add Bill
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.elec-bills {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
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

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: 60px;
  font-size: var(--font-size-md);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.bill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.bill-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bill-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bill-month {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-primary);
}

.bill-stats {
  display: flex;
  gap: 24px;
}

.bill-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: 800;
  color: var(--c-800);
}

.analysis-section {
  border-top: 1px solid var(--color-border);
  padding-top: 12px;
}

.analysis-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 6px;
}

.analysis-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  white-space: pre-line;
}

.analysis-pending {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.analysis-pending-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-retry-btn {
  border: none;
  background: none;
  color: var(--c-600, #0EA5B7);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.ai-retry-btn:hover:not(:disabled) { background: rgba(14, 165, 183, 0.1); }
.ai-retry-btn:disabled { cursor: not-allowed; opacity: 0.6; }

.analysis-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-border-soft);
  border-top-color: var(--c-600);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
}

.modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 440px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  font-size: var(--font-size-xl);
  font-weight: 700;
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
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.close-btn:hover { background: var(--color-border); }

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
  margin-bottom: 4px;
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

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-top: 6px;
}

.invite-note {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  line-height: 1.5;
}

.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 24px 22px;
  border-top: 1px solid var(--color-border);
}

.btn-primary {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.btn-primary:hover { background: var(--c-900); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-secondary {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 600;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  border-color: var(--c-600);
  color: var(--c-800);
}
</style>