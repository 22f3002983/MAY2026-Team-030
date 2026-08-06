<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios' // adjust this path to wherever your axios instance actually lives




// =============================================================================
// EVERYTHING for the resident Amenities experience lives in this one file:
//   - data layer (fetch + normalize from the Flask backend)
//   - page (grids, my bookings)
//   - detail/booking modal (was AmenityDetailModal.vue + BookingModal.vue)
//   - recommendation panel (was RecommendationPanel.vue)
//
// Note: this intentionally leaves out secretary-only actions (approve/reject,
// amenity CRUD, maintenance toggles) and AmenityBookingsModal.vue, since none
// of those are used on the resident-facing page. Say the word if you want
// those merged in too.
// =============================================================================




// ---------------------------------------------------------------------------
// Data layer — normalize backend shape into what the templates expect
// ---------------------------------------------------------------------------
const amenitiesRaw = ref([])
const bookingsRaw = ref([])
const loading = ref(false)
const loadError = ref(null)




function normalizeAmenity(a) {
  return {
    id: a.id,
    name: a.name,
    category: a.type,                 // backend: `type`
    icon: a.icon,
    location: a.location,
    description: a.description,
    capacity: a.capacity,
    air_conditioned: a.is_air_conditioned,
    decoratable: a.is_decoratable,
    features: a.features || [],
    booking_type: a.booking_type,       // 'automatic' | 'approval_required' | null
    special_booking: a.special_booking,
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




// Backend only has pending/approved/rejected/cancelled + a separate
// payment_status. We derive the richer display-only status set here.
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




const myBookings = computed(() =>
  bookingsRaw.value.map(attachAmenity).sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
)
const myUpcomingBookings = computed(() =>
  myBookings.value.filter((b) => ['pending_approval', 'awaiting_payment', 'confirmed'].includes(b.status))
)
const myPastBookings = computed(() =>
  myBookings.value.filter((b) => ['completed', 'cancelled', 'rejected'].includes(b.status))
)




async function fetchAmenities() {
  loading.value = true
  try {
    const { data } = await api.get('/amenities')
    amenitiesRaw.value = data.amenities.map(normalizeAmenity)
  } catch (e) {
    loadError.value = e
  } finally {
    loading.value = false
  }
}




async function fetchBookings() {
  const { data } = await api.get('/amenities/bookings')
  bookingsRaw.value = data.bookings.map(normalizeBooking)
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
// Availability + booking actions
// ---------------------------------------------------------------------------
async function checkAvailability(amenityId, { date, endDate, startTime, endTime }) {
  const { data } = await api.get(`/amenities/${amenityId}/availability`, {
    params: { date, end_date: endDate, start_time: startTime, end_time: endTime },
  })
  return data
}




async function createBooking({ amenity, date, endDate, startTime, endTime, eventType, guests, reason }) {
  const { data } = await api.post(`/amenities/${amenity.id}/book`, {
    date,
    end_date: endDate || date,
    start_time: startTime,
    end_time: endTime,
    event_type: eventType,
    reason: reason || eventType,
    guests,
  })
  return normalizeBooking(data.booking)
}


async function cancelBookingApi(bookingId) {
  const { data } = await api.patch(`/amenities/bookings/${bookingId}/cancel`)
  const i = bookingsRaw.value.findIndex((b) => b.id === bookingId)
  if (i !== -1) bookingsRaw.value[i] = normalizeBooking(data.booking)
}




async function payForBookingApi(bookingId) {
  const { data } = await api.patch(`/amenities/bookings/${bookingId}/pay`)
  const i = bookingsRaw.value.findIndex((b) => b.id === bookingId)
  if (i !== -1) bookingsRaw.value[i] = normalizeBooking(data.booking)
}




// event types offered on the booking form itself (unrelated to the
// recommendation panel, which is now AI-driven free text instead)
const EVENT_TYPES = [
  'Birthday party', 'Wedding function', 'Family gathering', 'Movie / watch party',
  'Kids party', 'Guests staying over', 'Small meeting', 'Sports session',
]




// =============================================================================
// PAGE STATE
// =============================================================================
const successMsg = ref('')
const showBookingsHistory = ref(false)




const exclusiveAmenities = computed(() => amenities.value.filter(a => a.category === 'exclusive'))
const publicAmenities = computed(() => amenities.value.filter(a => a.category === 'public'))
const infraAmenities = computed(() => amenities.value.filter(a => a.category === 'unbookable'))




function handleCancel(booking) {
  if (confirm(`Cancel your booking for ${booking.amenity.name} on ${booking.start_date}?`)) {
    cancelBookingApi(booking.id)
  }
}




function handlePay(booking) {
  payForBookingApi(booking.id).then(() => {
    successMsg.value = `Payment received — ${booking.amenity.name} is confirmed.`
    setTimeout(() => successMsg.value = '', 4500)
  })
}




// =============================================================================
// RECOMMENDATION PANEL STATE — AI-driven ("Find the Right Place")
// Free-text query -> POST /api/amenities/recommend -> a short recommendation
// generated from the current amenity list. Result stays on screen until the
// resident submits a new query (not cleared just by editing the input).
// =============================================================================
const recOpen = ref(false)
const recQuery = ref('')
const recLoading = ref(false)
const recResult = ref('')
const recUnavailable = ref(false)


async function getRecommendation() {
  const query = recQuery.value.trim()
  if (!query || recLoading.value) return


  // clear the previous answer immediately so it doesn't sit on screen while
  // the new search is loading — only the spinner should show
  recResult.value = ''
  recUnavailable.value = false
  recLoading.value = true
  try {
    const res = await api.post('/amenities/recommend', { query })
    if (res.data.recommendation) {
      recResult.value = res.data.recommendation
    } else {
      recResult.value = ''
      recUnavailable.value = true
    }
  } catch (err) {
    console.error('Failed to get amenity recommendation', err)
    recResult.value = ''
    recUnavailable.value = true
  } finally {
    recLoading.value = false
  }
}




// =============================================================================
// MODAL STATE (was AmenityDetailModal.vue + BookingModal.vue)
// =============================================================================
const selectedAmenity = ref(null)
const showModal = ref(false)
const modalStep = ref('detail') // 'detail' | 'book'




const isHourly = computed(() => selectedAmenity.value?.pricing?.type === 'hourly')
const bookable = computed(() =>
  selectedAmenity.value ? isBookable(selectedAmenity.value) && selectedAmenity.value.status !== 'maintenance' : false
)




// detail step: availability checker
const checkDate = ref('')
const checkStart = ref('18:00')
const checkEnd = ref('20:00')
const availResult = ref(null)
const checking = ref(false)




// book step
const bookForm = ref({ date: '', startTime: '18:00', endTime: '20:00', eventType: EVENT_TYPES[0], guests: 10 })
const bookError = ref('')
const bookSubmitting = ref(false)




function openDetail(amenity) {
  selectedAmenity.value = amenity
  modalStep.value = 'detail'
  showModal.value = true
  checkDate.value = ''
  availResult.value = null
  bookError.value = ''
}




function closeModal() {
  showModal.value = false
  selectedAmenity.value = null
}




async function runCheck() {
  if (!checkDate.value || !selectedAmenity.value) return
  checking.value = true
  try {
    availResult.value = await checkAvailability(selectedAmenity.value.id, {
      date: checkDate.value,
      startTime: checkStart.value,
      endTime: checkEnd.value,
    })
  } finally {
    checking.value = false
  }
}




function goToBook() {
  if (checkDate.value) bookForm.value.date = checkDate.value
  if (isHourly.value) {
    bookForm.value.startTime = checkStart.value
    bookForm.value.endTime = checkEnd.value
  }
  modalStep.value = 'book'
}




async function submitBooking() {
  bookError.value = ''
  if (!bookForm.value.date || !bookForm.value.eventType || !bookForm.value.guests) {
    bookError.value = 'All fields are required'
    return
  }
  if (isHourly.value && bookForm.value.startTime >= bookForm.value.endTime) {
    bookError.value = 'End time must be after start time'
    return
  }
  bookSubmitting.value = true
  try {
    const amenity = selectedAmenity.value
    const booking = await createBooking({
      amenity,
      date: bookForm.value.date,
      startTime: isHourly.value ? bookForm.value.startTime : null,
      endTime: isHourly.value ? bookForm.value.endTime : null,
      eventType: bookForm.value.eventType,
      guests: bookForm.value.guests,
    })
    bookingsRaw.value.unshift({
      id: booking.id, amenity_id: amenity.id, user_id: booking.user_id, user_name: booking.user_name,
      start_date: booking.start_date, end_date: booking.end_date, start_time: booking.start_time,
      end_time: booking.end_time, price: booking.price, event_type: booking.event_type,
      guests: booking.guests, status: booking.status, rejected_reason: booking.rejected_reason,
      created_at: booking.created_at,
    })
    closeModal()
    successMsg.value = booking.status === 'pending_approval'
      ? `Request for ${amenity.name} on ${bookForm.value.date} sent for approval.`
      : `${amenity.name} booked for ${bookForm.value.date}. Confirmation sent.`
    setTimeout(() => successMsg.value = '', 4500)
  } catch (e) {
    bookError.value = e?.response?.data?.error || 'Could not create booking.'
  } finally {
    bookSubmitting.value = false
  }
}




// =============================================================================
onMounted(() => {
  fetchAmenities()
  fetchBookings()
})
</script>




<template>
  <div class="amenities">
    <div class="page-header">
      <div>
        <h2>Amenities</h2>
        <p class="page-sub">Book exclusive facilities or check shared amenity status</p>
      </div>
    </div>




    <div v-if="successMsg" class="success-banner">✓ {{ successMsg }}</div>




    <!-- ============ RECOMMENDATION PANEL (AI-driven) ============ -->
    <div class="rec-panel">
      <button class="rec-panel-toggle" @click="recOpen = !recOpen">
        <span class="rec-ai-badge">🤖 Find the right place</span>
        <span class="rec-chevron" :class="{ up: recOpen }">⌄</span>
      </button>




      <div v-if="recOpen" class="rec-panel-body">
        <p class="rec-panel-sub">Tell us what you're looking for and we'll suggest the best fit — e.g. "I want a place to swim" or "a quiet room for a meeting".</p>




        <div class="rec-query-row">
          <input
            v-model="recQuery"
            type="text"
            class="rec-input rec-query-input"
            placeholder="What are you looking for?"
            @keyup.enter="getRecommendation"
          />
          <button class="rec-get-btn" :disabled="!recQuery.trim() || recLoading" @click="getRecommendation">
            <span v-if="recLoading" class="rec-spinner"></span>
            {{ recLoading ? 'Finding...' : 'Find' }}
          </button>
        </div>




        <div v-if="recResult" class="rec-answer-card">🤖 {{ recResult }}</div>
        <div v-else-if="recUnavailable" class="rec-answer-card rec-answer-unavailable">AI recommendation unavailable</div>
      </div>
    </div>




    <!-- My bookings -->
    <div class="my-bookings" v-if="myUpcomingBookings.length || myPastBookings.length">
      <div class="section-title">My Bookings</div>
      <p class="refund-note">Note: once a booking is paid, cancelling it will not refund the payment.</p>
      <div class="booking-list">
        <div v-for="b in myUpcomingBookings" :key="b.id" class="booking-row">
          <span class="booking-icon">{{ b.amenity.icon }}</span>
          <div class="booking-info">
            <div class="booking-name">{{ b.amenity.name }}</div>
            <div class="booking-meta">
              {{ b.start_date }}{{ b.end_date !== b.start_date ? ' → ' + b.end_date : '' }}
              <template v-if="b.start_time"> · {{ b.start_time }}–{{ b.end_time }}</template>
              · {{ b.event_type }}
            </div>
          </div>
          <span :class="['booking-status', b.status]">{{ bookingStatusLabel(b.status) }}</span>
          <div class="booking-actions">
            <button v-if="b.status === 'awaiting_payment'" class="pay-btn" @click="handlePay(b)">Pay ₹{{ b.price.toLocaleString('en-IN') }}</button>
            <button class="cancel-btn" @click="handleCancel(b)">Cancel</button>
          </div>
        </div>
      </div>




      <button v-if="myPastBookings.length" class="toggle-history" @click="showBookingsHistory = !showBookingsHistory">
        {{ showBookingsHistory ? 'Hide' : 'Show' }} past bookings ({{ myPastBookings.length }})
      </button>
      <div v-if="showBookingsHistory" class="booking-list past">
        <div v-for="b in myPastBookings" :key="b.id" class="booking-row muted">
          <span class="booking-icon">{{ b.amenity.icon }}</span>
          <div class="booking-info">
            <div class="booking-name">{{ b.amenity.name }}</div>
            <div class="booking-meta">{{ b.start_date }} · {{ b.event_type }}</div>
          </div>
          <span :class="['booking-status', b.status]">{{ bookingStatusLabel(b.status) }}</span>
        </div>
      </div>
    </div>




    <!-- exclusive -->
    <div class="section-title" style="margin-top: 32px">Exclusive Booking</div>
    <p class="section-sub">These facilities can be reserved for your exclusive use</p>




    <div class="amenity-grid">
      <div v-for="amenity in exclusiveAmenities" :key="amenity.id" class="amenity-card" @click="openDetail(amenity)">
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
            <span class="exclusive-tag">{{ amenity.booking_type === 'automatic' ? 'Auto-approve' : 'Needs approval' }}</span>
            <button v-if="isBookable(amenity) && amenity.status === 'available'" class="book-btn" @click.stop="openDetail(amenity); goToBook()">Book</button>
            <span v-else class="unavailable-label">Unavailable</span>
          </div>
        </div>
      </div>
    </div>




    <!-- public -->
    <div class="section-title" style="margin-top: 32px">Shared Facilities</div>
    <p class="section-sub">No booking needed — open to all residents</p>




    <div class="amenity-grid">
      <div v-for="amenity in publicAmenities" :key="amenity.id" class="amenity-card" @click="openDetail(amenity)">
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
            <span class="public-tag">{{ amenity.special_booking ? 'Bookable for private events' : 'No booking needed' }}</span>
          </div>
        </div>
      </div>
    </div>




    <!-- infrastructure -->
    <div class="section-title" style="margin-top: 32px">Infrastructure</div>
    <p class="section-sub">Common infrastructure — for information only, not bookable</p>




    <div class="amenity-grid">
      <div v-for="amenity in infraAmenities" :key="amenity.id" class="amenity-card" @click="openDetail(amenity)">
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
        </div>
      </div>
    </div>




    <!-- ============ DETAIL / BOOK MODAL ============ -->
    <div v-if="showModal && selectedAmenity" class="modal-overlay" @click.self="closeModal">
      <div class="modal-sheet">
        <button class="modal-close-btn" @click="closeModal">✕</button>




        <div class="modal-hero" :class="{ infra: selectedAmenity.category === 'unbookable' }">
          <span class="modal-hero-icon">{{ selectedAmenity.icon }}</span>
          <span :class="['modal-status-tag', selectedAmenity.status]">
            <span class="modal-status-dot"></span>{{ statusLabel(selectedAmenity.status) }}
            <template v-if="selectedAmenity.status_until"> · till {{ selectedAmenity.status_until }}</template>
          </span>
        </div>




        <div class="modal-content">
          <!-- DETAIL STEP -->
          <template v-if="modalStep === 'detail'">
            <h3>{{ selectedAmenity.name }}</h3>
            <p class="modal-location">📍 {{ selectedAmenity.location }}</p>
            <p class="modal-desc">{{ selectedAmenity.description }}</p>




            <div class="modal-spec-grid">
              <div class="modal-spec" v-if="selectedAmenity.capacity"><span class="modal-spec-label">Capacity</span><span class="modal-spec-value">Up to {{ selectedAmenity.capacity }}</span></div>
              <div class="modal-spec" v-if="selectedAmenity.air_conditioned !== undefined"><span class="modal-spec-label">Air conditioned</span><span class="modal-spec-value">{{ selectedAmenity.air_conditioned ? 'Yes' : 'No' }}</span></div>
              <div class="modal-spec" v-if="selectedAmenity.decoratable !== undefined"><span class="modal-spec-label">Decoration allowed</span><span class="modal-spec-value">{{ selectedAmenity.decoratable ? 'Yes' : 'No' }}</span></div>
              <div class="modal-spec" v-if="selectedAmenity.pricing?.type"><span class="modal-spec-label">Pricing</span><span class="modal-spec-value">₹{{ selectedAmenity.pricing.rate }} / {{ selectedAmenity.pricing.unitLabel }}</span></div>
              <div class="modal-spec" v-if="selectedAmenity.booking_type"><span class="modal-spec-label">Approval</span><span class="modal-spec-value">{{ selectedAmenity.booking_type === 'automatic' ? 'Instant' : 'Secretary approval' }}</span></div>
            </div>




            <div v-if="selectedAmenity.features?.length" class="modal-features">
              <span v-for="f in selectedAmenity.features" :key="f" class="modal-feature-chip">{{ f }}</span>
            </div>




            <div v-if="selectedAmenity.special_booking" class="modal-special-note">
              Normally a shared facility — can be booked exclusively for private events with secretary approval.
            </div>




            <div v-if="bookable" class="modal-availability-box">
              <div class="modal-avail-title">Check availability</div>
              <div class="modal-avail-row">
                <input type="date" v-model="checkDate" class="modal-avail-input" />
                <template v-if="isHourly">
                  <input type="time" v-model="checkStart" class="modal-avail-input small" />
                  <span class="modal-to">to</span>
                  <input type="time" v-model="checkEnd" class="modal-avail-input small" />
                </template>
                <button class="modal-check-btn" @click="runCheck" :disabled="checking">{{ checking ? 'Checking…' : 'Check' }}</button>
              </div>
              <div v-if="availResult" :class="['modal-avail-result', availResult.available ? 'free' : 'busy']">
                {{ availResult.available ? '✓ ' + availResult.message : '✕ ' + availResult.message }}
              </div>
            </div>




            <div class="modal-actions">
              <button v-if="bookable" class="modal-book-btn" @click="goToBook">
                {{ selectedAmenity.booking_type === 'approval_required' ? 'Request booking' : 'Book now' }}
              </button>
              <span v-else-if="selectedAmenity.category === 'unbookable'" class="modal-info-note">Infrastructure — no booking needed.</span>
              <span v-else-if="!isBookable(selectedAmenity)" class="modal-info-note">Open to all residents — no booking needed.</span>
              <span v-else class="modal-info-note">Unavailable while under maintenance.</span>
            </div>
          </template>




          <!-- BOOK STEP -->
          <template v-else>
            <button class="modal-back-link" @click="modalStep = 'detail'">← Back to details</button>
            <h3>Book {{ selectedAmenity.name }}</h3>
            <span class="modal-sub">{{ selectedAmenity.booking_type === 'automatic' ? 'Auto-approved' : 'Requires secretary approval' }}</span>




            <label class="modal-form-label">Date</label>
            <input v-model="bookForm.date" type="date" class="modal-n-input" />




            <div class="modal-time-row" v-if="isHourly">
              <div class="modal-time-field">
                <label class="modal-form-label">Start Time</label>
                <input v-model="bookForm.startTime" type="time" class="modal-n-input" />
              </div>
              <div class="modal-time-field">
                <label class="modal-form-label">End Time</label>
                <input v-model="bookForm.endTime" type="time" class="modal-n-input" />
              </div>
            </div>




            <label class="modal-form-label">Event type</label>
            <select v-model="bookForm.eventType" class="modal-n-input">
              <option v-for="t in EVENT_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>




            <label class="modal-form-label">Guests</label>
            <input v-model.number="bookForm.guests" type="number" min="1" class="modal-n-input" />




            <p v-if="bookError" class="modal-error-msg">{{ bookError }}</p>




            <div class="modal-actions">
              <button class="modal-book-btn" @click="submitBooking" :disabled="bookSubmitting">
                {{ bookSubmitting ? 'Submitting…' : 'Confirm Booking' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>




<style scoped>
.amenities { max-width: var(--content-max-width); }




.success-banner {
  background: var(--color-success-bg); color: var(--color-success-text);
  border: 1px solid var(--color-success); border-radius: var(--radius-md);
  padding: 12px 16px; font-size: var(--font-size-md); font-weight: 600; margin-bottom: 20px;
}




.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }




.section-title { font-size: var(--font-size-xl); font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; }
.refund-note { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-bottom: 12px; }




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
.rec-panel-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 14px; }




.rec-input {
  border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px 10px;
  font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary);
}


.rec-query-row { display: flex; gap: 10px; margin-bottom: 14px; }
.rec-query-input { flex: 1; font-family: var(--font-family); }


.rec-get-btn {
  display: flex; align-items: center; justify-content: center; gap: 7px;
  height: 38px; padding: 0 18px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-weight: 700; font-size: var(--font-size-sm); white-space: nowrap; flex-shrink: 0;
}
.rec-get-btn:hover:not(:disabled) { background: var(--c-800); }
.rec-get-btn:disabled { opacity: 0.5; cursor: not-allowed; }


.rec-spinner {
  width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff;
  border-radius: 50%; animation: rec-spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes rec-spin { to { transform: rotate(360deg); } }


.rec-answer-card {
  padding: 14px 16px; border-radius: var(--radius-md); background: var(--badge-closed-bg);
  color: var(--color-text-primary); font-size: var(--font-size-sm); line-height: 1.55;
}
.rec-answer-unavailable { color: var(--color-text-muted); font-style: italic; }




/* ---------- My bookings ---------- */
.my-bookings {
  background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-xl);
  padding: 18px; margin-bottom: 8px; box-shadow: var(--shadow-sm);
}
.booking-list { display: flex; flex-direction: column; gap: 10px; }
.booking-row {
  display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: var(--radius-md); background: var(--badge-closed-bg);
}
.booking-row.muted { opacity: 0.75; }
.booking-icon { font-size: 24px; }
.booking-info { flex: 1; min-width: 0; }
.booking-name { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.booking-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.booking-status {
  font-size: var(--font-size-xs); font-weight: 700; padding: 4px 10px; border-radius: var(--radius-pill);
  background: var(--color-info-bg, var(--badge-closed-bg)); color: var(--color-info-text); white-space: nowrap;
}
.booking-status.confirmed { background: var(--color-success-bg); color: var(--color-success-text); }
.booking-status.awaiting_payment { background: var(--color-warning-bg); color: var(--color-warning-text); }
.booking-status.pending_approval { background: var(--badge-closed-bg); color: var(--color-text-secondary); }
.booking-status.cancelled, .booking-status.rejected { background: var(--badge-closed-bg); color: var(--color-text-muted); }
.booking-status.completed { background: var(--color-success-bg); color: var(--color-success-text); }
.booking-actions { display: flex; gap: 6px; }
.pay-btn { padding: 6px 12px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }
.cancel-btn { padding: 6px 12px; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }
.toggle-history { margin-top: 12px; font-size: var(--font-size-xs); color: var(--c-900); font-weight: 700; }




/* ---------- Grid & cards ---------- */
.amenity-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 8px; }
.amenity-card { background: var(--color-surface); border-radius: var(--radius-xl); border: 1px solid var(--color-border); overflow: hidden; box-shadow: var(--shadow-sm); transition: box-shadow var(--transition-fast); cursor: pointer; }
.amenity-card:hover { box-shadow: var(--shadow-md); }




.card-header-area { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); height: 110px; display: flex; align-items: center; justify-content: center; position: relative; padding: 16px; }
.card-header-area.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.card-icon { font-size: 36px; filter: grayscale(1) brightness(5); }




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




.card-body-area { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.amenity-name { display: block; font-size: var(--font-size-lg); font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.amenity-desc { font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.5; }
.card-body-bottom { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; flex-wrap: wrap; gap: 6px; }




.exclusive-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--color-warning-bg); color: var(--color-warning-text); font-size: var(--font-size-xs); font-weight: 700; }
.public-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--color-success-bg); color: var(--color-success-text); font-size: var(--font-size-xs); font-weight: 700; }
.info-tag { padding: 4px 12px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--badge-closed-text); font-size: var(--font-size-xs); font-weight: 700; }




.book-btn { height: 36px; padding: 0 20px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-sm); font-weight: 700; transition: background var(--transition-fast); }
.book-btn:hover { background: var(--c-800); }
.unavailable-label { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: 600; }




/* ---------- Modal ---------- */
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.5); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-sheet { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto; position: relative; box-shadow: var(--shadow-md); }
.modal-close-btn { position: absolute; top: 12px; right: 12px; z-index: 2; width: 32px; height: 32px; border-radius: 50%; background: rgba(255,255,255,0.9); color: var(--color-text-primary); font-size: 14px; display: flex; align-items: center; justify-content: center; }
.modal-hero { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); height: 130px; display: flex; align-items: center; justify-content: center; position: relative; }
.modal-hero.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.modal-hero-icon { font-size: 44px; filter: grayscale(1) brightness(5); }
.modal-status-tag { position: absolute; bottom: 12px; left: 16px; display: flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; background: rgba(255,255,255,0.92); color: var(--color-text-primary); }
.modal-status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); flex-shrink: 0; }
.modal-status-tag.booked .modal-status-dot { background: var(--c-600); }
.modal-status-tag.maintenance .modal-status-dot { background: var(--color-warning); }




.modal-content { padding: 20px; }
.modal-content h3 { font-size: var(--font-size-xl); font-weight: 800; color: var(--color-text-primary); }
.modal-sub { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.modal-location { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }
.modal-desc { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin-top: 10px; line-height: 1.5; }




.modal-back-link { font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800); margin-bottom: 10px; }




.modal-spec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; margin-top: 16px; }
.modal-spec { display: flex; flex-direction: column; gap: 2px; }
.modal-spec-label { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.modal-spec-value { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-primary); }




.modal-features { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; }
.modal-feature-chip { font-size: var(--font-size-xs); padding: 4px 10px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); }




.modal-special-note { margin-top: 14px; font-size: var(--font-size-xs); color: var(--color-warning-text); background: var(--color-warning-bg); padding: 8px 12px; border-radius: var(--radius-md); }




.modal-availability-box { margin-top: 18px; padding: 14px; border-radius: var(--radius-md); background: var(--badge-closed-bg); }
.modal-avail-title { font-size: var(--font-size-sm); font-weight: 700; margin-bottom: 8px; color: var(--color-text-primary); }
.modal-avail-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.modal-avail-input { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 6px 8px; font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary); }
.modal-avail-input.small { width: 100px; }
.modal-to { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.modal-check-btn { padding: 6px 14px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-sm); font-weight: 700; }
.modal-avail-result { margin-top: 10px; font-size: var(--font-size-sm); font-weight: 600; }
.modal-avail-result.free { color: var(--color-success-text); }
.modal-avail-result.busy { color: var(--color-warning-text); }




.modal-form-label { display: block; font-size: var(--font-size-sm); font-weight: 600; color: var(--c-800); margin-top: 10px; margin-bottom: 4px; }
.modal-n-input { width: 100%; height: 42px; padding: 0 13px; border: 1.5px solid var(--color-border-soft); border-radius: var(--radius-md); font-size: var(--font-size-md); background: var(--color-surface-soft); color: var(--color-text-primary); outline: none; font-family: var(--font-family); }
.modal-n-input:focus { border-color: var(--c-600); }
.modal-time-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-time-field { display: flex; flex-direction: column; }
.modal-error-msg { font-size: var(--font-size-sm); color: var(--color-danger); margin-top: 6px; }




.modal-actions { margin-top: 20px; }
.modal-book-btn { width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-md); font-weight: 700; }
.modal-book-btn:hover { background: var(--c-800); }
.modal-book-btn:disabled { opacity: 0.6; }
.modal-info-note { font-size: var(--font-size-sm); color: var(--color-text-muted); }
</style>



