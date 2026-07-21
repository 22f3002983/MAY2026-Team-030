<script setup>
import { ref, computed } from 'vue'
import AmenityDetailModal from '../../components/AmenityDetailModal.vue'
import BookingModal from '../../components/BookingModal.vue'
import RecommendationPanel from '../../components/RecommendationPanel.vue'
import {
  amenities, myUpcomingBookings, myPastBookings,
  isBookable, statusLabel, bookingStatusLabel,
  cancelBooking, payForBooking,
} from '../../composables/useAmenities'

const selectedAmenity = ref(null)
const showDetail = ref(false)
const showBooking = ref(false)
const successMsg = ref('')
const showBookingsHistory = ref(false)

const exclusiveAmenities = computed(() => amenities.value.filter(a => a.category === 'exclusive'))
const publicAmenities = computed(() => amenities.value.filter(a => a.category === 'public'))
const infraAmenities = computed(() => amenities.value.filter(a => a.category === 'unbookable'))

const nonSharedAmenities = computed(() => [...exclusiveAmenities.value, ...infraAmenities.value])

const groupedByLocation = computed(() => {
  const groups = {}
  for (const a of nonSharedAmenities.value) {
    groups[a.location] ??= []
    groups[a.location].push(a)
  }
  return groups
})

function openDetail(amenity) {
  selectedAmenity.value = amenity
  showDetail.value = true
}

function goToBooking(amenity) {
  selectedAmenity.value = amenity
  showDetail.value = false
  showBooking.value = true
}

function handleConfirm({ amenity_name, date, booking }) {
  showBooking.value = false
  selectedAmenity.value = null
  successMsg.value = booking.status === 'pending_approval'
    ? `Request for ${amenity_name} on ${date} sent for approval.`
    : `${amenity_name} booked for ${date}. Confirmation sent.`
  setTimeout(() => successMsg.value = '', 4500)
}

function handleCancel(booking) {
  if (confirm(`Cancel your booking for ${booking.amenity.name} on ${booking.start_date}?`)) {
    cancelBooking(booking.id)
  }
}

function handlePay(booking) {
  payForBooking(booking.id)
  successMsg.value = `Payment received — ${booking.amenity.name} is confirmed.`
  setTimeout(() => successMsg.value = '', 4500)
}
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

    <RecommendationPanel @select="openDetail" />

    <!-- My bookings -->
    <div class="my-bookings" v-if="myUpcomingBookings.length || myPastBookings.length">
      <div class="section-title">My Bookings</div>
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
            <button v-if="isBookable(amenity) && amenity.status === 'available'" class="book-btn" @click.stop="goToBooking(amenity)">Book</button>
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

    <AmenityDetailModal v-if="showDetail" :amenity="selectedAmenity" @close="showDetail = false" @book="goToBooking" />
    <BookingModal v-if="showBooking" :amenity="selectedAmenity" @close="showBooking = false" @confirm="handleConfirm" />
  </div>
</template>

<style scoped>
.amenities { max-width: var(--content-max-width); }

.success-banner {
  background: var(--color-success-bg); color: var(--color-success-text);
  border: 1px solid var(--color-success); border-radius: var(--radius-md);
  padding: 12px 16px; font-size: var(--font-size-md); font-weight: 600; margin-bottom: 20px;
}

.section-title { font-size: var(--font-size-xl); font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; }
.section-header-row { display: flex; align-items: flex-start; justify-content: space-between; }

.switch-label { display: flex; align-items: center; gap: 8px; font-size: var(--font-size-xs); color: var(--color-text-secondary); font-weight: 600; }
.switch { width: 40px; height: 22px; border-radius: var(--radius-pill); background: var(--color-border); position: relative; transition: background var(--transition-fast); }
.switch.on { background: var(--c-900); }
.switch-knob { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; transition: transform var(--transition-fast); }
.switch.on .switch-knob { transform: translateX(18px); }

/* My bookings */
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

/* Grid & cards (base, from original) */
.amenity-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 8px; }
.amenity-card { background: var(--color-surface); border-radius: var(--radius-xl); border: 1px solid var(--color-border); overflow: hidden; box-shadow: var(--shadow-sm); transition: box-shadow var(--transition-fast); cursor: pointer; }
.amenity-card:hover { box-shadow: var(--shadow-md); }

.card-header-area { background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%); height: 110px; display: flex; align-items: center; justify-content: center; position: relative; padding: 16px; }
.card-header-area.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.card-icon { font-size: 36px; filter: grayscale(1) brightness(5); }

.status-tag { position: absolute; top: 12px; right: 12px; display: flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); font-weight: 700; background: rgba(255,255,255,0.92); }
.status-tag.inline { position: static; background: var(--badge-closed-bg); margin-top: 4px; display: inline-flex; }
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

/* location groups */
.location-group { margin-bottom: 22px; }
.location-title { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-secondary); margin-bottom: 10px; }
.amenity-card.compact { display: flex; align-items: center; gap: 12px; padding: 12px; cursor: pointer; }
.card-icon-inline { font-size: 26px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }
</style>