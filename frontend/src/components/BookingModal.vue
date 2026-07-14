<script setup>
import { ref } from 'vue'

const props = defineProps({
  amenity: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'confirm'])

const date = ref('')
const startTime = ref('')
const endTime = ref('')
const reason = ref('')
const error = ref('')

function confirm() {
  error.value = ''

  if (!date.value || !startTime.value || !endTime.value || !reason.value) {
    error.value = 'All fields are required'
    return
  }

  if (startTime.value >= endTime.value) {
    error.value = 'End time must be after start time'
    return
  }

  emit('confirm', {
    amenity_id:  props.amenity.id,
    amenity_name: props.amenity.name,
    date:        date.value,
    start_time:  startTime.value,
    end_time:    endTime.value,
    reason:      reason.value,
  })

  // reset
  date.value = ''
  startTime.value = ''
  endTime.value = ''
  reason.value = ''
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">

      <div class="modal-header">
        <div>
          <h3>Book {{ amenity?.name }}</h3>
          <span class="modal-sub">{{ amenity?.booking_type === 'automatic' ? 'Auto-approved' : 'Requires secretary approval' }}</span>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="modal-body">

        <label>Date</label>
        <input v-model="date" type="date" class="n-input" />

        <div class="time-row">
          <div class="time-field">
            <label>Start Time</label>
            <input v-model="startTime" type="time" class="n-input" />
          </div>
          <div class="time-field">
            <label>End Time</label>
            <input v-model="endTime" type="time" class="n-input" />
          </div>
        </div>

        <label>Reason for booking</label>
        <textarea
          v-model="reason"
          placeholder="e.g. Birthday party, family gathering..."
          class="n-input n-textarea"
        />

        <p v-if="error" class="error-msg">{{ error }}</p>

      </div>

      <div class="modal-footer">
        <button class="btn-secondary" @click="emit('close')">Cancel</button>
        <button class="btn-primary" @click="confirm">Confirm Booking</button>
      </div>

    </div>
  </div>
</template>

<style scoped>
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
  max-width: 460px;
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
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 3px;
  display: block;
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

.n-input:focus {
  border-color: var(--c-600);
}

.n-textarea {
  height: 80px;
  padding: 10px 13px;
  resize: vertical;
}

.time-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.time-field {
  display: flex;
  flex-direction: column;
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-top: 6px;
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

.btn-primary:hover {
  background: var(--c-900);
}

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