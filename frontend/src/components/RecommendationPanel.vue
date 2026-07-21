<script setup>
import { ref } from 'vue'
import { recommend, EVENT_TYPES } from '../composables/useAmenities'

const emit = defineEmits(['select'])

const open = ref(false)
const eventType = ref(EVENT_TYPES[0])
const guests = ref(20)
const budget = ref(2000)
const hours = ref(3)
const results = ref(null)

function getRecommendation() {
  results.value = recommend({ eventType: eventType.value, guests: guests.value, budget: budget.value, hours: hours.value })
}
</script>

<template>
  <div class="panel">
    <button class="panel-toggle" @click="open = !open">
      <span class="ai-badge">✨ Find the right place</span>
      <span class="chevron" :class="{ up: open }">⌄</span>
    </button>

    <div v-if="open" class="panel-body">
      <p class="panel-sub">Tell us about your event and we'll suggest the best fit.</p>

      <div class="form-grid">
        <div class="field">
          <label>Event type</label>
          <select v-model="eventType" class="input">
            <option v-for="t in EVENT_TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div class="field">
          <label>Guests</label>
          <input type="number" min="1" v-model.number="guests" class="input" />
        </div>
        <div class="field">
          <label>Budget (₹)</label>
          <input type="number" min="0" step="100" v-model.number="budget" class="input" />
        </div>
        <div class="field">
          <label>Duration (hrs, if hourly)</label>
          <input type="number" min="1" v-model.number="hours" class="input" />
        </div>
      </div>

      <button class="get-btn" @click="getRecommendation">Get suggestions</button>

      <div v-if="results" class="results">
        <div v-if="results.length === 0" class="empty">No great match within these constraints — try a higher budget or fewer guests.</div>
        <div v-for="(r, i) in results" :key="r.amenity.id" class="result-card">
          <div class="result-top">
            <span class="result-icon">{{ r.amenity.icon }}</span>
            <div>
              <div class="result-name">{{ r.amenity.name }}<span v-if="i === 0" class="best-tag">Best match</span></div>
              <div class="result-meta">Fits {{ r.amenity.capacity }} · ₹{{ r.estimatedPrice.toLocaleString('en-IN') }} est.</div>
            </div>
          </div>
          <button class="view-btn" @click="emit('select', r.amenity)">View & book</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-surface);
  overflow: hidden; margin-bottom: 24px; box-shadow: var(--shadow-sm);
}
.panel-toggle {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; background: linear-gradient(155deg, var(--c-900) 0%, var(--c-500) 100%);
}
.ai-badge { color: #fff; font-weight: 700; font-size: var(--font-size-md); }
.chevron { color: #fff; transition: transform var(--transition-fast); }
.chevron.up { transform: rotate(180deg); }

.panel-body { padding: 18px; }
.panel-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 14px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.field { display: flex; flex-direction: column; gap: 4px; }
label { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); }
.input {
  border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px 10px;
  font-size: var(--font-size-sm); background: var(--color-surface); color: var(--color-text-primary);
}

.get-btn {
  width: 100%; height: 40px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-weight: 700; font-size: var(--font-size-sm);
}
.get-btn:hover { background: var(--c-800); }

.results { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.empty { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.result-card {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 12px; border-radius: var(--radius-md); background: var(--badge-closed-bg);
}
.result-top { display: flex; align-items: center; gap: 10px; }
.result-icon { font-size: 26px; }
.result-name { font-weight: 700; font-size: var(--font-size-sm); color: var(--color-text-primary); display: flex; align-items: center; gap: 8px; }
.best-tag {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: var(--radius-pill);
  background: var(--color-success-bg); color: var(--color-success-text);
}
.result-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: 2px; }
.view-btn {
  padding: 6px 14px; border-radius: var(--radius-md); background: var(--c-900); color: #fff;
  font-size: var(--font-size-xs); font-weight: 700; white-space: nowrap;
}
</style>