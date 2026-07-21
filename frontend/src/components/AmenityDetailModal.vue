<script setup>
import { ref, computed } from 'vue'
import { checkAvailability, isBookable, statusLabel } from '../composables/useAmenities'

const props = defineProps({ amenity: { type: Object, required: true } })
const emit = defineEmits(['close', 'book'])

const checkDate = ref('')
const checkStart = ref('18:00')
const checkEnd = ref('20:00')
const result = ref(null)

const isHourly = computed(() => props.amenity.pricing?.type === 'hourly')
const isDaily = computed(() => props.amenity.pricing?.type === 'daily')
const bookable = computed(() => isBookable(props.amenity) && props.amenity.status !== 'maintenance')

function runCheck() {
  if (!checkDate.value) return
  result.value = checkAvailability(props.amenity.id, {
    date: checkDate.value,
    startTime: checkStart.value,
    endTime: checkEnd.value,
  })
}

function proceedToBook() {
  emit('book', props.amenity)
}
</script>

<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="sheet">
      <button class="close-btn" @click="$emit('close')">✕</button>

      <div class="hero" :class="{ infra: amenity.category === 'unbookable' }">
        <span class="hero-icon">{{ amenity.icon }}</span>
        <span :class="['status-tag', amenity.status]">
          <span class="status-dot"></span>{{ statusLabel(amenity.status) }}
          <template v-if="amenity.status_until"> · till {{ amenity.status_until }}</template>
        </span>
      </div>

      <div class="content">
        <h3>{{ amenity.name }}</h3>
        <p class="location">📍 {{ amenity.location }}</p>
        <p class="desc">{{ amenity.description }}</p>

        <div class="spec-grid">
          <div class="spec" v-if="amenity.capacity">
            <span class="spec-label">Capacity</span>
            <span class="spec-value">Up to {{ amenity.capacity }}</span>
          </div>
          <div class="spec" v-if="amenity.air_conditioned !== undefined">
            <span class="spec-label">Air conditioned</span>
            <span class="spec-value">{{ amenity.air_conditioned ? 'Yes' : 'No' }}</span>
          </div>
          <div class="spec" v-if="amenity.decoratable !== undefined">
            <span class="spec-label">Decoration allowed</span>
            <span class="spec-value">{{ amenity.decoratable ? 'Yes' : 'No' }}</span>
          </div>
          <div class="spec" v-if="amenity.pricing?.type">
            <span class="spec-label">Pricing</span>
            <span class="spec-value">₹{{ amenity.pricing.rate }} / {{ amenity.pricing.unitLabel }}</span>
          </div>
          <div class="spec" v-if="amenity.booking_type">
            <span class="spec-label">Approval</span>
            <span class="spec-value">{{ amenity.booking_type === 'automatic' ? 'Instant' : 'Secretary approval' }}</span>
          </div>
        </div>

        <div v-if="amenity.features?.length" class="features">
          <span v-for="f in amenity.features" :key="f" class="feature-chip">{{ f }}</span>
        </div>

        <div v-if="amenity.special_booking" class="special-note">
          Normally a shared facility — can be booked exclusively for private events with secretary approval.
        </div>

        <!-- availability checker -->
        <div v-if="bookable" class="availability-box">
          <div class="avail-title">Check availability</div>
          <div class="avail-row">
            <input type="date" v-model="checkDate" class="avail-input" />
            <template v-if="isHourly">
              <input type="time" v-model="checkStart" class="avail-input small" />
              <span class="to">to</span>
              <input type="time" v-model="checkEnd" class="avail-input small" />
            </template>
            <button class="check-btn" @click="runCheck">Check</button>
          </div>
          <div v-if="result" :class="['avail-result', result.available ? 'free' : 'busy']">
            {{ result.available ? '✓ ' + result.message : '✕ ' + result.message }}
          </div>
        </div>

        <div class="actions">
          <button v-if="bookable" class="book-btn" @click="proceedToBook">
            {{ amenity.booking_type === 'approval_required' ? 'Request booking' : 'Book now' }}
          </button>
          <span v-else-if="amenity.category === 'unbookable'" class="info-note">Infrastructure — no booking needed.</span>
          <span v-else-if="!isBookable(amenity)" class="info-note">Open to all residents — no booking needed.</span>
          <span v-else class="info-note">Unavailable while under maintenance.</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.5);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px;
}
.sheet {
  background: var(--color-surface); border-radius: var(--radius-xl);
  width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto;
  position: relative; box-shadow: var(--shadow-md);
}
.close-btn {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  width: 32px; height: 32px; border-radius: 50%;
  background: rgba(255,255,255,0.9); color: var(--color-text-primary);
  font-size: 14px; display: flex; align-items: center; justify-content: center;
}
.hero {
  background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%);
  height: 130px; display: flex; align-items: center; justify-content: center; position: relative;
}
.hero.infra { background: linear-gradient(155deg, #2d3748 0%, #4a5568 100%); }
.hero-icon { font-size: 44px; filter: grayscale(1) brightness(5); }
.status-tag {
  position: absolute; bottom: 12px; left: 16px; display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: var(--radius-pill); font-size: var(--font-size-xs);
  font-weight: 700; background: rgba(255,255,255,0.92); color: var(--color-text-primary);
}
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); flex-shrink: 0; }
.status-tag.booked .status-dot { background: var(--c-600); }
.status-tag.maintenance .status-dot { background: var(--color-warning); }

.content { padding: 20px; }
.content h3 { font-size: var(--font-size-xl); font-weight: 800; color: var(--color-text-primary); }
.location { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }
.desc { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin-top: 10px; line-height: 1.5; }

.spec-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; margin-top: 16px;
}
.spec { display: flex; flex-direction: column; gap: 2px; }
.spec-label { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.spec-value { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-primary); }

.features { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; }
.feature-chip {
  font-size: var(--font-size-xs); padding: 4px 10px; border-radius: var(--radius-pill);
  background: var(--badge-closed-bg); color: var(--color-text-secondary);
}

.special-note {
  margin-top: 14px; font-size: var(--font-size-xs); color: var(--color-warning-text);
  background: var(--color-warning-bg); padding: 8px 12px; border-radius: var(--radius-md);
}

.availability-box {
  margin-top: 18px; padding: 14px; border-radius: var(--radius-md); background: var(--badge-closed-bg);
}
.avail-title { font-size: var(--font-size-sm); font-weight: 700; margin-bottom: 8px; color: var(--color-text-primary); }
.avail-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.avail-input {
  border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 6px 8px;
  font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary);
}
.avail-input.small { width: 100px; }
.to { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.check-btn {
  padding: 6px 14px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-size: var(--font-size-sm); font-weight: 700;
}
.avail-result { margin-top: 10px; font-size: var(--font-size-sm); font-weight: 600; }
.avail-result.free { color: var(--color-success-text); }
.avail-result.busy { color: var(--color-warning-text); }

.actions { margin-top: 20px; }
.book-btn {
  width: 100%; height: 44px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-size: var(--font-size-md); font-weight: 700;
}
.book-btn:hover { background: var(--c-800); }
.info-note { font-size: var(--font-size-sm); color: var(--color-text-muted); }
</style>