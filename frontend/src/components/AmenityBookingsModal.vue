<script setup>
import { ref, computed } from 'vue'
import {
  allBookingsForAmenity, bookingStatusLabel,
  approveBooking, rejectBooking, cancelBooking,
} from '../composables/useAmenities'

const props = defineProps({ amenity: { type: Object, required: true } })
const emit = defineEmits(['close'])

const timeframe = ref('all') // all | ongoing | upcoming | past
const statusFilter = ref('all')

const bookings = computed(() => allBookingsForAmenity(props.amenity.id))

const filtered = computed(() =>
  bookings.value.filter(b =>
    (timeframe.value === 'all' || b.timeframe === timeframe.value) &&
    (statusFilter.value === 'all' || b.status === statusFilter.value)
  )
)

const counts = computed(() => ({
  all: bookings.value.length,
  ongoing: bookings.value.filter(b => b.timeframe === 'ongoing').length,
  upcoming: bookings.value.filter(b => b.timeframe === 'upcoming').length,
  past: bookings.value.filter(b => b.timeframe === 'past').length,
}))

function handleApprove(b) { approveBooking(b.id) }
function handleReject(b) {
  const reason = prompt('Reason for rejecting (optional):') || ''
  rejectBooking(b.id, reason)
}
function handleCancel(b) {
  if (confirm(`Cancel ${b.user_name}'s booking on ${b.start_date}?`)) cancelBooking(b.id)
}
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <button class="close-btn" @click="$emit('close')">✕</button>
      <h3>{{ amenity.icon }} {{ amenity.name }} — bookings</h3>

      <div class="filter-row">
        <button v-for="tf in ['all','ongoing','upcoming','past']" :key="tf"
          :class="['chip', { active: timeframe === tf }]" @click="timeframe = tf">
          {{ tf.charAt(0).toUpperCase() + tf.slice(1) }} ({{ counts[tf] }})
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
        <div v-if="!filtered.length" class="empty">No bookings match these filters.</div>
        <div v-for="b in filtered" :key="b.id" class="row">
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
            <button class="approve-btn" @click="handleApprove(b)">Approve</button>
            <button class="reject-btn" @click="handleReject(b)">Reject</button>
          </div>
          <div class="row-actions" v-else-if="['awaiting_payment','confirmed'].includes(b.status)">
            <button class="cancel-btn" @click="handleCancel(b)">Cancel booking</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.5); display: flex; align-items: center; justify-content: center; z-index: 120; padding: 20px; }
.modal { background: var(--color-surface); border-radius: var(--radius-xl); width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto; padding: 24px; position: relative; box-shadow: var(--shadow-md); }
.close-btn { position: absolute; top: 14px; right: 14px; width: 30px; height: 30px; border-radius: 50%; background: var(--badge-closed-bg); color: var(--color-text-primary); font-size: 13px; display: flex; align-items: center; justify-content: center; }
.modal h3 { font-size: var(--font-size-lg); font-weight: 800; color: var(--color-text-primary); margin-bottom: 14px; padding-right: 30px; }

.filter-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.chip { padding: 6px 12px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; }
.chip.active { background: var(--c-900); color: #fff; }

.status-select { margin-bottom: 16px; }
.input { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px 10px; font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary); width: 100%; }

.list { display: flex; flex-direction: column; gap: 10px; }
.empty { font-size: var(--font-size-sm); color: var(--color-text-muted); padding: 20px 0; text-align: center; }
.row { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 12px; }
.row-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.resident { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.status-pill { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: var(--radius-pill); background: var(--badge-closed-bg); color: var(--color-text-secondary); white-space: nowrap; }
.status-pill.confirmed, .status-pill.completed { background: var(--color-success-bg); color: var(--color-success-text); }
.status-pill.awaiting_payment { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-pill.cancelled, .status-pill.rejected { background: var(--badge-closed-bg); color: var(--color-text-muted); }

.row-actions { display: flex; gap: 8px; margin-top: 10px; }
.approve-btn { padding: 6px 14px; border-radius: var(--radius-md); background: var(--color-success); color: #fff; font-size: var(--font-size-xs); font-weight: 700; }
.reject-btn { padding: 6px 14px; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; }
.cancel-btn { padding: 6px 14px; border-radius: var(--radius-md); background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-xs); font-weight: 700; }
</style>