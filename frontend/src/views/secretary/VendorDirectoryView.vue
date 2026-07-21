<script setup>
import { ref, computed } from 'vue'

/* ---------------------------------------------------------------
   Vendor Management — Secretary-owned.
--------------------------------------------------------------- */

const categories = ['all', 'Plumbing', 'Electrical', 'Carpentry', 'Cleaning', 'Security', 'Gardening', 'Other']
const statusOptions = ['active', 'inactive', 'blacklisted']

const searchQuery = ref('')
const filterCategory = ref('all')
const filterPayType = ref('all')     // 'all' | 'salaried' | 'not_salaried'
const filterStatus = ref('all')      // 'all' | 'active' | 'inactive' | 'blacklisted'
const showAddForm = ref(false)

// mock data - replace with API call in Sprint 1
const vendors = ref([
  {
    id: 1,
    name: 'Kishore Plumbing',
    phone: '+91 98480 11223',
    category: 'Plumbing',
    working_hours: '8 AM – 8 PM',
    status: 'active',
    is_salaried: false,
    salary_amount: null,
    created_at: '2026-02-11',
  },
  {
    id: 2,
    name: 'Raju Electricals',
    phone: '+91 97400 33441',
    category: 'Electrical',
    working_hours: '9 AM – 7 PM',
    status: 'active',
    is_salaried: false,
    salary_amount: null,
    created_at: '2026-02-11',
  },
  {
    id: 3,
    name: 'Suresh Carpentry',
    phone: '+91 96300 22110',
    category: 'Carpentry',
    working_hours: '10 AM – 6 PM',
    status: 'active',
    is_salaried: false,
    salary_amount: null,
    created_at: '2026-03-02',
  },
  {
    id: 4,
    name: 'Clean Society',
    phone: '+91 95200 44332',
    category: 'Cleaning',
    working_hours: '7 AM – 5 PM',
    status: 'active',
    is_salaried: true,
    salary_amount: 18000,
    created_at: '2026-01-15',
  },
  {
    id: 5,
    name: 'Manoj Kumar (Security)',
    phone: '+91 94400 55667',
    category: 'Security',
    working_hours: '24x7 shift rotation',
    status: 'active',
    is_salaried: true,
    salary_amount: 22000,
    created_at: '2026-01-15',
  },
  {
    id: 6,
    name: 'Ramesh (Gardener)',
    phone: '+91 93200 88123',
    category: 'Gardening',
    working_hours: '7 AM – 11 AM',
    status: 'inactive',
    is_salaried: true,
    salary_amount: 12000,
    created_at: '2026-01-15',
  },
  {
    id: 7,
    name: 'QuickFix Electricals',
    phone: '+91 90000 11122',
    category: 'Electrical',
    working_hours: '10 AM – 8 PM',
    status: 'blacklisted',
    is_salaried: false,
    salary_amount: null,
    created_at: '2026-04-01',
  },
])

// salary payments recorded through the Pay Salaries flow
const paymentHistory = ref([
  { id: 'PAY-1001', vendorId: 4, vendorName: 'Clean Society',        amount: 18000, date: '01 Jun 2026' },
  { id: 'PAY-1002', vendorId: 5, vendorName: 'Manoj Kumar (Security)', amount: 22000, date: '01 Jun 2026' },
  { id: 'PAY-1003', vendorId: 6, vendorName: 'Ramesh (Gardener)',    amount: 12000, date: '01 Jun 2026' },
  { id: 'PAY-1004', vendorId: 4, vendorName: 'Clean Society',        amount: 18000, date: '01 Jul 2026' },
  { id: 'PAY-1005', vendorId: 5, vendorName: 'Manoj Kumar (Security)', amount: 22000, date: '01 Jul 2026' },
  { id: 'PAY-1006', vendorId: 6, vendorName: 'Ramesh (Gardener)',    amount: 12000, date: '01 Jul 2026' },
])

/* ---------------- Search / filter ---------------- */

const filteredVendors = computed(() => {
  return vendors.value.filter(v => {
    const matchesSearch = v.name.toLowerCase().includes(searchQuery.value.toLowerCase())
      || v.phone.includes(searchQuery.value)
    const matchesCategory = filterCategory.value === 'all' || v.category === filterCategory.value
    const matchesPayType = filterPayType.value === 'all'
      || (filterPayType.value === 'salaried' && v.is_salaried)
      || (filterPayType.value === 'not_salaried' && !v.is_salaried)
    const matchesStatus = filterStatus.value === 'all' || v.status === filterStatus.value
    return matchesSearch && matchesCategory && matchesPayType && matchesStatus
  })
})

/* ---------------- Add / edit vendor ---------------- */

const editingId = ref(null)

const emptyForm = () => ({
  name: '', phone: '', category: 'Plumbing', working_hours: '',
  status: 'active', is_salaried: false, salary_amount: null,
})

const form = ref(emptyForm())
const formError = ref('')

function openAddForm() {
  editingId.value = null
  form.value = emptyForm()
  formError.value = ''
  showAddForm.value = true
}

function openEditForm(vendor) {
  editingId.value = vendor.id
  form.value = { ...vendor }
  formError.value = ''
  showAddForm.value = true
}

function closeForm() {
  showAddForm.value = false
}

function saveVendor() {
  formError.value = ''

  if (!form.value.name.trim() || !form.value.phone.trim() || !form.value.category) {
    formError.value = 'Name, phone and category are required'
    return
  }
  if (form.value.is_salaried && (!form.value.salary_amount || Number(form.value.salary_amount) <= 0)) {
    formError.value = 'Enter a monthly salary amount for a salaried vendor'
    return
  }

  const payload = {
    ...form.value,
    salary_amount: form.value.is_salaried ? Number(form.value.salary_amount) : null,
  }

  if (editingId.value) {
    const idx = vendors.value.findIndex(v => v.id === editingId.value)
    vendors.value[idx] = { ...vendors.value[idx], ...payload }
    showToast(`${payload.name} updated`)
  } else {
    vendors.value.push({
      id: Math.max(0, ...vendors.value.map(v => v.id)) + 1,
      created_at: new Date().toISOString().slice(0, 10),
      ...payload,
    })
    showToast(`${payload.name} added to the directory`)
  }

  closeForm()
}

function setStatus(vendor, status) {
  vendor.status = status
  showToast(`${vendor.name} marked ${status}`)
}

function removeVendor(vendor) {
  const confirmed = window.confirm(`Remove ${vendor.name} from the directory? This can't be undone.`)
  if (!confirmed) return
  vendors.value = vendors.value.filter(v => v.id !== vendor.id)
  paymentHistory.value = paymentHistory.value.filter(p => p.vendorId !== vendor.id)
  showToast(`${vendor.name} removed`)
}

/* ---------------- Vendor detail / payment history (click a card) ---------------- */

const showVendorDetail = ref(false)
const detailVendor = ref(null)

function openVendorDetail(vendor) {
  detailVendor.value = vendor
  showVendorDetail.value = true
}

function closeVendorDetail() {
  showVendorDetail.value = false
  detailVendor.value = null
}

const detailVendorHistory = computed(() => {
  if (!detailVendor.value) return []
  return paymentHistory.value
    .filter(p => p.vendorId === detailVendor.value.id)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
})

const detailVendorTotalPaid = computed(() =>
  detailVendorHistory.value.reduce((sum, p) => sum + p.amount, 0)
)

/* ---------------- Pay Salaries ---------------- */

const showPaySalaries = ref(false)
const selectedForPayment = ref(new Set())
const paymentStep = ref('review') // 'review' | 'done'
const lastPaidCount = ref(0)
const lastPaidTotal = ref(0)

const salariedActiveVendors = computed(() =>
  vendors.value.filter(v => v.is_salaried && v.status === 'active')
)

function openPaySalaries() {
  paymentStep.value = 'review'
  selectedForPayment.value = new Set(salariedActiveVendors.value.map(v => v.id))
  showPaySalaries.value = true
}

function closePaySalaries() {
  showPaySalaries.value = false
}

function toggleSelected(id) {
  const s = selectedForPayment.value
  if (s.has(id)) s.delete(id); else s.add(id)
  selectedForPayment.value = new Set(s)
}

const selectedVendors = computed(() =>
  salariedActiveVendors.value.filter(v => selectedForPayment.value.has(v.id))
)

const totalToPay = computed(() =>
  selectedVendors.value.reduce((sum, v) => sum + (v.salary_amount || 0), 0)
)

function confirmPaySalaries() {
  if (selectedVendors.value.length === 0) return
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

  selectedVendors.value.forEach(v => {
    paymentHistory.value.unshift({
      id: `PAY-${1000 + paymentHistory.value.length + 1}`,
      vendorId: v.id, vendorName: v.name, amount: v.salary_amount, date: today,
    })
  })

  lastPaidCount.value = selectedVendors.value.length
  lastPaidTotal.value = totalToPay.value
  paymentStep.value = 'done'
  showToast(`Paid ${lastPaidCount.value} vendor(s) · ₹${lastPaidTotal.value.toLocaleString('en-IN')} total`)
}

/* ---------------- Toast ---------------- */

const toastVisible = ref(false)
const toastText = ref('')
let toastTimer = null

function showToast(text) {
  toastText.value = text
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2600)
}
</script>

<template>
  <div class="vendor-directory">

    <!-- header -->
    <div class="page-header">
      <div>
        <h2>Vendor Directory</h2>
        <p class="page-sub">{{ vendors.length }} vendors registered</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="openPaySalaries">💰 Pay Salaries</button>
        <button class="btn-add" @click="openAddForm">+ Add Vendor</button>
      </div>
    </div>

    <!-- search and filter -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by name or phone..."
        class="search-input"
      />
      <div class="filters-row">
        <select v-model="filterCategory" class="filter-select">
          <option value="all">All Categories</option>
          <option v-for="cat in categories.filter(c => c !== 'all')" :key="cat" :value="cat">{{ cat }}</option>
        </select>

        <select v-model="filterPayType" class="filter-select">
          <option value="all">All Pay Types</option>
          <option value="salaried">Salaried</option>
          <option value="not_salaried">Not Salaried</option>
        </select>

        <select v-model="filterStatus" class="filter-select">
          <option value="all">All Statuses</option>
          <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
    </div>

    <!-- vendor cards -->
    <div class="vendor-grid">
      <div
        v-for="vendor in filteredVendors"
        :key="vendor.id"
        class="vendor-card"
        @click="openVendorDetail(vendor)"
      >
        <!-- card header -->
        <div class="card-header">
          <div class="vendor-avatar">
            {{ vendor.name.charAt(0) }}
          </div>
          <div class="vendor-info">
            <span class="vendor-name">{{ vendor.name }}</span>
            <span class="vendor-category">{{ vendor.category }}</span>
          </div>
          <span :class="['status-badge', vendor.status]">
            {{ vendor.status }}
          </span>
        </div>

        <span v-if="vendor.is_salaried" class="pay-tag">
          💰 Salaried · ₹{{ vendor.salary_amount?.toLocaleString('en-IN') }}/mo
        </span>

        <!-- card body -->
        <div class="card-body">
          <div class="info-row">
            <span class="info-label">Phone</span>
            <span class="info-value">{{ vendor.phone }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Hours</span>
            <span class="info-value">{{ vendor.working_hours || '—' }}</span>
          </div>
        </div>

        <!-- card actions -->
        <div class="card-actions" @click.stop>
          <button class="action-btn" @click="openEditForm(vendor)">Edit</button>
          <select
            class="action-select"
            :value="vendor.status"
            @change="setStatus(vendor, $event.target.value)"
          >
            <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
          </select>
          <button class="action-btn danger" @click="removeVendor(vendor)">
            Remove
          </button>
        </div>
      </div>

      <!-- empty state -->
      <div v-if="filteredVendors.length === 0" class="empty-state">
        <p>No vendors found</p>
        <span>Try a different search or filter</span>
      </div>
    </div>

    <!-- add / edit vendor modal -->
    <div v-if="showAddForm" class="modal-overlay" @click.self="closeForm">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingId ? 'Edit Vendor' : 'Add New Vendor' }}</h3>
          <button class="close-btn" @click="closeForm">✕</button>
        </div>

        <div class="modal-body">
          <label>Name *</label>
          <input v-model="form.name" type="text" placeholder="Vendor or business name" class="n-input" />

          <label>Phone *</label>
          <input v-model="form.phone" type="text" placeholder="+91 98XXX XXXXX" class="n-input" />

          <label>Category *</label>
          <select v-model="form.category" class="n-input">
            <option v-for="cat in categories.filter(c => c !== 'all')" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>

          <label>Working Hours</label>
          <input v-model="form.working_hours" type="text" placeholder="e.g. 9 AM – 6 PM" class="n-input" />

          <label>Status</label>
          <select v-model="form.status" class="n-input">
            <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
          </select>

          <button
            type="button"
            :class="['salaried-toggle', { active: form.is_salaried }]"
            @click="form.is_salaried = !form.is_salaried"
          >
            <span class="toggle-dot"></span>
            This vendor is paid a monthly salary, not per job
          </button>

          <template v-if="form.is_salaried">
            <label>Monthly Salary (₹) *</label>
            <input v-model="form.salary_amount" type="number" min="0" placeholder="e.g. 18000" class="n-input" />
          </template>

          <p v-if="formError" class="error-msg">{{ formError }}</p>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="closeForm">Cancel</button>
          <button class="btn-primary" @click="saveVendor">{{ editingId ? 'Save Changes' : 'Add Vendor' }}</button>
        </div>
      </div>
    </div>

    <!-- vendor detail / payment history modal (opens on card click) -->
    <div v-if="showVendorDetail" class="modal-overlay" @click.self="closeVendorDetail">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>{{ detailVendor?.name }}</h3>
            <span class="modal-sub">{{ detailVendor?.category }} · {{ detailVendor?.phone }}</span>
          </div>
          <button class="close-btn" @click="closeVendorDetail">✕</button>
        </div>

        <div class="modal-body">
          <template v-if="detailVendor?.is_salaried">
            <div class="detail-summary">
              <span>Monthly salary</span>
              <strong>₹{{ detailVendor.salary_amount?.toLocaleString('en-IN') }}</strong>
            </div>
            <div class="detail-summary">
              <span>Total paid to date</span>
              <strong>₹{{ detailVendorTotalPaid.toLocaleString('en-IN') }}</strong>
            </div>

            <p class="section-label">Payment History</p>
            <div v-if="detailVendorHistory.length === 0" class="empty-inline">
              No payments recorded yet.
            </div>
            <div v-else class="history-list">
              <div v-for="p in detailVendorHistory" :key="p.id" class="history-row">
                <span>{{ p.date }}</span>
                <span class="history-amount">₹{{ p.amount.toLocaleString('en-IN') }}</span>
              </div>
            </div>
          </template>

          <template v-else>
            <p class="empty-inline">This vendor is paid per job, not a monthly salary — no payment history to show here.</p>
          </template>
        </div>
      </div>
    </div>

    <!-- pay salaries modal -->
    <div v-if="showPaySalaries" class="modal-overlay" @click.self="closePaySalaries">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>Pay Salaries</h3>
            <span class="modal-sub">Active, salaried vendors only</span>
          </div>
          <button class="close-btn" @click="closePaySalaries">✕</button>
        </div>

        <div class="modal-body">

          <template v-if="paymentStep === 'review'">

            <div v-if="salariedActiveVendors.length === 0" class="empty-inline">
              No active salaried vendors right now.
            </div>

            <template v-else>
              <div class="pay-list">
                <label v-for="v in salariedActiveVendors" :key="v.id" class="pay-row">
                  <input
                    type="checkbox"
                    :checked="selectedForPayment.has(v.id)"
                    @change="toggleSelected(v.id)"
                  />
                  <span class="pay-row-name">{{ v.name }}</span>
                  <span class="pay-row-cat">{{ v.category }}</span>
                  <span class="pay-row-amount">₹{{ v.salary_amount.toLocaleString('en-IN') }}</span>
                </label>
              </div>

              <div class="pay-summary">
                <span>Paying <strong>{{ selectedVendors.length }}</strong> vendor(s)</span>
                <span class="pay-summary-total">₹{{ totalToPay.toLocaleString('en-IN') }}</span>
              </div>

              <button class="btn-primary" :disabled="selectedVendors.length === 0" @click="confirmPaySalaries">
                Confirm Payment
              </button>
            </template>
          </template>

          <template v-else>
            <div class="pay-done">
              <div class="pay-done-icon">✓</div>
              <p class="pay-done-title">Payment recorded</p>
              <p class="pay-done-sub">
                Paid {{ lastPaidCount }} vendor(s) · ₹{{ lastPaidTotal.toLocaleString('en-IN') }} total
              </p>
            </div>
            <button class="btn-primary" @click="closePaySalaries">Done</button>
          </template>

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
.vendor-directory {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: var(--font-size-3xl);
  font-weight: 800;
  color: var(--color-text-primary);
  letter-spacing: -0.4px;
}

.page-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-top: 4px;
}

.header-actions { display: flex; gap: 10px; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 220px;
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

.filters-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-select {
  height: 42px;
  padding: 0 12px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  outline: none;
  cursor: pointer;
  text-transform: capitalize;
  transition: border-color var(--transition-fast);
}

.filter-select:focus { border-color: var(--c-600); }

.vendor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.vendor-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-fast);
  cursor: pointer;
}

.vendor-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.vendor-avatar {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--c-800), var(--c-500));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 800;
  font-size: var(--font-size-lg);
  flex-shrink: 0;
}

.vendor-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.vendor-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vendor-category {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.status-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: capitalize;
  flex-shrink: 0;
}

.status-badge.active {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.status-badge.inactive {
  background: var(--badge-closed-bg);
  color: var(--badge-closed-text);
}

.status-badge.blacklisted {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}

.pay-tag {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  background: #FCEED9;
  color: #8A5A00;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  gap: 10px;
  font-size: var(--font-size-sm);
}

.info-label {
  color: var(--color-text-muted);
  min-width: 46px;
  flex-shrink: 0;
}

.info-value {
  color: var(--color-text-primary);
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid var(--color-border);
}

.action-btn {
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.action-btn:hover {
  border-color: var(--c-600);
  color: var(--c-800);
}

.action-btn.danger:hover {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.action-select {
  padding: 8px 6px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: capitalize;
  cursor: pointer;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
}

.empty-state p {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin-bottom: 6px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
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
  max-width: 480px;
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
  font-size: var(--font-size-md);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.close-btn:hover {
  background: var(--color-border);
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
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
  transition: border-color var(--transition-fast);
  font-family: var(--font-family);
  margin-top: 6px;
}

.n-input:focus {
  border-color: var(--c-600);
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-top: 10px;
}

.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 24px 22px;
  border-top: 1px solid var(--color-border);
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

.btn-add:hover {
  background: var(--c-900);
}

.btn-outline {
  height: 42px;
  padding: 0 18px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--c-800);
  font-size: var(--font-size-md);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.btn-outline:hover { border-color: var(--c-600); background: var(--color-surface-soft); }

.btn-primary {
  width: 100%;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.btn-primary:hover:not(:disabled) {
  background: var(--c-900);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-footer .btn-primary { width: auto; flex: 1; }

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

/* salaried toggle in the add/edit form */
.salaried-toggle {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  height: 42px;
  padding: 0 13px;
  margin-top: 12px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface-soft);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.salaried-toggle.active {
  border-color: var(--c-800);
  background: #FCEED9;
  color: #8A5A00;
}

.toggle-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid var(--color-border-strong);
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.salaried-toggle.active .toggle-dot {
  background: #8A5A00;
  border-color: #8A5A00;
  box-shadow: inset 0 0 0 2.5px #FCEED9;
}

/* vendor detail / payment history modal */
.detail-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 2px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.detail-summary strong {
  font-size: var(--font-size-md);
  color: var(--c-800);
}

.section-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-top: 16px;
  margin-bottom: 8px;
}

/* pay salaries modal */
.empty-inline {
  text-align: center;
  padding: 24px 10px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.pay-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pay-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  cursor: pointer;
}

.pay-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  accent-color: var(--c-800);
}

.pay-row-name { flex: 1; font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-primary); }
.pay-row-cat { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.pay-row-amount { font-size: var(--font-size-sm); font-weight: 800; color: var(--c-800); }

.pay-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 14px 0 4px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: #EAF6FB;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-primary);
}

.pay-summary-total { font-size: var(--font-size-lg); font-weight: 800; color: var(--c-800); }

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.history-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-soft);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.history-amount { font-weight: 700; color: var(--color-text-primary); }

.pay-done {
  text-align: center;
  padding: 20px 10px 10px;
}

.pay-done-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: var(--color-success-bg);
  color: var(--color-success-text);
  font-size: 24px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pay-done-title { font-size: var(--font-size-lg); font-weight: 800; color: var(--color-text-primary); }
.pay-done-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

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