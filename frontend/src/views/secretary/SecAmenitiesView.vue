<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'

// =============================================================================
// Secretary Amenities Management — mirrors the resident AmenitiesView.vue's
// data-layer conventions (same normalize functions, same backend contract),
// plus secretary-only actions: amenity CRUD, maintenance toggle, and
// approve/reject on pending bookings.
// =============================================================================

// ---------------------------------------------------------------------------
// Data layer — normalize backend shape into what the templates expect
// ---------------------------------------------------------------------------
const amenitiesRaw = ref([])
const bookingsRaw = ref([])       // every booking, across all residents
const amenityBookingsCache = ref({}) // { [amenityId]: normalized bookings[] }
const loading = ref(false)

function normalizeAmenity(a) {
  return {
    id: a.id,
    name: a.name,
    category: a.type,
    icon: a.icon,
    location: a.location,
    description: a.description,
    capacity: a.capacity,
    air_conditioned: a.is_air_conditioned,
    decoratable: a.is_decoratable,
    features: a.features || [],
    special_booking: a.special_booking,
    booking_type: a.booking_type,
    pricing: {
      type: a.pricing?.type ?? null,
      rate: a.pricing?.rate ?? null,
      minUnits: a.pricing?.min_units ?? 1,
      unitLabel: a.pricing?.unit_label ?? null,
    },
    status: a.status,
    status_until: a.status_until,
  }
}

function bookingFrontendStatus(b) {
  if (b.status === 'pending') return 'pending_approval'
  if (b.status === 'cancelled') return 'cancelled'
  if (b.status === 'rejected') return 'rejected'
  if (b.status === 'approved') {
    if (b.payment_status === 'pending') return 'awaiting_payment'
    const end = b.end_date || b.date
    const today = new Date().toISOString().slice(0, 10)
    return end < today ? 'completed' : 'confirmed'
  }
  return b.status
}

function normalizeBooking(b) {
  return {
    id: b.id,
    amenity_id: b.amenity_id,
    user_id: b.resident_id,
    user_name: b.resident_name,
    start_date: b.date,
    end_date: b.end_date || b.date,
    start_time: b.start_time,
    end_time: b.end_time,
    price: b.price,
    event_type: b.event_type,
    guests: b.guests,
    status: bookingFrontendStatus(b),
    rejected_reason: b.rejected_reason,
    created_at: b.created_at,
  }
}

function attachAmenity(b) {
  return { ...b, amenity: amenitiesRaw.value.find((a) => a.id === b.amenity_id) }
}

const amenities = computed(() => amenitiesRaw.value)

const pendingApprovals = computed(() =>
  bookingsRaw.value
    .filter((b) => b.status === 'pending_approval')
    .map(attachAmenity)
    .sort((a, b) => new Date(a.created_at || a.start_date) - new Date(b.created_at || b.start_date))
)

async function fetchAmenities() {
  loading.value = true
  try {
    const { data } = await api.get('/amenities')
    amenitiesRaw.value = data.amenities.map(normalizeAmenity)
  } finally {
    loading.value = false
  }
}

async function fetchAllBookings() {
  const { data } = await api.get('/amenities/bookings')
  bookingsRaw.value = data.bookings.map(normalizeBooking)
}

async function fetchAmenityBookings(amenityId) {
  const { data } = await api.get(`/amenities/${amenityId}/bookings`)
  amenityBookingsCache.value[amenityId] = data.bookings.map(normalizeBooking)
}

function bookingTimeframe(booking) {
  const today = new Date().toISOString().slice(0, 10)
  if (['cancelled', 'rejected', 'completed'].includes(booking.status)) return 'past'
  if (booking.end_date < today) return 'past'
  if (booking.start_date <= today && today <= booking.end_date) return 'ongoing'
  return 'upcoming'
}

function allBookingsForAmenity(amenityId) {
  return (amenityBookingsCache.value[amenityId] || [])
    .map((b) => ({ ...b, timeframe: bookingTimeframe(b) }))
    .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
}

// ---------------------------------------------------------------------------
// Static helpers
// ---------------------------------------------------------------------------
function isBookable(amenity) {
  return !!amenity.booking_type
}
function statusLabel(status) {
  return { available: 'Available', booked: 'Booked', maintenance: 'Maintenance', closed: 'Closed' }[status] || status
}
function bookingStatusLabel(status) {
  return {
    pending_approval: 'Pending approval',
    awaiting_payment: 'Approved · payment due',
    confirmed: 'Confirmed',
    completed: 'Completed',
    cancelled: 'Cancelled',
    rejected: 'Not approved',
  }[status] || status
}
function calculatePrice(amenity, units) {
  if (!amenity.pricing?.rate) return 0
  return amenity.pricing.rate * Math.max(units, amenity.pricing.minUnits || 1)
}

// ---------------------------------------------------------------------------
// Secretary — amenity CRUD
// ---------------------------------------------------------------------------
function toBackendPayload(form) {
  return {
    name: form.name,
    type: form.category,
    icon: form.icon,
    location: form.location,
    description: form.description,
    capacity: form.capacity || null,
    is_air_conditioned: form.air_conditioned,
    is_decoratable: form.decoratable,
    features: form.featuresText ? form.featuresText.split(',').map((f) => f.trim()).filter(Boolean) : [],
    special_booking: form.special_booking ?? false,
    booking_type: form.booking_type || null,
    status: form.status || 'available',
    status_until: form.status === 'maintenance' ? (form.status_until || null) : null,
    pricing: form.pricingType
      ? {
          type: form.pricingType,
          rate: Number(form.rate) || 0,
          min_units: Number(form.minUnits) || 1,
          unit_label: form.unitLabel,
        }
      : { type: null },
  }
}

async function addAmenityApi(form) {
  const { data } = await api.post('/amenities', toBackendPayload(form))
  const amenity = normalizeAmenity(data.amenity)
  amenitiesRaw.value.push(amenity)
  return amenity
}

async function updateAmenityApi(id, form) {
  const { data } = await api.patch(`/amenities/${id}`, toBackendPayload(form))
  const amenity = normalizeAmenity(data.amenity)
  const i = amenitiesRaw.value.findIndex((a) => a.id === id)
  if (i !== -1) amenitiesRaw.value[i] = amenity
  return amenity
}

async function deleteAmenityApi(id) {
  try {
    await api.delete(`/amenities/${id}`)
    amenitiesRaw.value = amenitiesRaw.value.filter((a) => a.id !== id)
    return { ok: true }
  } catch (e) {
    return { ok: false, reason: e?.response?.data?.error || 'Could not delete amenity.' }
  }
}

async function setStatusApi(id, status, statusUntil) {
  const { data } = await api.patch(`/amenities/${id}/status`, { status, status_until: statusUntil })
  const amenity = normalizeAmenity(data.amenity)
  const i = amenitiesRaw.value.findIndex((a) => a.id === id)
  if (i !== -1) amenitiesRaw.value[i] = amenity
  return amenity
}

// ---------------------------------------------------------------------------
// Secretary — approvals
// ---------------------------------------------------------------------------
async function approveBookingApi(bookingId) {
  const { data } = await api.patch(`/amenities/bookings/${bookingId}/approve`)
  const i = bookingsRaw.value.findIndex((b) => b.id === bookingId)
  if (i !== -1) bookingsRaw.value[i] = normalizeBooking(data.booking)
}

async function rejectBookingApi(bookingId, reason) {
  const { data } = await api.patch(`/amenities/bookings/${bookingId}/reject`, { reason })
  const i = bookingsRaw.value.findIndex((b) => b.id === bookingId)
  if (i !== -1) bookingsRaw.value[i] = normalizeBooking(data.booking)
}

// ---------------------------------------------------------------------------
// Recommendation engine — same rule-based scoring as the resident page,
// available here so the secretary can suggest a fit when booking by phone.
// ---------------------------------------------------------------------------
const EVENT_AFFINITY = {
  'Birthday party': { 4: 3, 5: 3, 3: 2, 10: 2 },
  'Wedding function': { 1: 3, 10: 1 },
  'Family gathering': { 3: 3, 5: 2, 4: 2 },
  'Movie / watch party': { 7: 3 },
  'Kids party': { 3: 3, 4: 2, 5: 1 },
  'Guests staying over': { 2: 3 },
  'Small meeting': { 1: 2, 7: 1 },
  'Sports session': { 6: 3 },
}
const EVENT_TYPES = Object.keys(EVENT_AFFINITY)

function recommend({ eventType, guests, budget, hours = 3 }) {
  const candidates = amenitiesRaw.value.filter((a) => isBookable(a) && a.status === 'available')

  const scored = candidates.map((a) => {
    let score = (EVENT_AFFINITY[eventType]?.[a.id] || 0) * 10

    if (a.capacity && guests) {
      score += a.capacity >= guests ? 15 - Math.min(15, (a.capacity - guests) * 0.3) : -20
    }

    const units = a.pricing.type === 'hourly' ? hours : 1
    const price = calculatePrice(a, units)
    if (budget) {
      score += price <= budget ? 10 - Math.min(10, ((budget - price) / budget) * 10) : -15
    }

    return { amenity: a, score, estimatedPrice: price }
  })

  return scored
    .filter((s) => s.score > -10)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
}

// =============================================================================
// PAGE STATE
// =============================================================================
const toastMsg = ref('')
let toastTimer = null
function showToast(text) {
  toastMsg.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toastMsg.value = ''), 3200)
}

const exclusiveAmenities = computed(() => amenities.value.filter((a) => a.category === 'exclusive'))
const publicAmenities = computed(() => amenities.value.filter((a) => a.category === 'public'))
const infraAmenities = computed(() => amenities.value.filter((a) => a.category === 'unbookable'))

async function handleApprove(booking) {
  await approveBookingApi(booking.id)
  showToast(`${booking.amenity?.name} booking approved`)
}

async function handleReject(booking) {
  const reason = window.prompt(`Reason for rejecting this ${booking.amenity?.name} booking?`, '')
  if (reason === null) return
  await rejectBookingApi(booking.id, reason)
  showToast(`${booking.amenity?.name} booking rejected`)
}

// ---------------------------------------------------------------------------
// Recommendation panel state
// ---------------------------------------------------------------------------
const recOpen = ref(false)
const recEventType = ref(EVENT_TYPES[0])
const recGuests = ref(20)
const recBudget = ref(2000)
const recHours = ref(3)
const recResults = ref(null)

function getRecommendation() {
  recResults.value = recommend({
    eventType: recEventType.value,
    guests: recGuests.value,
    budget: recBudget.value,
    hours: recHours.value,
  })
}

// ---------------------------------------------------------------------------
// Add/Edit amenity modal
// ---------------------------------------------------------------------------
const showFormModal = ref(false)
const editingId = ref(null)
const formError = ref('')

const emptyForm = () => ({
  name: '', category: 'exclusive', icon: '⭐', location: '', description: '',
  capacity: null, air_conditioned: false, decoratable: false, featuresText: '',
  special_booking: false, booking_type: null,
  pricingType: null, rate: '', minUnits: 1, unitLabel: '',
  status: 'available', status_until: '',
})
const form = ref(emptyForm())

function openAddForm() {
  editingId.value = null
  form.value = emptyForm()
  formError.value = ''
  showFormModal.value = true
}

function openEditForm(amenity) {
  editingId.value = amenity.id
  form.value = {
    name: amenity.name,
    category: amenity.category,
    icon: amenity.icon || '⭐',
    location: amenity.location || '',
    description: amenity.description || '',
    capacity: amenity.capacity,
    air_conditioned: amenity.air_conditioned,
    decoratable: amenity.decoratable,
    featuresText: (amenity.features || []).join(', '),
    special_booking: amenity.special_booking || false,
    booking_type: amenity.booking_type,
    pricingType: amenity.pricing?.type || null,
    rate: amenity.pricing?.rate ?? '',
    minUnits: amenity.pricing?.minUnits ?? 1,
    unitLabel: amenity.pricing?.unitLabel || '',
    status: amenity.status,
    status_until: amenity.status_until || '',
  }
  formError.value = ''
  showFormModal.value = true
}

function closeFormModal() {
  showFormModal.value = false
}

async function submitForm() {
  formError.value = ''
  if (!form.value.name.trim()) {
    formError.value = 'Name is required'
    return
  }
  try {
    if (editingId.value) {
      await updateAmenityApi(editingId.value, form.value)
      showToast(`${form.value.name} updated`)
    } else {
      await addAmenityApi(form.value)
      showToast(`${form.value.name} added`)
    }
    closeFormModal()
  } catch (e) {
    formError.value = e?.response?.data?.error || 'Could not save amenity.'
  }
}

async function handleDelete(amenity) {
  if (!window.confirm(`Delete ${amenity.name}? This can't be undone.`)) return
  const result = await deleteAmenityApi(amenity.id)
  if (result.ok) {
    showToast(`${amenity.name} deleted`)
  } else {
    showToast(result.reason)
  }
}

async function handleToggleMaintenance(amenity) {
  if (amenity.status === 'maintenance') {
    await setStatusApi(amenity.id, 'available', null)
    showToast(`${amenity.name} marked available`)
  } else {
    const until = window.prompt(`Under maintenance until (YYYY-MM-DD), or leave blank:`, '')
    if (until === null) return
    await setStatusApi(amenity.id, 'maintenance', until || null)
    showToast(`${amenity.name} marked under maintenance`)
  }
}

// ---------------------------------------------------------------------------
// Booking history modal (click an amenity card)
// ---------------------------------------------------------------------------
const showHistoryModal = ref(false)
const historyAmenity = ref(null)

async function openHistory(amenity) {
  historyAmenity.value = amenity
  showHistoryModal.value = true
  await fetchAmenityBookings(amenity.id)
}

function closeHistory() {
  showHistoryModal.value = false
  historyAmenity.value = null
}

const historyBookings = computed(() =>
  historyAmenity.value ? allBookingsForAmenity(historyAmenity.value.id) : []
)

// =============================================================================
onMounted(async () => {
  await fetchAmenities()
  await fetchAllBookings()
})
</script>

<template>
  <div class="sec-amenities">
    <div class="page-header">
      <div>
        <h2>Amenities Management</h2>
        <p class="page-sub">Manage the catalogue, approve bookings, and toggle availability</p>
      </div>
      <button class="btn-add" @click="openAddForm">+ Add Amenity</button>
    </div>

    <div v-if="toastMsg" class="toast-banner">✓ {{ toastMsg }}</div>

    <!-- Pending approvals -->
    <div v-if="pendingApprovals.length" class="approvals-panel">
      <div class="section-title">Pending Approvals ({{ pendingApprovals.length }})</div>
      <div class="approval-list">
        <div v-for="b in pendingApprovals" :key="b.id" class="approval-row">
          <span class="approval-icon">{{ b.amenity?.icon }}</span>
          <div class="approval-info">
            <div class="approval-name">{{ b.amenity?.name }} — {{ b.user_name }}</div>
            <div class="approval-meta">
              {{ b.start_date }}{{ b.end_date !== b.start_date ? ' → ' + b.end_date : '' }}
              <template v-if="b.start_time"> · {{ b.start_time }}–{{ b.end_time }}</template>
              · {{ b.event_type }} · {{ b.guests }} guests
              <template v-if="b.price"> · ₹{{ b.price.toLocaleString('en-IN') }}</template>
            </div>
          </div>
          <div class="approval-actions">
            <button class="approve-btn" @click="handleApprove(b)">Approve</button>
            <button class="reject-btn" @click="handleReject(b)">Reject</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Recommendation panel -->
    <div class="rec-panel">
      <button class="rec-panel-toggle" @click="recOpen = !recOpen">
        <span class="rec-ai-badge">✨ Suggest a fit (booking by phone)</span>
        <span class="rec-chevron" :class="{ up: recOpen }">⌄</span>
      </button>

      <div v-if="recOpen" class="rec-panel-body">
        <div class="rec-form-grid">
          <div class="rec-field">
            <label class="rec-field-label">Event type</label>
            <select v-model="recEventType" class="rec-input">
              <option v-for="t in EVENT_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="rec-field">
            <label class="rec-field-label">Guests</label>
            <input type="number" min="1" v-model.number="recGuests" class="rec-input" />
          </div>
          <div class="rec-field">
            <label class="rec-field-label">Budget (₹)</label>
            <input type="number" min="0" step="100" v-model.number="recBudget" class="rec-input" />
          </div>
          <div class="rec-field">
            <label class="rec-field-label">Duration (hrs, if hourly)</label>
            <input type="number" min="1" v-model.number="recHours" class="rec-input" />
          </div>
        </div>
        <button class="rec-get-btn" @click="getRecommendation">Get suggestions</button>

        <div v-if="recResults" class="rec-results">
          <div v-if="recResults.length === 0" class="rec-empty">No great match within these constraints.</div>
          <div v-for="(r, i) in recResults" :key="r.amenity.id" class="rec-result-card">
            <span class="rec-result-icon">{{ r.amenity.icon }}</span>
            <div>
              <div class="rec-result-name">{{ r.amenity.name }}<span v-if="i === 0" class="rec-best-tag">Best match</span></div>
              <div class="rec-result-meta">Fits {{ r.amenity.capacity }} · ₹{{ r.estimatedPrice.toLocaleString('en-IN') }} est.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- exclusive -->
    <div class="section-title" style="margin-top: 24px">Exclusive Booking</div>
    <div class="amenity-grid">
      <div v-for="amenity in exclusiveAmenities" :key="amenity.id" class="amenity-card" @click="openHistory(amenity)">
        <div class="card-header-area">
          <span class="card-icon">{{ amenity.icon }}</span>
          <span :class="['status-tag', amenity.status]">
            <span class="status-dot"></span>{{ statusLabel(amenity.status) }}
            <template v-if="amenity.status_until && amenity.status !== 'available'"> · till {{ amenity.status_until }}</template>
          </span>
        </div>
        <div class="card-body-area">
          <div>
            <span class="amenity-name">{{ amenity.name }}</span>
            <p class="amenity-desc">{{ amenity.description }}</p>
          </div>
          <div class="card-body-bottom">
            <span class="exclusive-tag">{{ isBookable(amenity) ? (amenity.booking_type === 'automatic' ? 'Auto-approve' : 'Needs approval') : 'Not bookable' }}</span>
          </div>
          <div class="card-actions" @click.stop>
            <button class="action-btn" @click="openEditForm(amenity)">Edit</button>
            <button class="action-btn" @click="handleToggleMaintenance(amenity)">
              {{ amenity.status === 'maintenance' ? 'Clear maintenance' : 'Maintenance' }}
            </button>
            <button class="action-btn danger" @click="handleDelete(amenity)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- public -->
    <div class="section-title" style="margin-top: 32px">Shared Facilities</div>
    <div class="amenity-grid">
      <div v-for="amenity in publicAmenities" :key="amenity.id" class="amenity-card" @click="openHistory(amenity)">
        <div class="card-header-area">
          <span class="card-icon">{{ amenity.icon }}</span>
          <span :class="['status-tag', amenity.status]">
            <span class="status-dot"></span>{{ statusLabel(amenity.status) }}
            <template v-if="amenity.status_until && amenity.status !== 'available'"> · till {{ amenity.status_until }}</template>
          </span>
        </div>
        <div class="card-body-area">
          <div>
            <span class="amenity-name">{{ amenity.name }}</span>
            <p class="amenity-desc">{{ amenity.description }}</p>
          </div>
          <div class="card-body-bottom">
            <span class="public-tag">{{ isBookable(amenity) ? 'Bookable for private events' : 'No booking needed' }}</span>
          </div>
          <div class="card-actions" @click.stop>
            <button class="action-btn" @click="openEditForm(amenity)">Edit</button>
            <button class="action-btn" @click="handleToggleMaintenance(amenity)">
              {{ amenity.status === 'maintenance' ? 'Clear maintenance' : 'Maintenance' }}
            </button>
            <button class="action-btn danger" @click="handleDelete(amenity)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- infrastructure -->
    <div class="section-title" style="margin-top: 32px">Infrastructure</div>
    <div class="amenity-grid">
      <div v-for="amenity in infraAmenities" :key="amenity.id" class="amenity-card" @click="openHistory(amenity)">
        <div class="card-header-area infra">
          <span class="card-icon">{{ amenity.icon }}</span>
          <span :class="['status-tag', amenity.status]">
            <span class="status-dot"></span>{{ statusLabel(amenity.status) }}
            <template v-if="amenity.status_until && amenity.status !== 'available'"> · till {{ amenity.status_until }}</template>
          </span>
        </div>
        <div class="card-body-area">
          <div>
            <span class="amenity-name">{{ amenity.name }}</span>
            <p class="amenity-desc">{{ amenity.description }}</p>
          </div>
          <div class="card-body-bottom">
            <span class="info-tag">📍 {{ amenity.location }}</span>
          </div>
          <div class="card-actions" @click.stop>
            <button class="action-btn" @click="openEditForm(amenity)">Edit</button>
            <button class="action-btn" @click="handleToggleMaintenance(amenity)">
              {{ amenity.status === 'maintenance' ? 'Clear maintenance' : 'Maintenance' }}
            </button>
            <button class="action-btn danger" @click="handleDelete(amenity)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ ADD / EDIT MODAL ============ -->
    <div v-if="showFormModal" class="modal-overlay" @click.self="closeFormModal">
      <div class="modal-sheet form-modal">
        <button class="modal-close-btn" @click="closeFormModal">✕</button>
        <div class="modal-content">
          <h3>{{ editingId ? 'Edit Amenity' : 'Add New Amenity' }}</h3>

          <label class="form-label">Name *</label>
          <input v-model="form.name" type="text" class="n-input" placeholder="e.g. Rooftop Lounge" />

          <div class="form-row">
            <div>
              <label class="form-label">Category</label>
              <select v-model="form.category" class="n-input">
                <option value="exclusive">Exclusive (bookable)</option>
                <option value="public">Public (shared)</option>
                <option value="unbookable">Infrastructure</option>
              </select>
            </div>
            <div>
              <label class="form-label">Icon (emoji)</label>
              <input v-model="form.icon" type="text" class="n-input" placeholder="🏛" />
            </div>
          </div>

          <label class="form-label">Location</label>
          <input v-model="form.location" type="text" class="n-input" placeholder="e.g. Clubhouse · Ground Floor" />

          <label class="form-label">Description</label>
          <textarea v-model="form.description" class="n-input n-textarea" rows="2"></textarea>

          <div class="form-row">
            <div>
              <label class="form-label">Capacity</label>
              <input v-model.number="form.capacity" type="number" min="0" class="n-input" />
            </div>
            <div>
              <label class="form-label">Features (comma-separated)</label>
              <input v-model="form.featuresText" type="text" class="n-input" placeholder="Stage, Sound system" />
            </div>
          </div>

          <div class="form-checks">
            <label class="check-label"><input type="checkbox" v-model="form.air_conditioned" /> Air conditioned</label>
            <label class="check-label"><input type="checkbox" v-model="form.decoratable" /> Decoration allowed</label>
            <label class="check-label"><input type="checkbox" v-model="form.special_booking" /> Special booking (shared facility, exceptionally bookable)</label>
          </div>

          <label class="form-label">Booking type</label>
          <select v-model="form.booking_type" class="n-input">
            <option :value="null">Not bookable</option>
            <option value="automatic">Automatic</option>
            <option value="approval_required">Needs approval</option>
          </select>

          <template v-if="form.booking_type">
            <div class="form-row three">
              <div>
                <label class="form-label">Pricing type</label>
                <select v-model="form.pricingType" class="n-input">
                  <option :value="null">Free</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                </select>
              </div>
              <div v-if="form.pricingType">
                <label class="form-label">Rate (₹)</label>
                <input v-model="form.rate" type="number" min="0" class="n-input" />
              </div>
              <div v-if="form.pricingType">
                <label class="form-label">Min units</label>
                <input v-model.number="form.minUnits" type="number" min="1" class="n-input" />
              </div>
            </div>
            <label v-if="form.pricingType" class="form-label">Unit label</label>
            <input v-if="form.pricingType" v-model="form.unitLabel" type="text" class="n-input" placeholder="e.g. hour, day, night" />
          </template>

          <label class="form-label">Status</label>
          <select v-model="form.status" class="n-input">
            <option value="available">Available</option>
            <option value="maintenance">Maintenance</option>
            <option value="closed">Closed</option>
          </select>
          <template v-if="form.status === 'maintenance'">
            <label class="form-label">Maintenance until</label>
            <input v-model="form.status_until" type="date" class="n-input" />
          </template>

          <p v-if="formError" class="error-msg">{{ formError }}</p>

          <div class="modal-actions">
            <button class="btn-secondary" @click="closeFormModal">Cancel</button>
            <button class="btn-primary" @click="submitForm">{{ editingId ? 'Save Changes' : 'Add Amenity' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ BOOKING HISTORY MODAL ============ -->
    <div v-if="showHistoryModal && historyAmenity" class="modal-overlay" @click.self="closeHistory">
      <div class="modal-sheet">
        <button class="modal-close-btn" @click="closeHistory">✕</button>
        <div class="modal-hero" :class="{ infra: historyAmenity.category === 'unbookable' }">
          <span class="modal-hero-icon">{{ historyAmenity.icon }}</span>
        </div>
        <div class="modal-content">
          <h3>{{ historyAmenity.name }}</h3>
          <p class="modal-location">📍 {{ historyAmenity.location }}</p>

          <div class="section-label">Booking History</div>
          <div v-if="historyBookings.length === 0" class="empty-inline">No bookings yet.</div>
          <div v-else class="history-list">
            <div v-for="b in historyBookings" :key="b.id" class="history-row">
              <div class="history-info">
                <span class="history-resident">{{ b.user_name }}</span>
                <span class="history-meta">
                  {{ b.start_date }}{{ b.end_date !== b.start_date ? ' → ' + b.end_date : '' }}
                  <template v-if="b.start_time"> · {{ b.start_time }}–{{ b.end_time }}</template>
                  · {{ b.event_type }}
                </span>
              </div>
              <span :class="['booking-status', b.status]">{{ bookingStatusLabel(b.status) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- toast -->
  </div>
</template>

<style scoped>
.sec-amenities { max-width: var(--content-max-width); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.btn-add {
  height: 42px; padding: 0 20px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-size: var(--font-size-md); font-weight: 700; white-space: nowrap;
}
.btn-add:hover { background: var(--c-800); }

.toast-banner {
  background: var(--color-success-bg); color: var(--color-success-text);
  border: 1px solid var(--color-success); border-radius: var(--radius-md);
  padding: 12px 16px; font-size: var(--font-size-md); font-weight: 600; margin-bottom: 20px;
}

.section-title { font-size: var(--font-size-xl); font-weight: 700; color: var(--color-text-primary); margin-bottom: 12px; }

/* ---------- Pending approvals ---------- */
.approvals-panel {
  background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-xl);
  padding: 18px; margin-bottom: 20px; box-shadow: var(--shadow-sm);
}
.approval-list { display: flex; flex-direction: column; gap: 10px; }
.approval-row { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: var(--radius-md); background: var(--badge-closed-bg); }
.approval-icon { font-size: 24px; }
.approval-info { flex: 1; min-width: 0; }
.approval-name { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.approval-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.approval-actions { display: flex; gap: 6px; }
.approve-btn { padding: 6px 14px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }
.reject-btn { padding: 6px 14px; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-danger); color: var(--color-danger); font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }

/* ---------- Recommendation panel ---------- */
.rec-panel {
  border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-surface);
  overflow: hidden; margin-bottom: 24px; box-shadow: var(--shadow-sm);
}
.rec-panel-toggle {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%);
}
.rec-ai-badge { color: #fff; font-weight: 700; font-size: var(--font-size-md); }
.rec-chevron { color: #fff; transition: transform var(--transition-fast); }
.rec-chevron.up { transform: rotate(180deg); }
.rec-panel-body { padding: 18px; }
.rec-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.rec-field { display: flex; flex-direction: column; gap: 4px; }
.rec-field-label { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); }
.rec-input { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px 10px; font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary); }
.rec-get-btn { width: 100%; height: 40px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-weight: 700; font-size: var(--font-size-sm); }
.rec-get-btn:hover { background: var(--c-800); }
.rec-results { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.rec-empty { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.rec-result-card { display: flex; align-items: center; gap: 10px; padding: 12px; border-radius: var(--radius-md); background: var(--badge-closed-bg); }
.rec-result-icon { font-size: 26px; }
.rec-result-name { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); display: flex; align-items: center; gap: 8px; }
.rec-best-tag { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: var(--radius-pill); background: var(--color-success-bg); color: var(--color-success-text); }
.rec-result-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }

/* ---------- Grid & cards ---------- */
.amenity-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 8px; }
.amenity-card { background: var(--color-surface); border-radius: var(--radius-xl); border: 1px solid var(--color-border); overflow: hidden; box-shadow: var(--shadow-sm); transition: box-shadow var(--transition-fast); cursor: pointer; }
.amenity-card:hover { box-shadow: var(--shadow-md); }

.card-header-area { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); height: 100px; display: flex; align-items: center; justify-content: center; position: relative; padding: 16px; }
.card-header-area.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.card-icon { font-size: 32px; filter: grayscale(1) brightness(5); }

.status-tag { position: absolute; top: 12px; right: 12px; display: flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; background: rgba(255,255,255,0.92); }
.status-tag.available { color: var(--color-success-text); }
.status-tag.booked { color: var(--color-info-text); }
.status-tag.maintenance { color: var(--color-warning-text); }
.status-tag.closed { color: var(--badge-closed-text); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-tag.available .status-dot { background: var(--color-success); }
.status-tag.booked .status-dot { background: var(--c-600); }
.status-tag.maintenance .status-dot { background: var(--color-warning); }
.status-tag.closed .status-dot { background: var(--badge-closed-text); }

.card-body-area { padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.amenity-name { display: block; font-size: var(--font-size-md); font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.amenity-desc { font-size: var(--font-size-xs); color: var(--color-text-secondary); line-height: 1.5; }
.card-body-bottom { display: flex; align-items: center; }

.exclusive-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--color-warning-bg); color: var(--color-warning-text); font-size: var(--font-size-xs); font-weight: 700; }
.public-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--color-success-bg); color: var(--color-success-text); font-size: var(--font-size-xs); font-weight: 700; }
.info-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--badge-closed-text); font-size: var(--font-size-xs); font-weight: 700; }

.card-actions { display: flex; gap: 6px; padding-top: 8px; border-top: 1px solid var(--color-border); }
.action-btn { flex: 1; padding: 6px; border-radius: var(--radius-sm); border: 1.5px solid var(--color-border-soft); background: var(--color-surface); font-size: 11px; font-weight: 600; color: var(--color-text-secondary); }
.action-btn:hover { border-color: var(--c-600); color: var(--c-800); }
.action-btn.danger:hover { border-color: var(--color-danger); color: var(--color-danger); }

/* ---------- Modal ---------- */
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.5); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-sheet { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto; position: relative; box-shadow: var(--shadow-md); }
.form-modal { max-width: 560px; }
.modal-close-btn { position: absolute; top: 12px; right: 12px; z-index: 2; width: 32px; height: 32px; border-radius: 50%; background: rgba(0,0,0,0.06); color: var(--color-text-primary); font-size: 14px; display: flex; align-items: center; justify-content: center; }
.modal-hero { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); height: 110px; display: flex; align-items: center; justify-content: center; }
.modal-hero.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.modal-hero-icon { font-size: 40px; filter: grayscale(1) brightness(5); }
.modal-content { padding: 20px; }
.modal-content h3 { font-size: var(--font-size-xl); font-weight: 800; color: var(--color-text-primary); }
.modal-location { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.form-label { display: block; font-size: var(--font-size-sm); font-weight: 600; color: var(--c-800); margin-top: 12px; margin-bottom: 4px; }
.n-input { width: 100%; height: 42px; padding: 0 13px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); font-size: var(--font-size-md); background: var(--color-surface-soft); color: var(--color-text-primary); outline: none; font-family: var(--font-family); }
.n-input:focus { border-color: var(--c-600); }
.n-textarea { height: auto; min-height: 56px; padding: 10px 13px; resize: vertical; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-row.three { grid-template-columns: 1fr 1fr 1fr; }
.form-checks { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.check-label { display: flex; align-items: center; gap: 8px; font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.error-msg { font-size: var(--font-size-sm); color: var(--color-danger); margin-top: 10px; }

.modal-actions { margin-top: 20px; display: flex; gap: 10px; }
.btn-primary { flex: 1; height: 44px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-md); font-weight: 700; }
.btn-primary:hover { background: var(--c-800); }
.btn-secondary { flex: 1; height: 44px; border-radius: var(--radius-md); border: 1.5px solid var(--color-border-soft); background: var(--color-surface); color: var(--color-text-secondary); font-size: var(--font-size-md); font-weight: 600; }

.section-label { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.4px; margin-top: 16px; margin-bottom: 10px; }
.empty-inline { text-align: center; padding: 20px 10px; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.history-list { display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto; }
.history-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 12px; border-radius: var(--radius-md); background: var(--badge-closed-bg); }
.history-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.history-resident { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.history-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.booking-status { font-size: var(--font-size-xs); font-weight: 700; padding: 4px 10px; border-radius: var(--radius-pill); white-space: nowrap; background: var(--color-info-bg, var(--badge-closed-bg)); color: var(--color-info-text); }
.booking-status.confirmed { background: var(--color-success-bg); color: var(--color-success-text); }
.booking-status.awaiting_payment { background: var(--color-warning-bg); color: var(--color-warning-text); }
.booking-status.pending_approval { background: var(--badge-closed-bg); color: var(--color-text-secondary); }
.booking-status.cancelled, .booking-status.rejected { background: var(--badge-closed-bg); color: var(--color-text-muted); }
.booking-status.completed { background: var(--color-success-bg); color: var(--color-success-text); }
</style>
