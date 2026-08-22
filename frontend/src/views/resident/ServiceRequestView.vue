<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '../../api/axios' // adjust path if this view lives elsewhere
import { useAuthStore } from '../../stores/auth' // adjust path if needed

const auth = useAuthStore()
const currentResident = computed(() => ({
  flat: auth.user?.flat_number || '',
}))

/* ---------------------------------------------------------------
   Home Services — PERSONAL channel.
   This has nothing to do with the secretary or community issues.
   Resident books a society-empanelled vendor directly for work
   inside their own flat, tracks it, and pays the vendor from here.
--------------------------------------------------------------- */

const categoryOptions = ['Plumbing', 'Electrical', 'Carpentry', 'Cleaning', 'Other']

// backend uses profession words, frontend uses problem-type words — these
// are NOT interchangeable via simple casing, need an explicit map both ways.
// This pair is for ServiceRequest.category specifically (the category
// stored on the resident's own request) — unrelated to vendor.category.
const CATEGORY_TO_BACKEND = {
  Plumbing: 'plumber', Electrical: 'electrician', Carpentry: 'carpenter',
  Cleaning: 'cleaner', Other: 'other',
}
const CATEGORY_TO_FRONTEND = {
  plumber: 'Plumbing', electrician: 'Electrical', carpenter: 'Carpentry',
  cleaner: 'Cleaning', other: 'Other',
}

// vendor.category now matches CommunityIssue.category exactly (problem-type
// words, not professions) — a separate map from CATEGORY_TO_BACKEND above,
// used only for filtering which vendors show up for a given UI category.
const CATEGORY_TO_VENDOR_CATEGORY = {
  Plumbing: 'plumbing', Electrical: 'electrical', Carpentry: 'carpentry',
  Cleaning: 'cleaning', Other: 'other',
}

const estimatedMinutesByCategory = {
  Plumbing: 60, Electrical: 45, Carpentry: 90, Cleaning: 45, Other: 60,
}

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s }

function formatMinutes(mins) {
  if (!mins) return '—'
  if (mins < 60) return `${mins} min`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m === 0 ? `${h} hr` : `${h} hr ${m} min`
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  if (isNaN(d)) return iso
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

// backend returns "HH:MM:SS" (str() of a Time column); <input type="time">
// and our own display both want "HH:MM"
function trimSeconds(t) {
  return t ? t.slice(0, 5) : ''
}

/* ---------------- Vendors ---------------- */
// society-empanelled vendors available for personal, in-flat jobs. Filtering
// to VALID service categories naturally excludes salaried common-area staff
// (security/gardener/pest_control aren't service-request categories).

const vendors = ref([])

async function fetchVendors() {
  try {
    const res = await api.get('/vendors', { params: { status: 'active' } })
    const serviceCategories = new Set(Object.values(CATEGORY_TO_VENDOR_CATEGORY))
    vendors.value = (res.data.vendors || [])
      .filter(v => serviceCategories.has(v.category))
      .map(v => ({ id: v.id, name: v.name, category: v.category }))
  } catch (err) {
    console.error('Failed to load vendors', err)
  }
}

function vendorsForCategory(frontendCat) {
  const vendorCat = CATEGORY_TO_VENDOR_CATEGORY[frontendCat]
  return vendors.value.filter(v => v.category === vendorCat)
}

/* ---------------- Requests ---------------- */

const requests = ref([])
const loading = ref(true)
const loadError = ref('')

function mapRequest(r) {
  return {
    id: r.id,
    category: CATEGORY_TO_FRONTEND[r.category] || capitalize(r.category),
    desc: r.description,
    vendor: r.vendor_name,
    vendorId: r.vendor_id,
    date: r.scheduled_date,
    time: trimSeconds(r.scheduled_time),
    durationMinutes: r.duration_minutes,
    duration: formatMinutes(r.duration_minutes),
    status: capitalize(r.status),
    paymentStatus: r.payment_status,
    paymentAmount: r.payment_amount,
    createdOn: r.created_at ? formatDate(r.created_at.slice(0, 10)) : '',
    rating: r.rating,
  }
}

async function fetchRequests() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/service-requests')
    requests.value = (res.data.requests || []).map(mapRequest)
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load requests'
    console.error('Failed to load service requests', err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchVendors()
  await fetchRequests()
})

const statusFilters = ['All', 'Scheduled', 'Completed', 'Cancelled']
const filterStatus = ref('All')
const expandedId = ref(null)

const filtered = computed(() => {
  if (filterStatus.value === 'All') return requests.value
  return requests.value.filter(r => r.status === filterStatus.value)
})

function toggle(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function statusClass(s) {
  if (s === 'Scheduled') return 'status-progress'
  if (s === 'Completed') return 'status-resolved'
  if (s === 'Cancelled') return 'status-rejected'
  return ''
}

function categoryIcon(cat) {
  const map = { Plumbing: '🔧', Electrical: '⚡', Cleaning: '🧹', Carpentry: '🪚', Other: '🛠️' }
  return map[cat] || '🛠️'
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

/* ---------------- Raise / reschedule modal ---------------- */

const showRaise = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const formCategory = ref('Plumbing')
const formDesc     = ref('')
const formVendor   = ref('')
const formDate     = ref('')
const formTime     = ref('')
const aiNote       = ref('')

const estimatedDuration = computed(() => formatMinutes(estimatedMinutesByCategory[formCategory.value] || 60))

const aiSuggestedCategory = ref(null)
const aiThinking = ref(false)

// a suggestion is only valid for the text it was generated from — clear it
// (but don't re-call the AI) once the resident edits the description, so an
// outdated badge doesn't linger from partial/earlier wording
watch(formDesc, () => {
  aiSuggestedCategory.value = null
})

// triggered explicitly by a button rather than as-you-type: avoids calling
// the model on half-typed descriptions, and avoids the suggestion flickering
// as someone pauses mid-sentence to think
async function suggestCategory() {
  const val = formDesc.value.trim()
  if (!val) return
  aiThinking.value = true
  aiSuggestedCategory.value = null
  try {
    const res = await api.post('/service-requests/suggest-category', { description: val })
    aiSuggestedCategory.value = res.data.category ? CATEGORY_TO_FRONTEND[res.data.category] : null
  } catch (err) {
    console.error('Failed to get AI category suggestion', err)
  } finally {
    aiThinking.value = false
  }
}

function syncVendorToCategory() {
  const stillValid = vendorsForCategory(formCategory.value).some(v => v.name === formVendor.value)
  if (!stillValid) formVendor.value = ''
}

function applyAiCategory() {
  if (!aiSuggestedCategory.value) return
  formCategory.value = aiSuggestedCategory.value
  syncVendorToCategory()
}

function onCategoryChange() {
  syncVendorToCategory()
}

function openNewRequest() {
  editingId.value = null
  formCategory.value = 'Plumbing'
  formDesc.value = ''
  formVendor.value = ''
  formDate.value = ''
  formTime.value = ''
  aiNote.value = ''
  aiSuggestedCategory.value = null
  showRaise.value = true
}

function openReschedule(r) {
  editingId.value = r.id
  formCategory.value = r.category
  formDesc.value = r.desc
  formVendor.value = r.vendor
  formDate.value = r.date
  formTime.value = r.time
  aiNote.value = ''
  aiSuggestedCategory.value = null
  showRaise.value = true
}

function closeRaise() {
  showRaise.value = false
}

function autoAssignVendor() {
  const candidates = vendorsForCategory(formCategory.value)
  if (!candidates.length) return
  const loadOf = (v) => requests.value.filter(r => r.vendor === v.name && r.status === 'Scheduled').length
  const best = [...candidates].sort((a, b) => loadOf(a) - loadOf(b))[0]
  formVendor.value = best.name
  aiNote.value = `AI suggested ${best.name} · usually takes about ${estimatedDuration.value}`
}

const canSubmit = computed(() =>
  formCategory.value && formDesc.value.trim() && formVendor.value && formDate.value && formTime.value
)

async function submitRequest() {
  if (!canSubmit.value || submitting.value) return
  const vendorObj = vendors.value.find(v => v.name === formVendor.value)
  if (!vendorObj) return

  submitting.value = true
  try {
    if (editingId.value) {
      await api.patch(`/service-requests/${editingId.value}`, {
        category: CATEGORY_TO_BACKEND[formCategory.value],
        description: formDesc.value.trim(),
        vendor_id: vendorObj.id,
        scheduled_date: formDate.value,
        scheduled_time: formTime.value,
      })
      showToast(`Request updated — new slot booked`)
    } else {
      const res = await api.post('/service-requests', {
        category: CATEGORY_TO_BACKEND[formCategory.value],
        description: formDesc.value.trim(),
        vendor_id: vendorObj.id,
        scheduled_date: formDate.value,
        scheduled_time: formTime.value,
      })
      showToast(`Booked with ${formVendor.value}`)
    }
    await fetchRequests()
    closeRaise()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to save request')
  } finally {
    submitting.value = false
  }
}

async function cancelRequest(r) {
  try {
    await api.patch(`/service-requests/${r.id}/cancel`)
    showToast(`Request cancelled`)
    await fetchRequests()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to cancel request')
  }
}

/* ---------------- Complete + pay ---------------- */

const showComplete = ref(null)
const payAmount = ref('')
const paying = ref(false)

function openComplete(r) {
  showComplete.value = r
  payAmount.value = ''
}

function closeComplete() {
  showComplete.value = null
}

async function confirmPay() {
  const r = showComplete.value
  if (!payAmount.value || !r || paying.value) return

  paying.value = true
  try {
    const res = await api.patch(`/service-requests/${r.id}/complete`, { amount: Number(payAmount.value) })
    showToast(res.data.message)
    await fetchRequests()
    closeComplete()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to record payment')
  } finally {
    paying.value = false
  }
}

async function rate(r, stars) {
  try {
    const res = await api.patch(`/service-requests/${r.id}/rate`, { rating: stars })
    showToast(res.data.message)
    await fetchRequests()
  } catch (err) {
    showToast(err.response?.data?.error || 'Failed to submit rating')
  }
}
</script>

<template>
  <div class="home-services">

    <div class="page-header">
      <div>
        <h2>Home Services</h2>
        <p class="page-sub">Book and track vendors for your flat · {{ currentResident.flat }}</p>
      </div>
      <button class="btn-raise" @click="openNewRequest">+ New Request</button>
    </div>

    <!-- status filters -->
    <div class="status-pill-group">
      <button
        v-for="s in statusFilters"
        :key="s"
        :class="['status-pill', { active: filterStatus === s }]"
        @click="filterStatus = s"
      >
        {{ s }}
      </button>
    </div>

    <!-- load state (ADDED — loading/loadError were tracked but never shown) -->
    <p v-if="loadError" class="error-msg">{{ loadError }}</p>
    <div v-if="loading" class="empty-state">
      <p>Loading your requests...</p>
    </div>

    <!-- request cards -->
    <div v-else class="requests-list">
      <div v-for="r in filtered" :key="r.id" class="request-card">

        <button class="card-header" @click="toggle(r.id)">
          <div class="cat-icon">{{ categoryIcon(r.category) }}</div>
          <div class="card-summary">
            <div class="card-top">
              <span class="request-id">{{ r.vendor }}</span>
              <span class="request-cat">· {{ r.category }}</span>
            </div>
            <p class="request-desc">{{ r.desc }}</p>
          </div>
          <span class="request-date">{{ formatDate(r.date) }}</span>
          <span :class="['status-badge', statusClass(r.status)]">{{ r.status }}</span>
          <span class="chevron" :class="{ rotated: expandedId === r.id }">›</span>
        </button>

        <div v-if="expandedId === r.id" class="card-detail">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">Vendor</span>
              <span class="detail-value">{{ r.vendor }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">{{ r.status === 'Cancelled' ? 'Was scheduled for' : 'Scheduled for' }}</span>
              <span class="detail-value">{{ formatDate(r.date) }}, {{ r.time }}</span>
            </div>
            <!-- <div class="detail-item">
              <span class="detail-label">Estimated time</span>
              <span class="detail-value">{{ r.duration || '—' }}</span>
            </div> -->
            <div class="detail-item">
              <span class="detail-label">Requested on</span>
              <span class="detail-value">{{ r.createdOn }}</span>
            </div>
          </div>

          <div class="detail-desc">{{ r.desc }}</div>

          <!-- scheduled: manage -->
          <div v-if="r.status === 'Scheduled'" class="action-row">
            <button class="action-btn" @click="openReschedule(r)">Reschedule</button>
            <button class="action-btn" @click="openComplete(r)">Mark Complete &amp; Pay</button>
            <button class="action-btn danger" @click="cancelRequest(r)">Cancel Request</button>
          </div>

          <!-- completed: payment + feedback -->
          <div v-else-if="r.status === 'Completed'" class="completed-block">
            <div class="pay-row">
              <span class="pay-text pay-paid">Paid ₹{{ r.paymentAmount }} to {{ r.vendor }}</span>
            </div>
            <div class="feedback-row">
              <span class="feedback-label">Rate this service:</span>
              <span class="stars">
                <span
                  v-for="n in 5" :key="n"
                  class="star"
                  :class="{ filled: r.rating && n <= r.rating }"
                  @click="rate(r, n)"
                >★</span>
              </span>
            </div>
          </div>

          <!-- cancelled -->
          <div v-else class="cancelled-note">This request was cancelled — no payment was made.</div>
        </div>

      </div>

      <div v-if="filtered.length === 0" class="empty-state">
        <p>No requests found</p>
        <span>Try a different status filter, or book a new service</span>
      </div>
    </div>

    <!-- raise / reschedule modal -->
    <div v-if="showRaise" class="modal-overlay" @click.self="closeRaise">
      <div class="modal modal-xl">
        <div class="modal-header">
          <div>
            <h3>{{ editingId ? 'Reschedule Request' : 'Book a Home Service' }}</h3>
            <span class="modal-sub">For your flat — {{ currentResident.flat }} only</span>
          </div>
          <button class="close-btn" @click="closeRaise">✕</button>
        </div>

        <div class="modal-body">
          <div class="one-col">

            <!-- left: form -->
            <div class="form-col">

              <label>Describe the issue</label>
              <textarea
                v-model="formDesc"
                class="n-input n-textarea"
                rows="3"
                placeholder="e.g. Kitchen tap has been leaking since this morning"
              ></textarea>
              <button
                type="button"
                class="suggest-category-btn"
                :disabled="!formDesc.trim() || aiThinking"
                @click="suggestCategory"
              >
                {{ aiThinking ? '✦ Thinking...' : '✨ Suggest category' }}
              </button>

              <div class="field-header">
                <label>Category</label>
                <span
                  v-if="aiSuggestedCategory"
                  class="ai-badge"
                  @click="applyAiCategory"
                  title="Click to apply"
                >
                  ✦ AI suggested: {{ aiSuggestedCategory }}
                </span>
              </div>
              <select v-model="formCategory" class="n-input" @change="onCategoryChange">
                <option v-for="c in categoryOptions" :key="c" :value="c">{{ categoryIcon(c) }} {{ c }}</option>
              </select>

              <!-- <p class="duration-hint">
                ⏱ Estimated time for {{ formCategory }}: <strong>{{ estimatedDuration }}</strong>
              </p> -->

              <div class="vendor-row">
                <div class="vendor-select-wrap">
                  <label>Vendor</label>
                  <select v-model="formVendor" class="n-input">
                    <option value="" disabled>Choose a vendor...</option>
                    <option v-for="v in vendorsForCategory(formCategory)" :key="v.name" :value="v.name">{{ v.name }}</option>
                  </select>
                </div>
                <button class="btn-outline ai-suggest-btn" @click="autoAssignVendor">Find Matching Vendor</button>
              </div>
              <p v-if="aiNote" class="ai-note">{{ aiNote }}</p>

              <div class="slot-row">
                <div class="slot-field">
                  <label>Date</label>
                  <input type="date" v-model="formDate" class="n-input" />
                </div>
                <div class="slot-field">
                  <label>Time</label>
                  <input type="time" v-model="formTime" class="n-input" />
                </div>
              </div>

              <!-- FIXED: disabled during submit + shows progress text, prevents double-submit -->
              <button class="btn-primary" :disabled="!canSubmit || submitting" @click="submitRequest">
                {{ submitting ? 'Saving...' : (editingId ? 'Save New Slot' : 'Book Request') }}
              </button>
            </div>

            <!-- right: AI helper + resolution times -->
            <!-- <div class="side-panel">

              <div class="ai-panel">
                <div class="ai-panel-title">✦ How AI helps</div>
                <p class="ai-panel-text">
                  Once you've described the issue, tap "Suggest category" and Niwaas reads it to suggest the most likely category — so your request reaches the right vendor faster, with a realistic time estimate.
                </p>
              </div>

              <div class="resolution-panel">
                <div class="resolution-title">Estimated time for this request</div>
                <div class="resolution-item highlighted">
                  <span class="resolution-icon">{{ categoryIcon(formCategory) }}</span>
                  <span class="resolution-text">
                    {{ formCategory }} · <strong>{{ estimatedDuration }}</strong>
                  </span>
                </div>
                <p class="resolution-note">Updates automatically based on the category detected from your description.</p>
              </div>

            </div> -->

          </div>
        </div>
      </div>
    </div>

    <!-- complete + pay modal -->
    <div v-if="showComplete" class="modal-overlay" @click.self="closeComplete">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>Mark Complete &amp; Pay</h3>
            <span class="modal-sub">{{ showComplete.id }} · {{ showComplete.vendor }}</span>
          </div>
          <button class="close-btn" @click="closeComplete">✕</button>
        </div>

        <div class="modal-body">
          <label>Amount paid (₹)</label>
          <input type="number" v-model="payAmount" class="n-input" placeholder="e.g. 500" min="0" />
          <p class="helper-text">This confirms the job is done and records what you paid {{ showComplete.vendor }} directly.</p>

          <!-- FIXED: disabled while paying, shows progress text -->
          <button class="btn-primary" :disabled="!payAmount || paying" @click="confirmPay">
            {{ paying ? 'Processing...' : 'Confirm & Close' }}
          </button>
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
.home-services {
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

.btn-raise {
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

.btn-raise:hover { background: var(--c-900); }

.status-pill-group {
  display: flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 4px;
  margin-bottom: 20px;
  width: fit-content;
}

.status-pill {
  padding: 8px 13px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.status-pill.active { background: var(--c-800); color: #fff; }

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-bottom: 14px;
}

.requests-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.request-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.card-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  text-align: left;
  transition: background var(--transition-fast);
}

.card-header:hover { background: var(--color-surface-muted); }

.cat-icon {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: #EAF6FB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.card-summary { flex: 1; min-width: 0; }

.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}

.request-id { font-size: var(--font-size-md); font-weight: 800; color: var(--c-900); }
.request-cat { font-size: var(--font-size-sm); color: var(--color-text-muted); }

.request-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 340px;
}

.request-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.status-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-resolved { background: var(--color-success-bg); color: var(--color-success-text); }
.status-rejected { background: var(--color-danger-bg);  color: var(--color-danger-text);  }

.chevron {
  font-size: 20px;
  color: var(--color-border-strong);
  transition: transform var(--transition-base);
  flex-shrink: 0;
}

.chevron.rotated { transform: rotate(90deg); }

.card-detail {
  padding: 0 18px 18px 76px;
  border-top: 1px solid var(--color-border);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 16px 0;
}

.detail-item { display: flex; flex-direction: column; gap: 3px; }

.detail-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.detail-value { font-size: var(--font-size-md); font-weight: 600; color: var(--color-text-primary); }

.detail-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.55;
  background: var(--color-surface-soft);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin-bottom: 14px;
}

.action-row { display: flex; gap: 10px; flex-wrap: wrap; }

.action-btn {
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--c-800);
  background: #E9F4FA;
  padding: 9px 15px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.action-btn:hover { background: #D4EBF7; }
.action-btn.danger { color: var(--color-danger-text); background: var(--color-danger-bg); }
.action-btn.danger:hover { background: #F5C6C6; }

.completed-block { display: flex; flex-direction: column; gap: 12px; }

.pay-text { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-muted); }
.pay-paid { color: var(--color-success-text); }

.feedback-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }

.feedback-label { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-primary); }

.stars { font-size: 19px; letter-spacing: 2px; }
.star { color: var(--color-border-strong); cursor: pointer; }
.star.filled { color: #E0A030; }

.cancelled-note {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.empty-state { text-align: center; padding: 60px 20px; }

.empty-state p {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.empty-state span { font-size: var(--font-size-sm); color: var(--color-text-muted); }

/* modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
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
  max-width: 460px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-xl { max-width: 720px; }

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.modal-header h3 { font-size: var(--font-size-xl); font-weight: 700; }

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
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.close-btn:hover { background: var(--color-border); }

.modal-body {
  padding: 20px 24px 26px;
  overflow-y: auto;
}

/* two-col layout inside the raise/reschedule modal */
.two-col {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 18px;
  align-items: start;
}

.form-col { display: flex; flex-direction: column; }

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
  background: #DCEBF8;
  padding: 4px 9px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.ai-badge:hover   { background: #C8DEF3; }

.suggest-category-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
  background: transparent;
  border: 1.5px solid var(--color-border-soft);
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  margin: 8px 0 14px;
  transition: all var(--transition-fast);
}

.suggest-category-btn:hover:not(:disabled) { border-color: var(--c-600); background: #EAF6FB; }
.suggest-category-btn:disabled { opacity: 0.5; cursor: not-allowed; }

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
  margin-bottom: 6px;
}

.form-col > label:first-child { margin-top: 0; }

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
  min-height: 64px;
  padding: 10px 13px;
  resize: vertical;
  line-height: 1.5;
}

.duration-hint {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--c-800);
  background: #EAF6FB;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  margin: 4px 0 2px;
}

.vendor-row { display: flex; align-items: flex-end; gap: 8px; margin-top: 12px; }
.vendor-select-wrap { flex: 1; min-width: 0; }
.vendor-select-wrap label { margin-top: 0; }
.ai-suggest-btn { height: 42px; white-space: nowrap; }

.ai-note {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: #6B3FA0;
  margin-top: 8px;
}

.slot-row { display: flex; gap: 10px; margin-top: 4px; }
.slot-field { flex: 1; min-width: 0; }

.helper-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 6px;
  margin-bottom: 12px;
  line-height: 1.5;
}

.btn-primary {
  width: 100%;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 16px;
  transition: background var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: var(--c-900); }

.btn-outline {
  height: 42px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--c-800);
  font-size: var(--font-size-sm);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.btn-outline:hover:not(:disabled) { border-color: var(--c-600); background: var(--color-surface-soft); }

/* side panel (AI helper + estimated time) */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-panel {
  background: linear-gradient(155deg, var(--c-800), var(--c-500));
  border-radius: var(--radius-lg);
  padding: 18px;
  color: #fff;
}

.ai-panel-title {
  font-size: var(--font-size-md);
  font-weight: 800;
  margin-bottom: 10px;
}

.ai-panel-text {
  font-size: var(--font-size-sm);
  line-height: 1.6;
  opacity: 0.9;
}

.resolution-panel {
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.resolution-title {
  font-size: var(--font-size-md);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 12px;
}

.resolution-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-md);
}

.resolution-item.highlighted {
  background: #EAF6FB;
  box-shadow: inset 0 0 0 1.5px var(--c-600);
}

.resolution-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.resolution-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.resolution-note {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 10px;
  line-height: 1.5;
}

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