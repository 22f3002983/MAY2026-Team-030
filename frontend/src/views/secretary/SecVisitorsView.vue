<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'
import { formatPhoneDisplay } from '../../utils/phone'

// Local YYYY-MM-DD for today, used as the default filter and for the
// <input type="date"> v-model. Deliberately built from local
// year/month/day rather than toISOString() — toISOString() converts to
// UTC first, which can silently roll the date back a day for anyone
// east of UTC (e.g. IST) when it's already past midnight there.
function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const selectedDate = ref(todayStr())
const visitors      = ref([])
const loading       = ref(true)
const loadError     = ref('')

async function fetchVisitorsForDate() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/visitors/today', { params: { date: selectedDate.value } })
    visitors.value = res.data.visitors
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load visitors for this date'
    visitors.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchVisitorsForDate)

// Compares an ISO timestamp against the selected YYYY-MM-DD using local
// calendar date on both sides, so a check-in stored in UTC still lands
// on the right day for a resident/secretary in IST.
function sameLocalDate(isoStr, dateStr) {
  if (!isoStr || !dateStr) return false
  const d   = new Date(isoStr)
  const sel = new Date(dateStr + 'T00:00:00')
  return d.getFullYear() === sel.getFullYear() && d.getMonth() === sel.getMonth() && d.getDate() === sel.getDate()
}

// "Expected to come" — still waiting to check in, and either their
// expected_date is this day, or (for walk-ins, which don't carry a
// meaningful expected_date) they were created on this day. Matches the
// same "for that day" definition the backend's /visitors/today uses.
const expectedList = computed(() => visitors.value.filter(v =>
  v.status === 'pre_registered' && (
    v.expected_date === selectedDate.value ||
    (v.visit_type === 'walk_in' && sameLocalDate(v.created_at, selectedDate.value))
  )
))

// Checked in / checked out — the actual event happened on this day,
// regardless of what day the pass was originally expected for. A visitor
// who both checked in and out the same day appears in both lists.
const checkedInList  = computed(() => visitors.value.filter(v => sameLocalDate(v.check_in_time, selectedDate.value)))
const checkedOutList = computed(() => visitors.value.filter(v => sameLocalDate(v.check_out_time, selectedDate.value)))

function flatLabel(v) {
  if (!v.flat_number) return '—'
  return v.tower ? `${v.tower} · ${v.flat_number}` : v.flat_number
}
function phoneLabel(v) {
  return formatPhoneDisplay(v.phone) || '—'
}
function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

function isToday(dateStr) {
  return dateStr === todayStr()
}
</script>

<template>
  <div class="sec-visitors">
    <div class="page-header">
      <div>
        <h2>Visitors</h2>
        <p class="page-sub">Who's expected, checked in, and checked out — by date</p>
      </div>
      <div class="date-filter">
        <label for="visitor-date">Date</label>
        <input id="visitor-date" v-model="selectedDate" type="date" class="n-input" @change="fetchVisitorsForDate" />
        <span v-if="isToday(selectedDate)" class="today-pill">Today</span>
      </div>
    </div>

    <p v-if="loadError" class="error-msg">{{ loadError }}</p>
    <div v-if="loading" class="empty-queue">Loading...</div>

    <template v-else>
      <div class="visitor-section">
        <div class="section-header">
          <span class="section-title">Expected to come</span>
          <span class="count-badge">{{ expectedList.length }}</span>
        </div>
        <table class="v-table">
          <thead>
            <tr><th>Name</th><th>Phone</th><th>Flat</th></tr>
          </thead>
          <tbody>
            <tr v-for="v in expectedList" :key="v.id">
              <td>{{ v.name }}</td>
              <td>{{ phoneLabel(v) }}</td>
              <td>{{ flatLabel(v) }}</td>
            </tr>
            <tr v-if="expectedList.length === 0">
              <td colspan="3" class="empty-row">No one expected on this date</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="visitor-section">
        <div class="section-header">
          <span class="section-title">Checked in</span>
          <span class="count-badge">{{ checkedInList.length }}</span>
        </div>
        <table class="v-table">
          <thead>
            <tr><th>Name</th><th>Phone</th><th>Flat</th><th>In</th></tr>
          </thead>
          <tbody>
            <tr v-for="v in checkedInList" :key="v.id">
              <td>{{ v.name }}</td>
              <td>{{ phoneLabel(v) }}</td>
              <td>{{ flatLabel(v) }}</td>
              <td>{{ formatTime(v.check_in_time) }}</td>
            </tr>
            <tr v-if="checkedInList.length === 0">
              <td colspan="4" class="empty-row">No check-ins on this date</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="visitor-section">
        <div class="section-header">
          <span class="section-title">Checked out</span>
          <span class="count-badge">{{ checkedOutList.length }}</span>
        </div>
        <table class="v-table">
          <thead>
            <tr><th>Name</th><th>Phone</th><th>Flat</th><th>Out</th></tr>
          </thead>
          <tbody>
            <tr v-for="v in checkedOutList" :key="v.id">
              <td>{{ v.name }}</td>
              <td>{{ phoneLabel(v) }}</td>
              <td>{{ flatLabel(v) }}</td>
              <td>{{ formatTime(v.check_out_time) }}</td>
            </tr>
            <tr v-if="checkedOutList.length === 0">
              <td colspan="4" class="empty-row">No check-outs on this date</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sec-visitors { max-width: var(--content-max-width); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; gap: 12px; flex-wrap: wrap; }
.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.date-filter { display: flex; align-items: center; gap: 10px; }
.date-filter label { font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-secondary); }
.date-filter .n-input { width: auto; height: 38px; }
.today-pill { font-size: 11px; font-weight: 700; color: var(--color-success-text); background: var(--color-success-bg); padding: 3px 10px; border-radius: var(--radius-pill); }

.n-input { height: 40px; padding: 0 12px; border-radius: var(--radius-md); border: 1.5px solid var(--color-border-soft); background: var(--color-surface-soft); font-size: var(--font-size-sm); color: var(--color-text-primary); transition: border-color var(--transition-fast); }
.n-input:focus { border-color: var(--c-600); }

.error-msg { font-size: var(--font-size-xs); color: var(--color-danger); margin-bottom: 12px; }

.empty-queue { padding: 32px; text-align: center; color: var(--color-text-muted); font-size: var(--font-size-md); }

.visitor-section { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-xs); margin-bottom: 20px; }

.section-header { padding: 14px 20px; border-bottom: 1px solid var(--color-border); display: flex; align-items: center; justify-content: space-between; }
.section-title { font-size: var(--font-size-lg); font-weight: 800; color: var(--c-900); }
.count-badge { font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800); background: var(--color-bg); padding: 3px 10px; border-radius: var(--radius-pill); }

.v-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.v-table th { padding: 10px 20px; text-align: left; font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.4px; background: var(--color-surface-soft); border-bottom: 1px solid var(--color-border); }
.v-table td { padding: 12px 20px; border-bottom: 1px solid var(--color-border); color: var(--color-text-primary); }
.v-table tbody tr:last-child td { border-bottom: none; }
.v-table tbody tr:hover { background: var(--color-surface-muted); }
.empty-row { text-align: center; color: var(--color-text-muted); padding: 20px; }
</style>