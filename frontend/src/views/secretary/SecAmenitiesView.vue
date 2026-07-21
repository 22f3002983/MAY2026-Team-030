<script setup>
import { ref, computed, watch } from 'vue'
import {
  amenities, pendingApprovals, statusLabel, bookingStatusLabel,
  addAmenity, updateAmenity, deleteAmenity,
  setMaintenance, clearMaintenance, approveBooking, rejectBooking,
  allBookingsForAmenity, cancelBooking,
} from '../../composables/useAmenities'

// ---------------------------------------------------------------------------
// Page state
// ---------------------------------------------------------------------------
const toast = ref('')
const approvalsOpen = ref(true)
function flash(msg) { toast.value = msg; setTimeout(() => toast.value = '', 3500) }

const bookableCount = computed(() => amenities.value.filter(a => a.booking_type).length)

// Grouped for the section layout below — one filter each, built off the same
// `amenities` list so a change in the Edit form is reflected everywhere.
const amenityGroups = computed(() => [
  { key: 'exclusive',  label: 'Exclusive',        sub: 'Bookable by individual residents for private use',      items: amenities.value.filter(a => a.category === 'exclusive') },
  { key: 'public',     label: 'Shared / Public',   sub: 'Common-use spaces open to all residents',                items: amenities.value.filter(a => a.category === 'public') },
  { key: 'unbookable', label: 'Infrastructure',    sub: 'Not resident-bookable — building utilities & systems',  items: amenities.value.filter(a => a.category === 'unbookable') },
])

// ---------------------------------------------------------------------------
// Add / Edit form
// ---------------------------------------------------------------------------
const showForm = ref(false)
const editingAmenity = ref(null)
const form = ref(blankForm())

function blankForm() {
  return {
    name: '', icon: '⭐', category: 'exclusive', location: '', tower: '', floor: '', description: '',
    capacity: '', air_conditioned: false, decoratable: false, featuresText: '',
    bookable: false, booking_type: 'automatic',
    pricingType: '', rate: '', minUnits: 1, unitLabel: 'hour',
    status: 'available', status_until: '',
  }
}

watch(editingAmenity, (a) => {
  if (!a) { form.value = blankForm(); return }
  form.value = {
    name: a.name, icon: a.icon, category: a.category, location: a.location,
    tower: a.tower || '', floor: a.floor || '', description: a.description,
    capacity: a.capacity ?? '', air_conditioned: !!a.air_conditioned, decoratable: !!a.decoratable,
    featuresText: (a.features || []).join(', '),
    bookable: !!a.booking_type, booking_type: a.booking_type || 'automatic',
    pricingType: a.pricing?.type || '', rate: a.pricing?.rate ?? '', minUnits: a.pricing?.minUnits ?? 1,
    unitLabel: a.pricing?.unitLabel || (a.pricing?.type === 'daily' ? 'day' : 'hour'),
    status: a.status, status_until: a.status_until || '',
  }
})

const showPricing = computed(() => form.value.bookable)
const showUntil = computed(() => form.value.status === 'maintenance' || form.value.status === 'booked')

function openAdd() { editingAmenity.value = null; showForm.value = true }
function openEdit(amenity) { editingAmenity.value = amenity; showForm.value = true }
function closeForm() { showForm.value = false }

function submitForm() {
  if (!form.value.name.trim()) return
  const payload = {
    name: form.value.name.trim(),
    icon: form.value.icon || '⭐',
    category: form.value.category,
    location: form.value.location.trim(),
    tower: form.value.tower.trim(),
    floor: form.value.floor.trim(),
    description: form.value.description.trim(),
    capacity: form.value.capacity === '' ? null : Number(form.value.capacity),
    air_conditioned: form.value.air_conditioned,
    decoratable: form.value.decoratable,
    features: form.value.featuresText.split(',').map(f => f.trim()).filter(Boolean),
    booking_type: form.value.bookable ? form.value.booking_type : null,
    pricing: form.value.bookable && form.value.pricingType
      ? {
          type: form.value.pricingType,
          rate: Number(form.value.rate) || 0,
          minUnits: Number(form.value.minUnits) || 1,
          unitLabel: form.value.unitLabel || (form.value.pricingType === 'daily' ? 'day' : 'hour'),
        }
      : { type: null },
    status: form.value.status,
    status_until: showUntil.value ? (form.value.status_until || null) : null,
  }
  if (editingAmenity.value) {
    updateAmenity(editingAmenity.value.id, payload)
    flash(`${payload.name} updated.`)
  } else {
    addAmenity(payload)
    flash(`${payload.name} added.`)
  }
  showForm.value = false
}

function handleDelete(amenity) {
  if (!confirm(`Delete ${amenity.name}? This can't be undone.`)) return
  const res = deleteAmenity(amenity.id)
  flash(res.ok ? `${amenity.name} deleted.` : res.reason)
}

function toggleMaintenance(amenity) {
  if (amenity.status === 'maintenance') {
    clearMaintenance(amenity.id)
    flash(`${amenity.name} marked available.`)
  } else {
    setMaintenance(amenity.id, null)
    flash(`${amenity.name} blocked for maintenance.`)
  }
}

// ---------------------------------------------------------------------------
// Approvals
// ---------------------------------------------------------------------------
function handleApprove(b) { approveBooking(b.id); flash(`Approved ${b.amenity.name} for ${b.user_name}.`) }

// ---------------------------------------------------------------------------
// Reject flow — shared by the approvals panel and the per-amenity bookings
// panel. Both just call openReject(b); the modal handles the rest.
// ---------------------------------------------------------------------------
const showRejectModal = ref(false)
const rejectTarget = ref(null)
const rejectReason = ref('')

const rejectAmenityName = computed(() => rejectTarget.value?.amenity?.name || bookingsAmenity.value?.name || '')

function openReject(b) {
  rejectTarget.value = b
  rejectReason.value = ''
  showRejectModal.value = true
}
function closeReject() {
  showRejectModal.value = false
  rejectTarget.value = null
}
function confirmReject() {
  if (!rejectTarget.value) return
  rejectBooking(rejectTarget.value.id, rejectReason.value.trim())
  const who = rejectTarget.value.user_name
  const name = rejectAmenityName.value
  flash(`Rejected ${name ? name + ' request from ' : 'request from '}${who}.`)
  closeReject()
}

// ---------------------------------------------------------------------------
// Per-amenity bookings panel
// ---------------------------------------------------------------------------
const showBookings = ref(false)
const bookingsAmenity = ref(null)
const timeframe = ref('all')
const statusFilter = ref('all')

const bookingsList = computed(() => bookingsAmenity.value ? allBookingsForAmenity(bookingsAmenity.value.id) : [])
const filteredBookings = computed(() =>
  bookingsList.value.filter(b =>
    (timeframe.value === 'all' || b.timeframe === timeframe.value) &&
    (statusFilter.value === 'all' || b.status === statusFilter.value)
  )
)
const timeframeCounts = computed(() => ({
  all: bookingsList.value.length,
  ongoing: bookingsList.value.filter(b => b.timeframe === 'ongoing').length,
  upcoming: bookingsList.value.filter(b => b.timeframe === 'upcoming').length,
  past: bookingsList.value.filter(b => b.timeframe === 'past').length,
}))

function openBookings(amenity) {
  bookingsAmenity.value = amenity
  timeframe.value = 'all'
  statusFilter.value = 'all'
  showBookings.value = true
}
function closeBookings() { showBookings.value = false }
function approveRow(b) { approveBooking(b.id) }
function cancelRow(b) {
  if (confirm(`Cancel ${b.user_name}'s booking on ${b.start_date}?`)) cancelBooking(b.id)
}
</script>

<template>
  <div class="secretary-amenities">
    <div class="page-header">
      <div>
        <h2>Manage Amenities</h2>
        <p class="page-sub">Add, edit, price, and control bookability for all facilities</p>
      </div>
      <button class="add-btn" @click="openAdd">+ Add amenity</button>
    </div>

    <div v-if="toast" class="toast">✓ {{ toast }}</div>

    <div class="stats-row">
      <div class="stat"><span class="stat-num">{{ amenities.length }}</span><span class="stat-label">Total amenities</span></div>
      <div class="stat"><span class="stat-num">{{ bookableCount }}</span><span class="stat-label">Bookable</span></div>
      <div class="stat"><span class="stat-num">{{ pendingApprovals.length }}</span><span class="stat-label">Pending approvals</span></div>
    </div>

    <!-- approvals -->
    <div class="approvals-panel">
      <button class="approvals-toggle" @click="approvalsOpen = !approvalsOpen">
        <span>Pending Approvals ({{ pendingApprovals.length }})</span>
        <span class="chevron" :class="{ up: approvalsOpen }">⌄</span>
      </button>
      <div v-if="approvalsOpen" class="approvals-list">
        <div v-if="!pendingApprovals.length" class="empty">Nothing waiting on you right now.</div>
        <div v-for="b in pendingApprovals" :key="b.id" class="approval-row">
          <span class="approval-icon">{{ b.amenity.icon }}</span>
          <div class="approval-info">
            <div class="approval-name">{{ b.amenity.name }} — {{ b.user_name }}</div>
            <div class="approval-meta">
              {{ b.start_date }}{{ b.end_date !== b.start_date ? ' → ' + b.end_date : '' }}
              <template v-if="b.start_time"> · {{ b.start_time }}–{{ b.end_time }}</template>
              · {{ b.event_type }} · {{ b.guests }} guests · ₹{{ b.price.toLocaleString('en-IN') }}
            </div>
          </div>
          <div class="approval-actions">
            <button class="approve-btn" @click="handleApprove(b)">Approve</button>
            <button class="reject-btn" @click="openReject(b)">Reject</button>
          </div>
        </div>
      </div>
    </div>

    <!-- amenity sections: exclusive / shared-public / infrastructure -->
    <template v-for="group in amenityGroups" :key="group.key">
      <div class="section-title" style="margin-top: 28px">
        {{ group.label }} <span class="group-count">({{ group.items.length }})</span>
      </div>
      <p class="section-sub">{{ group.sub }}</p>

      <div class="amenity-grid">
        <div v-if="!group.items.length" class="empty-group">No {{ group.label.toLowerCase() }} amenities yet.</div>

        <div v-for="amenity in group.items" :key="amenity.id" class="amenity-card">
          <button
            class="maint-btn"
            :class="{ active: amenity.status === 'maintenance' }"
            :title="amenity.status === 'maintenance' ? 'Clear maintenance' : 'Mark maintenance'"
            @click.stop="toggleMaintenance(amenity)"
          >🔧</button>

          <div class="card-top" @click="openBookings(amenity)">
            <span class="card-icon">{{ amenity.icon }}</span>
            <div class="card-top-info">
              <div class="amenity-name">{{ amenity.name }}</div>
              <div class="amenity-location">📍 {{ [amenity.tower, amenity.floor, amenity.location].filter(Boolean).join(' · ') || '—' }}</div>
            </div>
          </div>

          <div class="card-status-row">
            <span :class="['status-tag', amenity.status]">
              {{ amenity.status === 'maintenance' ? 'Blocked for maintenance' : statusLabel(amenity.status) }}
            </span>
            <span v-if="amenity.booking_type" class="pricing-tag">
              {{ amenity.pricing?.type ? `₹${amenity.pricing.rate}/${amenity.pricing.unitLabel}` : 'Free' }}
            </span>
            <span v-else class="pricing-tag muted">Not bookable</span>
          </div>

          <div class="card-actions">
            <button class="edit-btn" @click.stop="openEdit(amenity)">Edit</button>
            <button class="delete-btn" @click.stop="handleDelete(amenity)">Delete</button>
          </div>
        </div>
      </div>
    </template>

    <!-- ============================= ADD/EDIT FORM ============================= -->
    <Teleport to="body">
      <div v-if="showForm" class="overlay" @click.self="closeForm">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ editingAmenity ? 'Edit amenity' : 'Add amenity' }}</h3>
            <button class="close-btn" @click="closeForm">✕</button>
          </div>

          <div class="modal-body">
            <div class="field-row">
              <div class="field grow">
                <label>Name</label>
                <input v-model="form.name" class="input" placeholder="e.g. Rooftop Lounge" />
              </div>
              <div class="field icon-field">
                <label>Icon</label>
                <input v-model="form.icon" class="input" maxlength="2" />
              </div>
            </div>

            <div class="field">
              <label>Category</label>
              <select v-model="form.category" class="input">
                <option value="exclusive">Exclusive</option>
                <option value="public">Shared / Public</option>
                <option value="unbookable">Infrastructure</option>
              </select>
              <span class="hint">Determines which section this amenity is grouped under below.</span>
            </div>

            <div class="field">
              <label>Location</label>
              <input v-model="form.location" class="input" placeholder="e.g. Rooftop, near Block A" />
            </div>

            <div class="field-row">
              <div class="field">
                <label>Tower</label>
                <input v-model="form.tower" class="input" placeholder="e.g. Tower A" />
              </div>
              <div class="field">
                <label>Floor</label>
                <input v-model="form.floor" class="input" placeholder="e.g. Ground, 3rd, Basement 1" />
              </div>
            </div>

            <div class="field">
              <label>Description</label>
              <textarea v-model="form.description" class="input" rows="2"></textarea>
            </div>

            <div class="field-row">
              <div class="field">
                <label>Capacity</label>
                <input type="number" min="0" v-model="form.capacity" class="input" />
              </div>
              <div class="field checks">
                <label class="check"><input type="checkbox" v-model="form.air_conditioned" /> Air conditioned</label>
                <label class="check"><input type="checkbox" v-model="form.decoratable" /> Decoration allowed</label>
              </div>
            </div>

            <div class="field">
              <label>Features (comma separated)</label>
              <input v-model="form.featuresText" class="input" placeholder="Sound system, Tables & chairs" />
            </div>

            <div class="divider"></div>

            <div class="field">
              <label class="check"><input type="checkbox" v-model="form.bookable" /> Bookable by residents</label>
              <span class="hint">Works for any category — flip this regardless of exclusive/shared/infra.</span>
            </div>

            <div class="field" v-if="form.bookable">
              <label>Approval</label>
              <select v-model="form.booking_type" class="input">
                <option value="automatic">Auto-approve</option>
                <option value="approval_required">Needs secretary approval</option>
              </select>
            </div>

            <template v-if="showPricing">
              <div class="field">
                <label>Pricing</label>
                <select v-model="form.pricingType" class="input">
                  <option value="">Free / no charge</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Per day</option>
                </select>
              </div>
              <div class="field-row" v-if="form.pricingType">
                <div class="field">
                  <label>Rate (₹)</label>
                  <input type="number" min="0" v-model="form.rate" class="input" />
                </div>
                <div class="field">
                  <label>Min. units</label>
                  <input type="number" min="1" v-model="form.minUnits" class="input" />
                </div>
              </div>
            </template>

            <div class="divider"></div>

            <div class="field">
              <label>Status</label>
              <select v-model="form.status" class="input">
                <option value="available">Available</option>
                <option value="maintenance">Under maintenance</option>
                <option value="booked">Booked</option>
              </select>
            </div>
            <div class="field" v-if="showUntil">
              <label>Until</label>
              <input type="date" v-model="form.status_until" class="input" />
            </div>

            <button class="save-btn" @click="submitForm">{{ editingAmenity ? 'Save changes' : 'Add amenity' }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ============================= BOOKINGS PANEL ============================= -->
    <Teleport to="body">
      <div v-if="showBookings" class="overlay" @click.self="closeBookings">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ bookingsAmenity.icon }} {{ bookingsAmenity.name }} — bookings</h3>
            <button class="close-btn" @click="closeBookings">✕</button>
          </div>

          <div class="modal-body">
            <div class="filter-row">
              <button v-for="tf in ['all','ongoing','upcoming','past']" :key="tf"
                :class="['chip', { active: timeframe === tf }]" @click="timeframe = tf">
                {{ tf.charAt(0).toUpperCase() + tf.slice(1) }} ({{ timeframeCounts[tf] }})
              </button>
            </div>

            <select v-model="statusFilter" class="input status-select">
              <option value="all">All statuses</option>
              <option value="pending_approval">Pending approval</option>
              <option value="awaiting_payment">Approved · payment due</option>
              <option value="confirmed">Confirmed</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
              <option value="rejected">Rejected</option>
            </select>

            <div class="list">
              <div v-if="!filteredBookings.length" class="booking-empty">No bookings match these filters.</div>
              <div v-for="b in filteredBookings" :key="b.id" class="row">
                <div class="row-top">
                  <div>
                    <div class="resident">{{ b.user_name }}</div>
                    <div class="meta">
                      {{ b.start_date }}{{ b.end_date !== b.start_date ? ' → ' + b.end_date : '' }}
                      <template v-if="b.start_time"> · {{ b.start_time }}–{{ b.end_time }}</template>
                    </div>
                    <div class="meta">{{ b.event_type }} · {{ b.guests }} guests · ₹{{ b.price.toLocaleString('en-IN') }}</div>
                  </div>
                  <span :class="['status-pill', b.status]">{{ bookingStatusLabel(b.status) }}</span>
                </div>
                <div class="row-actions" v-if="b.status === 'pending_approval'">
                  <button class="approve-btn" @click="approveRow(b)">Approve</button>
                  <button class="reject-btn" @click="openReject(b)">Reject</button>
                </div>
                <div class="row-actions" v-else-if="['awaiting_payment','confirmed'].includes(b.status)">
                  <button class="reject-btn" @click="cancelRow(b)">Cancel booking</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ============================= REJECT MODAL ============================= -->
    <Teleport to="body">
      <div v-if="showRejectModal" class="overlay" @click.self="closeReject">
        <div class="modal reject-modal">
          <div class="modal-header">
            <h3>Reject booking</h3>
            <button class="close-btn" @click="closeReject">✕</button>
          </div>
          <div class="modal-body">
            <p class="reject-summary">
              {{ rejectTarget?.user_name }}<template v-if="rejectAmenityName"> · {{ rejectAmenityName }}</template> · {{ rejectTarget?.start_date }}
            </p>
            <div class="field">
              <label>Reason (optional)</label>
              <textarea v-model="rejectReason" class="input" rows="3" placeholder="e.g. Clashes with scheduled maintenance"></textarea>
            </div>
            <div class="reject-actions">
              <button class="cancel-reject-btn" @click="closeReject">Cancel</button>
              <button class="confirm-reject-btn" @click="confirmReject">Reject booking</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.secretary-amenities { max-width: var(--content-max-width); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; gap: 12px; flex-wrap: wrap; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }
.add-btn { height: 40px; padding: 0 18px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-weight: 700; font-size: var(--font-size-sm); flex-shrink: 0; }
.add-btn:hover { background: var(--c-800); }

.toast { background: var(--color-success-bg); color: var(--color-success-text); border: 1px solid var(--color-success); border-radius: var(--radius-md); padding: 12px 16px; font-size: var(--font-size-md); font-weight: 600; margin-bottom: 16px; }

.stats-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.stat { flex: 1; min-width: 140px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 14px 16px; display: flex; flex-direction: column; box-shadow: var(--shadow-sm); }
.stat-num { font-size: var(--font-size-2xl, 28px); font-weight: 800; color: var(--color-text-primary); }
.stat-label { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }

.approvals-panel { border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-surface); overflow: hidden; box-shadow: var(--shadow-sm); }
.approvals-toggle { width: 100%; display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; background: var(--color-warning-bg); color: var(--color-warning-text); font-weight: 700; font-size: var(--font-size-md); }
.chevron { transition: transform var(--transition-fast); }
.chevron.up { transform: rotate(180deg); }
.approvals-list { padding: 14px 18px; display: flex; flex-direction: column; gap: 10px; }
.empty { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.approval-row { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: var(--radius-md); background: var(--badge-closed-bg); }
.approval-icon { font-size: 24px; }
.approval-info { flex: 1; min-width: 0; }
.approval-name { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.approval-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.approval-actions { display: flex; gap: 6px; }
.approve-btn { padding: 6px 14px; border-radius: var(--radius-md); background: var(--color-success); color: #fff; font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }
.reject-btn { padding: 6px 14px; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap; }

.section-title { font-size: var(--font-size-xl); font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.group-count { font-weight: 600; color: var(--color-text-muted); font-size: var(--font-size-md); }
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; }

.amenity-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.empty-group { grid-column: 1 / -1; font-size: var(--font-size-sm); color: var(--color-text-muted); padding: 16px; text-align: center; border: 1px dashed var(--color-border); border-radius: var(--radius-lg); }
.amenity-card { position: relative; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-xl); box-shadow: var(--shadow-sm); padding: 14px; display: flex; flex-direction: column; gap: 10px; }

.maint-btn {
  position: absolute; top: 10px; right: 10px;
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--badge-closed-bg); font-size: 13px; line-height: 1;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.maint-btn.active { background: var(--color-warning-bg); color: var(--color-warning-text); }
.maint-btn:hover { background: var(--color-border); }
.maint-btn.active:hover { opacity: 0.85; }

.card-top { display: flex; align-items: center; gap: 10px; padding-right: 38px; cursor: pointer; }
.card-icon { font-size: 28px; }
.card-top-info { flex: 1; min-width: 0; }
.amenity-name { font-weight: 700; font-size: var(--font-size-md); color: var(--color-text-primary); }
.amenity-location { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 1px; }

.card-status-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.status-tag { font-size: var(--font-size-xs); font-weight: 700; padding: 4px 10px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); }
.status-tag.available { background: var(--color-success-bg); color: var(--color-success-text); }
.status-tag.maintenance { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-tag.booked { background: var(--color-info-bg, var(--badge-closed-bg)); color: var(--color-info-text); }
.pricing-tag { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); }
.pricing-tag.muted { color: var(--color-text-muted); font-weight: 600; }

.card-actions { display: flex; gap: 8px; }
.edit-btn { flex: 1; padding: 8px 0; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-xs); font-weight: 700; }
.edit-btn:hover { background: var(--c-800); }
.delete-btn { flex: 1; padding: 8px 0; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; }

/* ---- modal chrome ----
   Teleported to <body> and given a very high z-index so a fixed/sticky app
   navbar (which usually sits around z-index 50–200) can never render above
   the overlay and clip the modal header. */
.overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 2000; padding: 24px;
}
.modal {
  background: var(--color-surface); border-radius: var(--radius-xl);
  width: 100%; max-width: 480px; max-height: min(90vh, 720px);
  display: flex; flex-direction: column; overflow: hidden;
  box-shadow: var(--shadow-md);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 20px 24px; border-bottom: 1px solid var(--color-border); flex-shrink: 0;
}
.modal-header h3 { font-size: var(--font-size-lg); font-weight: 800; color: var(--color-text-primary); }
.close-btn { flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%; background: var(--badge-closed-bg); color: var(--color-text-primary); font-size: 13px; display: flex; align-items: center; justify-content: center; }
.modal-body { padding: 20px 24px 24px; overflow-y: auto; }

/* form fields */
.field { margin-bottom: 14px; display: flex; flex-direction: column; gap: 4px; }
.field-row { display: flex; gap: 12px; }
.field-row .field { flex: 1; }
.field.grow { flex: 2; }
.icon-field { max-width: 70px; }
label { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); }
.input { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px 10px; font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary); width: 100%; font-family: inherit; }
textarea.input { resize: vertical; }
.hint { font-size: 11px; color: var(--color-text-muted); }
.checks { justify-content: center; gap: 8px; }
.check { display: flex; align-items: center; gap: 6px; font-weight: 600; color: var(--color-text-primary); font-size: var(--font-size-sm); }
.check input { width: 15px; height: 15px; }
.divider { height: 1px; background: var(--color-border); margin: 16px 0; }
.save-btn { width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-900); color: #fff; font-size: var(--font-size-md); font-weight: 700; margin-top: 6px; }
.save-btn:hover { background: var(--c-800); }

/* bookings panel */
.filter-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.chip { padding: 6px 12px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; }
.chip.active { background: var(--c-900); color: #fff; }
.status-select { margin-bottom: 16px; }
.list { display: flex; flex-direction: column; gap: 10px; }
.booking-empty { font-size: var(--font-size-sm); color: var(--color-text-muted); padding: 20px 0; text-align: center; }
.row { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 12px; }
.row-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.resident { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.status-pill { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); white-space: nowrap; }
.status-pill.confirmed, .status-pill.completed { background: var(--color-success-bg); color: var(--color-success-text); }
.status-pill.awaiting_payment { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-pill.cancelled, .status-pill.rejected { background: var(--badge-closed-bg); color: var(--color-text-muted); }
.row-actions { display: flex; gap: 8px; margin-top: 10px; }

/* reject modal */
.reject-modal { max-width: 420px; }
.reject-summary { font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: 600; margin-bottom: 14px; }
.reject-actions { display: flex; gap: 10px; margin-top: 6px; }
.cancel-reject-btn { flex: 1; height: 44px; border-radius: var(--radius-md); background: var(--badge-closed-bg); color: var(--color-text-secondary); font-size: var(--font-size-sm); font-weight: 700; }
.cancel-reject-btn:hover { background: var(--color-border); }
.confirm-reject-btn { flex: 1; height: 44px; border-radius: var(--radius-md); background: var(--color-danger, #C0392B); color: #fff; font-size: var(--font-size-sm); font-weight: 700; }
.confirm-reject-btn:hover { opacity: 0.9; }
</style>