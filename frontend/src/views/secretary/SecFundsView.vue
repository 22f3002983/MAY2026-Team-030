<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api/axios'

const funds = ref([])
const config = ref([])
const transactions = ref([])
const loading = ref(true)
const error = ref('')
const activeTab = ref('overview')

const showTxnModal = ref(false)
const txnForm = ref({ fund_name: '', type: 'debit', amount: null, description: '' })
const txnError = ref('')
const saving = ref(false)

// ── bulk config editing ─────────────────────────────────────
const editingConfig = ref(false)
const configDraft = ref([]) // [{ id, fund_name, percentage, is_active }]
const configError = ref('')
const savingConfig = ref(false)

const draftTotal = computed(() =>
  configDraft.value.filter(c => c.is_active).reduce((sum, c) => sum + Number(c.percentage || 0), 0)
)

function startEditConfig() {
  configDraft.value = config.value.map(c => ({ id: c.id, fund_name: c.fund_name, percentage: c.percentage, is_active: c.is_active }))
  configError.value = ''
  editingConfig.value = true
}

function cancelEditConfig() {
  editingConfig.value = false
}

async function saveAllConfig() {
  configError.value = ''
  if (Math.round(draftTotal.value * 100) / 100 !== 100) {
    configError.value = `Active percentages must sum to 100 (currently ${draftTotal.value})`
    return
  }
  savingConfig.value = true
  try {
    await api.patch('/funds/config', { configs: configDraft.value })
    editingConfig.value = false
    await loadAll()
  } catch (err) {
    configError.value = err.response?.data?.error || 'Failed to update configuration'
  } finally {
    savingConfig.value = false
  }
}

const totalBalance = computed(() => funds.value.reduce((sum, f) => sum + f.balance, 0))

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const [f, c, t] = await Promise.all([
      api.get('/funds'),
      api.get('/funds/config'),
      api.get('/funds/transactions'),
    ])
    funds.value = f.data.funds
    config.value = c.data.config
    transactions.value = t.data.transactions
  } catch (err) {
    error.value = 'Failed to load fund data'
  } finally {
    loading.value = false
  }
}

function fundLabel(name) {
  const map = { operating: 'Operating Fund', sinking: 'Sinking Fund', contingency: 'Contingency Fund' }
  return map[name] || name
}

// Operating is the default source for debits. Other funds unlock only if
// Operating's balance can't cover the amount currently being entered.
const debitFundOptions = computed(() => {
  const operating = funds.value.find(f => f.fund_name === 'operating')
  const amount = Number(txnForm.value.amount) || 0
  const operatingInsufficient = !operating || operating.balance < amount
  return operatingInsufficient ? funds.value : funds.value.filter(f => f.fund_name === 'operating')
})

// Keep the selected fund valid if the available options change
// (e.g. user picked a non-Operating fund, then lowered the amount
// so Operating becomes sufficient again).
watch(debitFundOptions, (options) => {
  if (txnForm.value.type === 'debit' && !options.some(f => f.fund_name === txnForm.value.fund_name)) {
    txnForm.value.fund_name = options[0]?.fund_name || ''
  }
})

function openTxnModal() {
  txnForm.value = { fund_name: 'operating', type: 'debit', amount: null, description: '' }
  txnError.value = ''
  showTxnModal.value = true
}

async function submitTxn() {
  txnError.value = ''
  const needsFund = txnForm.value.type === 'debit'
  if ((needsFund && !txnForm.value.fund_name) || !txnForm.value.amount || !txnForm.value.description.trim()) {
    txnError.value = 'Amount and description are required' + (needsFund ? ', and a fund for the debit' : '')
    return
  }
  saving.value = true
  try {
    const payload = { type: txnForm.value.type, amount: txnForm.value.amount, description: txnForm.value.description }
    if (needsFund) payload.fund_name = txnForm.value.fund_name
    await api.post('/funds/transactions', payload)
    showTxnModal.value = false
    await loadAll()
  } catch (err) {
    txnError.value = err.response?.data?.error || 'Failed to record transaction'
  } finally {
    saving.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="funds">
    <div class="page-header">
      <div>
        <h2>Society Funds</h2>
        <p class="page-sub">Track fund balances and record income/expense transactions</p>
      </div>
      <button class="btn-add" @click="openTxnModal">+ Record Transaction</button>
    </div>

    <div v-if="loading" class="empty-state"><p>Loading fund data...</p></div>
    <div v-else-if="error" class="empty-state"><p>{{ error }}</p></div>

    <template v-else>
      <div class="tabs">
        <button :class="['tab', { active: activeTab === 'overview' }]" @click="activeTab = 'overview'">Overview</button>
        <button :class="['tab', { active: activeTab === 'config' }]" @click="activeTab = 'config'">Split Configuration</button>
        <button :class="['tab', { active: activeTab === 'transactions' }]" @click="activeTab = 'transactions'">Transactions</button>
      </div>

      <template v-if="activeTab === 'overview'">
        <div class="fund-grid">
          <div class="fund-card total">
            <span class="fund-label">Total Balance</span>
            <span class="fund-balance">₹{{ totalBalance.toLocaleString('en-IN') }}</span>
          </div>
          <div v-for="f in funds" :key="f.id" class="fund-card">
            <span class="fund-label">{{ fundLabel(f.fund_name) }}</span>
            <span class="fund-balance">₹{{ f.balance.toLocaleString('en-IN') }}</span>
          </div>
        </div>
      </template>

      <template v-if="activeTab === 'config'">
        <p class="section-sub">Incoming dues and amenity-booking payments are split across active funds by these percentages. They must always sum to 100 — edit all funds together, then save.</p>

        <div v-if="!editingConfig" class="config-list">
          <div v-for="cfg in config" :key="cfg.id" class="config-row">
            <span class="config-name">{{ fundLabel(cfg.fund_name) }}</span>
            <span class="config-pct">{{ cfg.percentage }}%</span>
            <span :class="['config-status', { inactive: !cfg.is_active }]">{{ cfg.is_active ? 'Active' : 'Inactive' }}</span>
          </div>
          <button class="edit-btn" style="align-self: flex-start; margin-top: 8px;" @click="startEditConfig">Edit all</button>
        </div>

        <div v-else class="config-list">
          <div v-for="cfg in configDraft" :key="cfg.id" class="config-row">
            <span class="config-name">{{ fundLabel(cfg.fund_name) }}</span>
            <input v-model.number="cfg.percentage" type="number" min="0" max="100" class="config-input" />
            <label class="active-toggle"><input type="checkbox" v-model="cfg.is_active" /> Active</label>
          </div>
          <div class="config-total" :class="{ bad: Math.round(draftTotal * 100) / 100 !== 100 }">
            Total: {{ draftTotal }}% {{ Math.round(draftTotal * 100) / 100 === 100 ? '✓' : '(must equal 100)' }}
          </div>
          <div style="display: flex; gap: 10px; margin-top: 8px;">
            <button class="save-btn" :disabled="savingConfig" @click="saveAllConfig">{{ savingConfig ? 'Saving...' : 'Save all' }}</button>
            <button class="cancel-btn" @click="cancelEditConfig">Cancel</button>
          </div>
        </div>

        <p v-if="configError" class="error-msg">{{ configError }}</p>
      </template>

      <template v-if="activeTab === 'transactions'">
        <div v-if="transactions.length === 0" class="empty-state"><p>No transactions yet</p></div>
        <div v-else class="table-wrap">
          <table class="txn-table">
            <thead><tr><th>Date</th><th>Fund</th><th>Type</th><th>Amount</th><th>Source</th><th>Description</th></tr></thead>
            <tbody>
              <tr v-for="t in transactions" :key="t.id">
                <td>{{ formatDate(t.created_at) }}</td>
                <td class="fund-cell">{{ fundLabel(t.fund_name) }}</td>
                <td><span :class="['type-chip', t.type]">{{ t.type === 'credit' ? '+ Credit' : '− Debit' }}</span></td>
                <td>₹{{ t.amount.toLocaleString('en-IN') }}</td>
                <td class="source-cell">{{ t.source }}</td>
                <td class="desc-cell">{{ t.description || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>

    <div v-if="showTxnModal" class="modal-overlay" @click.self="showTxnModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Record Transaction</h3>
          <button class="close-btn" @click="showTxnModal = false">✕</button>
        </div>
        <div class="modal-body">
            <label>Type</label>
            <select v-model="txnForm.type" class="n-input">
              <option value="debit">Debit (expense)</option>
              <option value="credit">Credit (extra income)</option>
            </select>

            <template v-if="txnForm.type === 'debit'">
              <label>Fund</label>
              <select v-model="txnForm.fund_name" class="n-input">
                <option v-for="f in debitFundOptions" :key="f.fund_name" :value="f.fund_name">{{ fundLabel(f.fund_name) }}</option>
              </select>
              <p v-if="debitFundOptions.length === 1" class="section-sub" style="margin: 4px 0 0;">
                Debits come from Operating by default. Other funds unlock if Operating's balance can't cover this amount.
              </p>
            </template>

            <template v-else>
              <p class="section-sub" style="margin: 4px 0 0;">
                This amount will be automatically split across active funds per the configured percentages.
              </p>
            </template>

            <label>Amount (₹)</label>
            <input v-model.number="txnForm.amount" type="number" min="0" step="0.01" class="n-input" placeholder="e.g. 5000" />
            <label>Description</label>
            <textarea v-model="txnForm.description" class="n-input n-textarea" placeholder="e.g. Garden maintenance payment to vendor" />
            <p v-if="txnError" class="error-msg">{{ txnError }}</p>
          </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showTxnModal = false">Cancel</button>
          <button class="btn-primary" :disabled="saving" @click="submitTxn">{{ saving ? 'Saving...' : 'Record' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.funds { max-width: var(--content-max-width); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.btn-add { height: 42px; padding: 0 20px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; white-space: nowrap; transition: background var(--transition-fast); }
.btn-add:hover { background: var(--c-900); }

.tabs { display: flex; gap: 4px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 4px; margin-bottom: 22px; width: fit-content; }
.tab { height: 38px; padding: 0 18px; border-radius: var(--radius-sm); font-size: var(--font-size-md); font-weight: 600; color: var(--color-text-secondary); transition: all var(--transition-fast); }
.tab.active { background: var(--c-800); color: #fff; }

.fund-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.fund-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 20px; display: flex; flex-direction: column; gap: 8px; box-shadow: var(--shadow-xs); }
.fund-card.total { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); border: none; }
.fund-card.total .fund-label, .fund-card.total .fund-balance { color: #fff; }
.fund-label { font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-muted); }
.fund-balance { font-size: var(--font-size-2xl, 22px); font-weight: 800; color: var(--color-text-primary); }

.section-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; max-width: 600px; }

.config-list { display: flex; flex-direction: column; gap: 10px; }
.config-row { display: flex; align-items: center; gap: 14px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 14px 18px; box-shadow: var(--shadow-xs); }
.config-name { font-weight: 700; color: var(--color-text-primary); flex: 1; }
.config-pct { font-size: var(--font-size-lg); font-weight: 800; color: var(--c-800); }
.config-status { font-size: var(--font-size-xs); font-weight: 700; padding: 3px 10px; border-radius: var(--radius-pill); background: var(--color-success-bg); color: var(--color-success-text); }
.config-status.inactive { background: var(--badge-closed-bg); color: var(--badge-closed-text); }
.config-input { width: 80px; height: 34px; padding: 0 8px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-sm); background: var(--color-surface-soft); color: var(--color-text-primary); }
.active-toggle { display: flex; align-items: center; gap: 6px; font-size: var(--font-size-sm); font-weight: 600; }
.active-toggle input { width: auto; }
.edit-btn, .save-btn, .cancel-btn { height: 34px; padding: 0 14px; border-radius: var(--radius-sm); font-size: var(--font-size-xs); font-weight: 700; }
.edit-btn { background: var(--color-surface-soft); color: var(--c-800); border: 1px solid var(--color-border); }
.save-btn { background: var(--color-success-bg); color: var(--color-success-text); border: 1px solid var(--color-success); }
.cancel-btn { background: transparent; color: var(--color-text-secondary); border: 1px solid var(--color-border); }

.table-wrap { background: var(--color-surface); border-radius: var(--radius-lg); border: 1px solid var(--color-border); overflow-x: auto; box-shadow: var(--shadow-xs); }
.txn-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.txn-table th { padding: 12px 20px; text-align: left; font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.4px; background: var(--color-surface-soft); border-bottom: 1px solid var(--color-border); }
.txn-table td { padding: 14px 20px; border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.txn-table tbody tr:last-child td { border-bottom: none; }
.fund-cell { font-weight: 700; color: var(--color-text-primary); }
.source-cell { color: var(--color-text-muted); font-size: var(--font-size-xs); text-transform: capitalize; }
.desc-cell { color: var(--color-text-secondary); max-width: 260px; }

.type-chip { font-size: var(--font-size-xs); font-weight: 700; padding: 3px 10px; border-radius: var(--radius-pill); }
.type-chip.credit { background: var(--color-success-bg); color: var(--color-success-text); }
.type-chip.debit { background: var(--color-danger-bg); color: var(--color-danger-text); }

.empty-state { text-align: center; padding: 60px 20px; }
.empty-state p { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text-muted); }

.error-msg { font-size: var(--font-size-sm); color: var(--color-danger); margin-top: 6px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); padding: 20px; }
.modal { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 440px; max-height: 90vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 22px 24px 16px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { font-size: var(--font-size-xl); font-weight: 700; }
.close-btn { width: 32px; height: 32px; border-radius: var(--radius-sm); background: var(--color-bg); color: var(--color-text-secondary); display: flex; align-items: center; justify-content: center; transition: background var(--transition-fast); }
.close-btn:hover { background: var(--color-border); }

.modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
label { display: block; font-size: var(--font-size-sm); font-weight: 600; color: var(--c-800); margin-top: 10px; margin-bottom: 4px; }
.n-input { width: 100%; height: 42px; padding: 0 13px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); font-size: var(--font-size-md); background: var(--color-surface-soft); color: var(--color-text-primary); outline: none; font-family: var(--font-family); transition: border-color var(--transition-fast); }
.n-input:focus { border-color: var(--c-600); }
.n-textarea { height: 70px; padding: 10px 13px; resize: vertical; }

.modal-footer { display: flex; gap: 10px; padding: 16px 24px 22px; border-top: 1px solid var(--color-border); }
.btn-primary { flex: 1; height: 42px; border-radius: var(--radius-md); background: var(--c-800); color: #fff; font-size: var(--font-size-md); font-weight: 700; transition: background var(--transition-fast); }
.btn-primary:hover { background: var(--c-900); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { flex: 1; height: 42px; border-radius: var(--radius-md); border: 1.5px solid var(--color-border-soft); background: var(--color-surface); color: var(--color-text-secondary); font-size: var(--font-size-md); font-weight: 600; transition: all var(--transition-fast); }
.btn-secondary:hover { border-color: var(--c-600); color: var(--c-800); }

.config-total { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-success-text); padding: 8px 4px; }
.config-total.bad { color: var(--color-danger-text); }
</style>