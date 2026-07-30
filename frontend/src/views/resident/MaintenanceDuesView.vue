<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/axios'

const auth = useAuthStore()

const dues    = ref([])
const loading = ref(true)
const error   = ref('')

const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']

function formatMonth(isoDate) {
  const [y, m] = isoDate.split('-')
  return `${MONTH_NAMES[parseInt(m, 10) - 1]} ${y}`
}

function formatDate(isoDate) {
  if (!isoDate) return null
  return new Date(isoDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function fetchDues() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/dues')
    dues.value = res.data.dues.map(d => ({
      id:          d.id,
      month:       formatMonth(d.month),
      amount_due:  Number(d.amount_due),
      amount_paid: Number(d.amount_paid),
      due_date:    formatDate(d.month),
      paid_date:   formatDate(d.paid_date),
      status:      d.status,
      receipt_url: d.status === 'paid' ? d.id : null,
    }))
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not load dues'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDues)

const currentDue = computed(() => dues.value[0] || null)

const isPaid = (due) => due.status === 'paid'
function getStatus(due) { return isPaid(due) ? 'paid' : 'pending' }
function statusLabel(due) { return isPaid(due) ? 'Paid' : 'Pending' }

const outstandingDues = computed(() =>
  currentDue.value
    ? dues.value.filter(d => d.id !== currentDue.value.id && !isPaid(d))
    : []
)

const unpaidDues = computed(() => dues.value.filter(d => !isPaid(d)))
const unpaidCount = computed(() => unpaidDues.value.length)

const totalOutstanding = computed(() =>
  unpaidDues.value.reduce((sum, d) => sum + d.amount_due, 0)
)

const totalPaid = computed(() =>
  dues.value.reduce((sum, d) => sum + d.amount_paid, 0)
)

const paymentHistory = computed(() => dues.value)

const showPayModal = ref(false)
const payTarget     = ref(null)
const paySuccess    = ref('')
const paying        = ref(false)

function openPayModal(due = null) {
  payTarget.value = due
  paySuccess.value = ''
  showPayModal.value = true
}

async function confirmPayment() {
  const targets = payTarget.value ? [payTarget.value] : unpaidDues.value
  paying.value = true

  try {
    for (const d of targets) {
      await api.patch(`/dues/${d.id}/pay`)
    }
    paySuccess.value = targets.length > 1
      ? `${targets.length} months marked paid`
      : `Payment recorded for ${targets[0].month}`

    await fetchDues()

    setTimeout(() => { showPayModal.value = false }, 1200)
  } catch (err) {
    paySuccess.value = ''
    error.value = err.response?.data?.error || 'Payment failed, try again'
  } finally {
    paying.value = false
  }
}

async function downloadReceipt(dueId) {
  try {
    const res = await api.get(`/dues/${dueId}/receipt`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `receipt_${dueId}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    error.value = 'Could not download receipt'
  }
}
</script>

<template>
  <div class="dues-view">

    <div class="page-header">
      <div>
        <h2>Maintenance Dues</h2>
        <p class="page-sub">View your dues, payment status and history</p>
      </div>
    </div>

    <p v-if="loading" class="page-sub">Loading dues…</p>
    <p v-else-if="error" class="page-sub" style="color:#b91c1c;">{{ error }}</p>
    <p v-else-if="!dues.length" class="page-sub">No dues found yet. Ask your secretary to generate this month's maintenance.</p>

    <template v-else>
      <!-- ribbon 1: current month only -->
      <div class="current-due-card">
        <div class="due-card-left">
          <span class="due-eyebrow">This month</span>
          <span class="due-month">{{ currentDue.month }}</span>
          <span class="due-amount">₹{{ (isPaid(currentDue) ? 0 : currentDue.amount_due).toLocaleString('en-IN') }}</span>
          <span v-if="!isPaid(currentDue)" class="due-by">Due by {{ currentDue.due_date }}</span>
        </div>
        <div class="due-card-right">
          <span :class="['due-status', getStatus(currentDue)]">{{ statusLabel(currentDue) }}</span>
          <button v-if="!isPaid(currentDue)" class="pay-info-btn" @click="openPayModal(currentDue)">
            Pay now
          </button>
        </div>
      </div>

      <!-- ribbon 2: pay everything outstanding in one go -->
      <div v-if="outstandingDues.length" class="pay-all-ribbon">
        <div class="pay-all-text">
          <span class="pay-all-headline">{{ unpaidCount }} months unpaid</span>
          <span class="pay-all-sub">₹{{ totalOutstanding.toLocaleString('en-IN') }} total outstanding</span>
        </div>
        <button class="pay-all-btn" @click="openPayModal(null)">Pay all outstanding</button>
      </div>

      <!-- ribbon 3: months other than current that are still unpaid -->
      <div v-if="outstandingDues.length" class="other-dues-card">
        <div class="other-dues-title">Other unpaid months</div>
        <div class="other-due-row" v-for="d in outstandingDues" :key="d.id">
          <span class="other-due-month">{{ d.month }}</span>
          <span class="other-due-amount">₹{{ d.amount_due.toLocaleString('en-IN') }}</span>
          <button class="other-due-pay-btn" @click="openPayModal(d)">Pay</button>
        </div>
      </div>

      <div class="summary-row">
        <div class="summary-item">
          <span class="summary-value">₹{{ totalPaid.toLocaleString('en-IN') }}</span>
          <span class="summary-label">Total paid</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ dues.filter(isPaid).length }}</span>
          <span class="summary-label">Months paid</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ unpaidCount }}</span>
          <span class="summary-label">Months pending</span>
        </div>
      </div>

      <div class="section-title">Payment History</div>

      <div class="history-table-wrap">
        <table class="history-table">
          <thead>
            <tr>
              <th>Month</th>
              <th>Amount Due</th>
              <th>Amount Paid</th>
              <th>Paid On</th>
              <th>Status</th>
              <th>Receipt</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paymentHistory" :key="item.id">
              <td class="month-cell">{{ item.month }}</td>
              <td>₹{{ (isPaid(item) ? 0 : item.amount_due).toLocaleString('en-IN') }}</td>
              <td>₹{{ item.amount_paid.toLocaleString('en-IN') }}</td>
              <td class="date-cell">{{ item.paid_date || '—' }}</td>
              <td>
                <span :class="['history-badge', getStatus(item)]">
                  {{ statusLabel(item) }}
                </span>
              </td>
              <td>
                <a v-if="item.receipt_url" href="#" class="receipt-link" @click.prevent="downloadReceipt(item.receipt_url)">
                  Download
                </a>
                <span v-else class="no-receipt">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="showPayModal" class="modal-overlay" @click.self="showPayModal = false">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ payTarget ? `Pay ${payTarget.month}` : 'Pay all outstanding' }}</h3>
            <button class="close-btn" @click="showPayModal = false">✕</button>
          </div>
          <div class="modal-body">
            <p class="modal-amount">
              ₹{{ (payTarget ? payTarget.amount_due : totalOutstanding).toLocaleString('en-IN') }}
            </p>
            <p v-if="!payTarget" class="modal-sub">Covers {{ unpaidCount }} unpaid months</p>

            <div v-if="!payTarget" class="modal-breakdown">
              <div class="modal-breakdown-row" v-for="d in unpaidDues" :key="d.id">
                <span class="modal-breakdown-month">{{ d.month }}</span>
                <span class="modal-breakdown-amount">₹{{ d.amount_due.toLocaleString('en-IN') }}</span>
              </div>
            </div>

            <p v-if="paySuccess" class="success-msg">✓ {{ paySuccess }}</p>

            <button class="submit-btn" :disabled="paying" @click="confirmPayment">
              {{ paying ? 'Processing…' : 'Confirm payment' }}
            </button>
          </div>
        </div>
      </div>
    </template>

  </div>
</template>

<style scoped>
.dues-view { max-width: var(--content-max-width); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.current-due-card {
  background: linear-gradient(135deg, var(--c-900) 0%, var(--c-800) 100%);
  border-radius: var(--radius-xl); padding: 26px 32px; display: flex; align-items: center;
  justify-content: space-between; margin-bottom: 14px; box-shadow: var(--shadow-md);
}
.due-card-left { display: flex; flex-direction: column; gap: 3px; }
.due-eyebrow { font-size: var(--font-size-xs); color: rgba(255,255,255,0.55); font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; }
.due-month { font-size: var(--font-size-sm); color: rgba(255,255,255,0.8); font-weight: 600; }
.due-amount { font-size: var(--font-size-hero); font-weight: 800; color: #fff; letter-spacing: -1px; line-height: 1.1; margin-top: 2px; }
.due-by { font-size: var(--font-size-xs); color: rgba(255,255,255,0.6); font-weight: 600; margin-top: 4px; }
.due-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 12px; }
.due-status { padding: 6px 16px; border-radius: var(--radius-pill); font-size: var(--font-size-sm); font-weight: 700; }
.due-status.paid    { background: var(--color-success-bg); color: var(--color-success-text); }
.due-status.pending { background: var(--color-warning-bg); color: var(--color-warning-text); }
.pay-info-btn { padding: 9px 18px; border-radius: var(--radius-md); background: #fff; color: var(--c-900); font-size: var(--font-size-sm); font-weight: 700; }
.pay-info-btn:hover { background: rgba(255,255,255,0.9); }

.pay-all-ribbon {
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  background: var(--color-warning-bg); border: 1px solid var(--color-warning);
  border-radius: var(--radius-lg); padding: 16px 22px; margin-bottom: 14px;
}
.pay-all-text { display: flex; flex-direction: column; gap: 2px; }
.pay-all-headline { font-size: var(--font-size-md); font-weight: 700; color: var(--color-warning-text); }
.pay-all-sub { font-size: var(--font-size-xs); color: var(--color-warning-text); opacity: 0.85; }
.pay-all-btn { flex-shrink: 0; height: 40px; padding: 0 20px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-sm); font-weight: 700; white-space: nowrap; }
.pay-all-btn:hover { background: var(--c-900); }

.other-dues-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 6px 6px 10px; margin-bottom: 24px; box-shadow: var(--shadow-xs);
}
.other-dues-title {
  font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 16px 8px;
}
.other-due-row {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  border-top: 1px solid var(--color-border);
}
.other-due-month { flex: 1; font-weight: 600; color: var(--color-text-primary); font-size: var(--font-size-sm); }
.other-due-amount { font-weight: 700; color: var(--color-text-primary); font-size: var(--font-size-sm); }
.other-due-pay-btn {
  height: 30px; padding: 0 14px; border-radius: var(--radius-sm); border: 1.5px solid var(--c-600);
  background: transparent; color: var(--c-800); font-size: var(--font-size-xs); font-weight: 700;
}
.other-due-pay-btn:hover { background: var(--color-bg); }

.summary-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 28px; }
.summary-item { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 18px 20px; display: flex; flex-direction: column; gap: 4px; box-shadow: var(--shadow-xs); }
.summary-value { font-size: var(--font-size-3xl); font-weight: 800; color: var(--c-800); letter-spacing: -0.5px; }
.summary-label { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: 600; }

.section-title { font-size: var(--font-size-xl); font-weight: 700; margin-bottom: 14px; }

.history-table-wrap { background: var(--color-surface); border-radius: var(--radius-lg); border: 1px solid var(--color-border); overflow-x: auto; box-shadow: var(--shadow-sm); margin-bottom: 24px; }
.history-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.history-table thead tr { border-bottom: 1px solid var(--color-border); }
.history-table th { padding: 12px 16px; text-align: left; font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }
.history-table td { padding: 14px 16px; border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.history-table tbody tr:last-child td { border-bottom: none; }
.history-table tbody tr:hover { background: var(--color-surface-muted); }
.month-cell { font-weight: 600; color: var(--color-text-primary); }
.date-cell { color: var(--color-text-secondary); white-space: nowrap; }

.history-badge { padding: 3px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; }
.history-badge.paid    { background: var(--color-success-bg); color: var(--color-success-text); }
.history-badge.pending { background: var(--color-warning-bg); color: var(--color-warning-text); }

.receipt-link { color: var(--c-800); font-weight: 600; font-size: var(--font-size-sm); text-decoration: underline; }
.no-receipt { color: var(--color-text-muted); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); }
.modal { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 380px; box-shadow: var(--shadow-lg); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 22px 14px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { font-size: var(--font-size-lg); font-weight: 700; }
.close-btn { width: 30px; height: 30px; border-radius: var(--radius-sm); background: var(--color-bg); color: var(--color-text-secondary); display: flex; align-items: center; justify-content: center; }
.modal-body { padding: 20px 22px; text-align: center; }
.modal-amount { font-size: var(--font-size-3xl); font-weight: 800; color: var(--c-800); margin-bottom: 4px; }
.modal-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 12px; }
.modal-breakdown { text-align: left; border: 1px solid var(--color-border); border-radius: var(--radius-md); overflow: hidden; margin-bottom: 4px; }
.modal-breakdown-row { display: flex; align-items: center; justify-content: space-between; padding: 9px 14px; font-size: var(--font-size-sm); }
.modal-breakdown-row + .modal-breakdown-row { border-top: 1px solid var(--color-border); }
.modal-breakdown-month { color: var(--color-text-secondary); font-weight: 600; }
.modal-breakdown-amount { color: var(--color-text-primary); font-weight: 700; }
.success-msg { font-size: var(--font-size-xs); color: var(--color-success-text); font-weight: 600; margin: 10px 0; }
.submit-btn { width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; margin-top: 16px; }
.submit-btn:disabled { opacity: 0.6; }
</style>