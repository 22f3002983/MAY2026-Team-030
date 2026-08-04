<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

const searchQuery = ref('')
const showAddModal = ref(false)
const selectedResident = ref(null)
const showDetailModal = ref(false)
const loading = ref(true)
const submitting = ref(false)

const newResident = ref({
  name: '',
  email: '',
  password: '',
  tower: '',
  floor: null,
  unit_number: '',
  flat_number: '',
  phone: '',
  members: 1,
  occupant_type: 'owner',
})

const formError = ref('')

const residents = ref([])

// ── Tower dropdown: real towers from the backend + an "add new tower"
// option that reveals a free-text input ────────────────────────────
const towerList   = ref([])
const NEW_TOWER   = '__new__'
const newTowerName = ref('')

async function fetchTowers() {
  try {
    const res = await api.get('/flats/blocks')
    towerList.value = res.data.blocks
  } catch (err) {
    console.error('Failed to load tower list', err)
  }
}

// ── Phone: fixed +91 prefix, digits-only, max 10 ────────────────────
const phoneDigits = ref('')

function onPhoneInput(e) {
  phoneDigits.value = e.target.value.replace(/\D/g, '').slice(0, 10)
}

async function fetchResidents() {
  loading.value = true
  try {
    const res = await api.get('/auth/residents')
    residents.value = res.data.residents
  } catch (err) {
    console.error('Failed to load residents', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchResidents()
  fetchTowers()
})

const filtered = computed(() => {
  if (!searchQuery.value) return residents.value
  const q = searchQuery.value.toLowerCase()
  return residents.value.filter(r =>
    (r.name || '').toLowerCase().includes(q) ||
    (r.flat_number || '').toLowerCase().includes(q) ||
    (r.phone || '').includes(q)
  )
})

const onboardedCount = computed(() => residents.value.filter(r => r.is_onboarded).length)
const pendingCount   = computed(() => residents.value.filter(r => !r.is_onboarded).length)

function openDetail(resident) {
  selectedResident.value = resident
  showDetailModal.value  = true
}

async function addResident() {
  formError.value = ''

  const resolvedTower = newResident.value.tower === NEW_TOWER
    ? newTowerName.value.trim()
    : newResident.value.tower

  if (!newResident.value.name || !newResident.value.email || !newResident.value.password ||
      !newResident.value.flat_number) {
    formError.value = 'Name, email, password and flat number are required'
    return
  }
  if (phoneDigits.value.length !== 10) {
    formError.value = 'Phone number must be exactly 10 digits'
    return
  }
  if (newResident.value.password.length < 6) {
    formError.value = 'Password must be at least 6 characters'
    return
  }
  if (!resolvedTower || newResident.value.floor === null || !newResident.value.unit_number) {
    formError.value = 'Tower, floor and unit number are required to register a new flat'
    return
  }

  submitting.value = true
  try {
    const res = await api.post('/auth/register', {
      email:          newResident.value.email.trim().toLowerCase(),
      password:       newResident.value.password,
      role:           'resident',
      name:           newResident.value.name,
      phone:          '+91' + phoneDigits.value,
      tower:          resolvedTower,
      floor:          newResident.value.floor,
      unit_number:    newResident.value.unit_number,
      flat_number:    newResident.value.flat_number,
      occupant_type:  newResident.value.occupant_type,
      household_size: newResident.value.members,
    })

    await fetchResidents()
    await fetchTowers() // pick up a brand-new tower if one was just added

    newResident.value = { name: '', email: '', password: '', tower: '', floor: null, unit_number: '', flat_number: '', phone: '', members: 1, occupant_type: 'owner' }
    newTowerName.value = ''
    phoneDigits.value = ''
    showAddModal.value = false

    alert('Resident added. They can log in with the email/password you set, and change their password afterward.')
  } catch (err) {
    formError.value = err.response?.data?.error || 'Failed to add resident'
  } finally {
    submitting.value = false
  }
}

const regenerating = ref(false)
const regenerateError = ref('')

async function regenerateInvite(resident) {
  regenerateError.value = ''
  regenerating.value = true
  try {
    const res = await api.post('/auth/invite', { resident_id: resident.id })
    // update the currently-open resident + the row in the list so both reflect the new code
    if (selectedResident.value && selectedResident.value.id === resident.id) {
      selectedResident.value = { ...selectedResident.value, invite_code: res.data.invite_code }
    }
    const idx = residents.value.findIndex(r => r.id === resident.id)
    if (idx !== -1) {
      residents.value[idx] = { ...residents.value[idx], invite_code: res.data.invite_code }
    }
  } catch (err) {
    regenerateError.value = err.response?.data?.error || 'Failed to regenerate invite code'
  } finally {
    regenerating.value = false
  }
}

function duesClass(status) {
  if (status === 'paid')    return 'dues-paid'
  if (status === 'overdue') return 'dues-overdue'
  if (status === 'none')    return 'dues-none'
  return 'dues-pending'
}

// derive a display status from pending_due/has_dues since the backend
// doesn't return a separate dues_status field
function duesDisplay(resident) {
  if (resident.pending_due === null || resident.pending_due === undefined) return '—'
  if (!resident.has_dues) return 'No dues yet'
  if (resident.pending_due <= 0) return 'Paid'
  return `₹${resident.pending_due.toLocaleString('en-IN')}`
}
function duesStatusOf(resident) {
  if (resident.pending_due === null || resident.pending_due === undefined) return 'pending'
  if (!resident.has_dues) return 'none'
  if (resident.pending_due <= 0) return 'paid'
  return 'pending'
}
</script>

<template>
  <div class="sec-residents">

    <div class="page-header">
      <div>
        <h2>Residents</h2>
        <p class="page-sub">{{ residents.length }} flats · {{ onboardedCount }} onboarded · {{ pendingCount }} pending</p>
      </div>
      <button class="btn-add" @click="showAddModal = true">+ Add Resident</button>
    </div>

    <input
      v-model="searchQuery"
      type="text"
      placeholder="Search by name, flat or phone..."
      class="search-input"
    />

    <!-- residents table -->
    <div class="table-wrap">
      <table class="residents-table">
        <thead>
          <tr>
            <th>Resident</th>
            <th>Flat</th>
            <th>Phone</th>
            <th>Members</th>
            <th>Outstanding Dues</th>
            <th>Type</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="empty-row">Loading...</td>
          </tr>
          <tr
            v-for="r in filtered"
            :key="r.id"
            class="resident-row"
            @click="openDetail(r)"
          >
            <td>
              <div class="resident-cell">
                <div class="resident-avatar">
                  {{ r.is_onboarded ? r.name.charAt(0) : '?' }}
                </div>
                <span class="resident-name">{{ r.name }}</span>
              </div>
            </td>
            <td class="flat-cell">{{ r.flat_number || '—' }}</td>
            <td class="phone-cell">{{ r.phone }}</td>
            <td class="members-cell">{{ r.household_size || '—' }}</td>
            <td>
              <span :class="['dues-badge', duesClass(duesStatusOf(r))]">
                {{ duesDisplay(r) }}
              </span>
            </td>
            <td>
              <span class="type-badge">{{ r.occupant_type }}</span>
            </td>
            <td>
              <span :class="['onboard-badge', r.is_onboarded ? 'active' : 'pending']">
                {{ r.is_onboarded ? 'Active' : 'Pending' }}
              </span>
            </td>
          </tr>

          <tr v-if="!loading && filtered.length === 0">
            <td colspan="7" class="empty-row">No residents found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- resident detail modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>{{ selectedResident?.name }}</h3>
            <span class="modal-sub">{{ selectedResident?.flat_number }} · {{ selectedResident?.occupant_type }}</span>
          </div>
          <button class="close-btn" @click="showDetailModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div class="detail-grid">
            <div class="detail-row">
              <span class="d-label">Phone</span>
              <span class="d-value">{{ selectedResident?.phone }}</span>
            </div>
            <div class="detail-row">
              <span class="d-label">Flat</span>
              <span class="d-value">{{ selectedResident?.flat_number || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="d-label">Members</span>
              <span class="d-value">{{ selectedResident?.household_size || '—' }}</span>
            </div>
            <div class="detail-row">
              <span class="d-label">Type</span>
              <span class="d-value" style="text-transform: capitalize">{{ selectedResident?.occupant_type }}</span>
            </div>
            <div class="detail-row">
              <span class="d-label">Dues</span>
              <span :class="['d-value', duesClass(duesStatusOf(selectedResident || {}))]">
                {{ selectedResident ? duesDisplay(selectedResident) : '—' }}
              </span>
            </div>
            <div class="detail-row">
              <span class="d-label">Status</span>
              <span :class="['onboard-badge', selectedResident?.is_onboarded ? 'active' : 'pending']">
                {{ selectedResident?.is_onboarded ? 'Active' : 'Pending onboarding' }}
              </span>
            </div>
            <div v-if="selectedResident?.invite_code" class="detail-row">
              <span class="d-label">Invite code</span>
              <span class="d-value invite-code">{{ selectedResident?.invite_code }}</span>
            </div>
            <div v-if="selectedResident && !selectedResident.is_onboarded" class="detail-row">
              <span class="d-label"></span>
              <button class="btn-secondary" style="flex: none; height: 34px; padding: 0 14px;" :disabled="regenerating" @click="regenerateInvite(selectedResident)">
                {{ regenerating ? 'Regenerating...' : 'Regenerate invite code' }}
              </button>
            </div>
            <p v-if="regenerateError" class="error-msg">{{ regenerateError }}</p>

          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showDetailModal = false">Close</button>
        </div>
      </div>
    </div>

    <!-- add resident modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Add Resident</h3>
          <button class="close-btn" @click="showAddModal = false">✕</button>
        </div>

        <div class="modal-body">
          <label>Name *</label>
          <input v-model="newResident.name" type="text" placeholder="Full name" class="n-input" />

          <label>Email *</label>
          <input v-model="newResident.email" type="email" placeholder="resident@example.com" class="n-input" />

          <label>Password *</label>
          <input v-model="newResident.password" type="text" placeholder="Starting password (min 6 chars)" class="n-input" />

         <div class="two-col">
            <div>
              <label>Tower *</label>
              <select v-model="newResident.tower" class="n-input n-select">
                <option value="" disabled>Select tower</option>
                <option v-for="t in towerList" :key="t" :value="t">Tower {{ t }}</option>
                <option :value="NEW_TOWER">+ Add new tower</option>
              </select>
              <input
                v-if="newResident.tower === NEW_TOWER"
                v-model="newTowerName"
                type="text"
                placeholder="New tower name, e.g. E"
                class="n-input"
                style="margin-top: 8px;"
              />
            </div>
            <div>
              <label>Floor *</label>
              <input v-model.number="newResident.floor" type="number" min="0" class="n-input" />
            </div>
          </div>
          <div class="two-col">
            <div>
              <label>Unit number *</label>
              <input v-model="newResident.unit_number" type="text" placeholder="e.g. 402" class="n-input" />
            </div>
            <div>
              <label>Flat number *</label>
              <input v-model="newResident.flat_number" type="text" placeholder="e.g. A-402" class="n-input" />
            </div>
          </div>

          <label>Phone *</label>
          <div class="phone-input-group">
            <span class="phone-prefix">+91</span>
            <input
              :value="phoneDigits"
              @input="onPhoneInput"
              type="text"
              inputmode="numeric"
              maxlength="10"
              placeholder="98XXXXXXXX"
              class="n-input phone-input"
            />
          </div>

          <div class="two-col">
            <div>
              <label>Household size</label>
              <input v-model.number="newResident.members" type="number" min="1" class="n-input" />
            </div>
            <div>
              <label>Type</label>
              <select v-model="newResident.occupant_type" class="n-input">
                <option value="owner">Owner</option>
                <option value="tenant">Tenant</option>
              </select>
            </div>
          </div>

          <p v-if="formError" class="error-msg">{{ formError }}</p>

          <div class="invite-note">
            The resident can log in immediately with the email and password you set here, and change their password later from their account settings.
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn-primary" :disabled="submitting" @click="addResident">
            {{ submitting ? 'Adding...' : 'Add Resident' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.sec-residents {
  max-width: var(--content-max-width);
}

.phone-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phone-prefix {
  height: 42px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  color: var(--color-text-secondary);
  font-weight: 600;
  flex-shrink: 0;
}

.phone-input {
  flex: 1;
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

.search-input {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  margin-bottom: 16px;
  transition: border-color var(--transition-fast);
}

.search-input:focus { border-color: var(--c-600); }

.table-wrap {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
}

.residents-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.residents-table thead tr {
  border-bottom: 1px solid var(--color-border);
}

.residents-table th {
  padding: 12px 20px;
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  background: var(--color-surface-soft);
  white-space: nowrap;
}

.residents-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.residents-table tbody tr:last-child td { border-bottom: none; }

.resident-row {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.resident-row:hover { background: var(--color-surface-muted); }

.resident-cell {
  display: flex;
  align-items: center;
  gap: 11px;
}

.resident-avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: linear-gradient(150deg, var(--c-800), var(--c-500));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-sm);
}

.resident-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-primary);
}

.flat-cell    { font-weight: 600; color: var(--color-text-secondary); }
.phone-cell   { color: var(--color-text-secondary); }
.members-cell { color: var(--color-text-secondary); font-weight: 600; }

.dues-badge {
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.dues-paid    { color: var(--color-success-text); }
.dues-pending { color: var(--color-warning-text); }
.dues-overdue { color: var(--color-danger-text);  }
.dues-none    { color: var(--color-text-secondary); }

.type-badge {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: capitalize;
}

.onboard-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.onboard-badge.active  { background: var(--color-success-bg); color: var(--color-success-text); }
.onboard-badge.pending { background: var(--color-warning-bg); color: var(--color-warning-text); }

.empty-row {
  text-align: center;
  color: var(--color-text-muted);
  padding: 40px;
  font-size: var(--font-size-md);
}

/* modals */
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
  text-transform: capitalize;
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

.detail-grid {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: 11px 16px;
  border-bottom: 1px solid var(--color-border);
  gap: 12px;
}

.detail-row:last-child { border-bottom: none; }

.d-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  width: 80px;
  flex-shrink: 0;
}

.d-value {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.invite-code {
  font-family: ui-monospace, monospace;
  color: var(--c-800);
  font-size: var(--font-size-md);
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

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

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