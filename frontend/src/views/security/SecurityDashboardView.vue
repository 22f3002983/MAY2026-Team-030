<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MetricCard from '../../components/dashboard/MetricCard.vue'
import api from '../../api/axios'
import { digitsOnly, toStoredPhone } from '../../utils/phone'

// CHANGED — was a hardcoded placeholder array; now populated live from
// GET /api/flats/directory (flat -> primary resident lookup)
const flatDirectory = ref([])

async function fetchFlatDirectory() {
  try {
    const res = await api.get('/flats/directory')
    flatDirectory.value = res.data.flats
  } catch (err) {
    console.error('Failed to load flat directory', err)
  }
}

// CHANGED — matches on flat_number now (real field name from the API)
function residentForFlat(flatNumber) {
  return flatDirectory.value.find(f => f.flat_number === flatNumber)?.resident_name || ''
}
function residentIdForFlat(flatNumber) {
  return flatDirectory.value.find(f => f.flat_number === flatNumber)?.resident_id || null
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

// live visitor data
const todaysVisitors  = ref([])
const insideVisitors  = ref([])
const loading         = ref(true)

// session-only tracking of visitors this security session sent for gate
// approval, so the Approvals panel can tell them apart from a resident's
// own pre-registered walk-ins once status converges

async function fetchToday() {
  try {
    const res = await api.get('/visitors/today')
    todaysVisitors.value = res.data.visitors
  } catch (err) {
    console.error('Failed to load today\'s visitors', err)
  }
}

async function fetchInside() {
  try {
    const res = await api.get('/visitors/inside')
    insideVisitors.value = res.data.visitors
  } catch (err) {
    console.error('Failed to load visitors currently inside', err)
  }
}

async function refreshAll() {
  await Promise.all([fetchToday(), fetchInside()])
}

// ADDED — dashboard metric counts, sourced from the summary endpoint
// instead of being derived client-side from todaysVisitors/insideVisitors
const summaryStats = ref({
  visitorsInside:   '—',
  awaitingApproval: '—',
  preRegistered:    '—',
  deliveriesToday:  '—',
})

async function fetchSummary() {
  try {
    const res = await api.get('/summary/security')
    summaryStats.value = {
      visitorsInside:   res.data.visitors_inside,
      awaitingApproval: res.data.awaiting_approval,
      preRegistered:    res.data.pre_registered,
      deliveriesToday:  res.data.deliveries_today,
    }
  } catch (err) {
    console.error('Failed to load security summary', err)
  }
}

let pollHandle = null

onMounted(async () => {
  loading.value = true
  // CHANGED — added fetchFlatDirectory + fetchSummary alongside refreshAll
  await Promise.all([refreshAll(), fetchFlatDirectory(), fetchSummary()])
  loading.value = false
  // poll so resident approve/deny (done on their own device) shows up here
  // without a manual refresh — no websocket/push channel exists yet
  pollHandle = setInterval(() => {
    refreshAll()
    fetchSummary()   // ADDED — keep metric counts fresh too
  }, 10000)
})

onUnmounted(() => {
  if (pollHandle) clearInterval(pollHandle)
})

// ===== computed views =====

const activeApprovals = computed(() =>
  todaysVisitors.value.filter(v =>
    v.status === 'awaiting_approval' ||
    (v.visit_type === 'walk_in' && v.status === 'pre_registered' && !v.check_in_time && !v.is_expired)
  )
)

const currentlyInside = computed(() => insideVisitors.value)

const todaysLog = computed(() =>
  todaysVisitors.value
    .filter(v => ['checked_in', 'checked_out', 'rejected'].includes(v.status))
    .sort((a, b) => new Date(b.check_in_time || b.check_out_time || 0) - new Date(a.check_in_time || a.check_out_time || 0))
)

// CHANGED — metrics now read from summaryStats (server-computed) instead
// of being derived client-side
const metrics = computed(() => [
  { label: 'Visitors Inside',   value: String(summaryStats.value.visitorsInside),   sub: 'live count',     icon: '✓',  tint: '#4E8EA2' },
  { label: 'Awaiting Approval', value: String(summaryStats.value.awaitingApproval), sub: 'at the gate',    icon: '🛡', tint: '#E0A030' },
  { label: 'Pre-registered',    value: String(summaryStats.value.preRegistered),    sub: 'expected today', icon: '📅', tint: '#78BDE9' },
  { label: 'Deliveries',        value: String(summaryStats.value.deliveriesToday),  sub: 'today',          icon: '📦', tint: '#49769F' },
])

function statusLabel(v) {
  if (v.status === 'pre_registered' && v.is_expired && !v.check_in_time) return 'Expired'
  const map = {
    awaiting_approval: 'Waiting for resident',
    pre_registered:    'Awaiting check-in',
    checked_in:        'Checked In',
    checked_out:       'Checked Out',
    rejected:           'Rejected',
  }
  return map[v.status] || v.status
}

// =====================================================================
// VERIFY A PASS CODE
// =====================================================================
const passCode = ref('')
const verifyResult = ref(null)

async function verify() {
  const code = passCode.value.trim().toUpperCase()
  if (!code) return

  try {
    const res = await api.patch('/visitors/verify', { pass_code: code })
    verifyResult.value = { outcome: 'valid', visitor: res.data.visitor }
  } catch (err) {
    const allKnown = [...todaysVisitors.value, ...insideVisitors.value]
    const match = allKnown.find(v => v.pass_code === code)

    if (!match) {
      verifyResult.value = { outcome: 'not_found' }
    } else if (match.status === 'checked_in') {
      verifyResult.value = { outcome: 'already_in', visitor: match }
    } else if (match.status === 'checked_out') {
      verifyResult.value = { outcome: 'already_used', visitor: match }
    } else if (match.is_expired) {
      verifyResult.value = { outcome: 'expired', visitor: match }
    } else {
      verifyResult.value = { outcome: 'not_found' }
    }
  }
  passCode.value = ''
}

function closeVerifyModal() {
  verifyResult.value = null
}

async function checkIn(visitor) {
  try {
    await api.patch(`/visitors/${visitor.id}/checkin`)
    await refreshAll()
  } catch (err) {
    console.error('Check-in failed', err)
  }
}

async function checkOut(visitor) {
  try {
    await api.patch(`/visitors/${visitor.id}/checkout`)
    await refreshAll()
  } catch (err) {
    console.error('Check-out failed', err)
  }
}

async function rejectAtGate(visitor) {
  try {
    await api.patch(`/visitors/${visitor.id}/reject`)
    await refreshAll()
  } catch (err) {
    console.error('Reject failed', err)
  }
}

// =====================================================================
// UNEXPECTED VISITOR -> send to resident for approval
// =====================================================================
const showUnexpectedForm = ref(false)
const uvName    = ref('')
const uvPhone   = ref('')   // 10 raw digits; +91 prefix is shown separately
const uvVehicle = ref('')
const uvFlat    = ref('')
const uvPurpose = ref('')
const uvError   = ref('')
const uvSending = ref(false)

function openUnexpectedForm(prefillName = '') {
  uvName.value = prefillName
  uvPhone.value = ''
  uvVehicle.value = ''
  uvFlat.value = ''
  uvPurpose.value = ''
  uvError.value = ''
  showUnexpectedForm.value = true
  verifyResult.value = null
}

function closeUnexpectedForm() {
  showUnexpectedForm.value = false
}

function onUvPhoneInput(e) {
  uvPhone.value = digitsOnly(e.target.value)
}

async function sendForApproval() {
  uvError.value = ''
  if (!uvName.value.trim()) { uvError.value = 'Visitor name is required'; return }
  if (!uvFlat.value) { uvError.value = 'Select which flat they are visiting'; return }

  const residentId = residentIdForFlat(uvFlat.value)
  if (!residentId) { uvError.value = 'No resident on file for that flat'; return }
  if (uvPhone.value && uvPhone.value.length !== 10) {
    uvError.value = 'Phone number must be exactly 10 digits'
    return
  }

  uvSending.value = true
  try {
    const res = await api.post('/visitors/gate-request', {
      name:           uvName.value.trim(),
      resident_id:    residentId,
      phone:          toStoredPhone(uvPhone.value) || undefined,
      vehicle_number: uvVehicle.value.trim() || undefined,
      reason:         uvPurpose.value.trim() || undefined,
    })


    await refreshAll()
    closeUnexpectedForm()
  } catch (err) {
    uvError.value = err.response?.data?.error || 'Failed to send request to resident'
  } finally {
    uvSending.value = false
  }
}
</script>
<template>
  <div class="security-dashboard">

    <div class="page-header">
      <div>
        <h2>Gate Dashboard</h2>
        <p class="page-sub">Live visitor and entry status — Raghvendra Sai Society</p>
      </div>
      <button class="btn-outline" @click="openUnexpectedForm()">+ Log unexpected visitor</button>
    </div>

    <div class="metrics-grid">
      <MetricCard
        v-for="m in metrics"
        :key="m.label"
        :label="m.label"
        :value="m.value"
        :sub="m.sub"
        :icon="m.icon"
        :tint="m.tint"
      />
    </div>

    <div class="verify-banner">
      <div class="verify-text">
        <span class="verify-label">Verify a visitor</span>
        <span class="verify-sub">Enter the gate pass code to check a visitor in</span>
      </div>
      <input
        v-model="passCode"
        type="text"
        placeholder="GATE-••••"
        class="pass-input"
        @keyup.enter="verify"
      />
      <button class="verify-btn" @click="verify">Verify</button>
    </div>

    <!-- verify result modal -->
    <div v-if="verifyResult" class="modal-overlay" @click.self="closeVerifyModal">
      <div class="verify-modal">

        <template v-if="verifyResult.outcome === 'not_found'">
          <div class="verify-modal-icon error">✕</div>
          <h3 class="verify-modal-title">Pass Not Found</h3>
          <p class="verify-modal-sub">No pass matches this code. If someone's at the gate without one, log them and send it to the resident.</p>
          <div class="verify-modal-actions">
            <button class="verify-modal-close" @click="closeVerifyModal">Close</button>
            <button class="approve-modal-btn" @click="openUnexpectedForm()">Log unexpected visitor</button>
          </div>
        </template>

        <template v-else-if="verifyResult.outcome === 'expired'">
          <div class="verify-modal-icon error">✕</div>
          <h3 class="verify-modal-title">Pass Expired</h3>
          <p class="verify-modal-sub">This code expired {{ formatTime(verifyResult.visitor.expires_at) }}. Ask the resident to reissue it, or log the visitor for a fresh approval.</p>
          <div class="verify-modal-actions">
            <button class="verify-modal-close" @click="closeVerifyModal">Close</button>
            <button class="approve-modal-btn" @click="openUnexpectedForm(verifyResult.visitor.name)">Log unexpected visitor</button>
          </div>
        </template>

        <template v-else-if="verifyResult.outcome === 'already_in'">
          <div class="verify-modal-icon success">✓</div>
          <h3 class="verify-modal-title">Already Checked In</h3>
          <p class="verify-modal-sub">{{ verifyResult.visitor.name }} entered at {{ formatTime(verifyResult.visitor.check_in_time) }} and hasn't checked out yet.</p>
          <div class="verify-modal-actions">
            <button class="verify-modal-close" @click="closeVerifyModal">Close</button>
            <button class="reject-modal-btn" @click="checkOut(verifyResult.visitor); closeVerifyModal()">Check Out Now</button>
          </div>
        </template>

        <template v-else-if="verifyResult.outcome === 'already_used'">
          <div class="verify-modal-icon error">✕</div>
          <h3 class="verify-modal-title">Pass Already Used</h3>
          <p class="verify-modal-sub">{{ verifyResult.visitor.name }} already checked out at {{ formatTime(verifyResult.visitor.check_out_time) }}. This code is single-use — ask the resident for a new one.</p>
          <button class="verify-modal-close" @click="closeVerifyModal">Close</button>
        </template>

        <template v-else>
          <div class="verify-modal-icon success">✓</div>
          <h3 class="verify-modal-title">Valid Pass</h3>
          <div class="verify-detail-grid">
            <div class="verify-detail-row">
              <span class="vd-label">Visitor</span>
              <span class="vd-value">{{ verifyResult.visitor.name }}</span>
            </div>
            <div class="verify-detail-row">
              <span class="vd-label">Reason</span>
              <span class="vd-value">{{ verifyResult.visitor.reason || '—' }}</span>
            </div>
            <!-- NOTE: backend's visitor_to_security_dict does not return resident
                 name or flat — only resident_id. These rows are left out rather
                 than showing blank/wrong data. Add resident_name/flat to that
                 serializer if you want them displayed here. -->
            <div v-if="verifyResult.visitor.vehicle_number" class="verify-detail-row">
              <span class="vd-label">Vehicle</span>
              <span class="vd-value">{{ verifyResult.visitor.vehicle_number }}</span>
            </div>
            <div class="verify-detail-row">
              <span class="vd-label">Pass Code</span>
              <span class="vd-value code">{{ verifyResult.visitor.pass_code }}</span>
            </div>
            <div class="verify-detail-row">
              <span class="vd-label">Valid Till</span>
              <span class="vd-value">{{ formatTime(verifyResult.visitor.expires_at) }}</span>
            </div>
          </div>
          <div class="verify-modal-actions">
            <button class="reject-modal-btn" @click="rejectAtGate(verifyResult.visitor); closeVerifyModal()">
              ✕ Deny Entry
            </button>
            <button class="approve-modal-btn" @click="checkIn(verifyResult.visitor); closeVerifyModal()">
              ✓ Check In
            </button>
          </div>
        </template>

      </div>
    </div>

    <!-- log-an-unexpected-visitor form -->
    <div v-if="showUnexpectedForm" class="modal-overlay" @click.self="closeUnexpectedForm">
      <div class="verify-modal uv-modal">
        <h3 class="verify-modal-title">Log Unexpected Visitor</h3>
        <p class="verify-modal-sub">This sends a request to the resident's app for approval. Nothing is confirmed until they respond.</p>

        <div class="uv-field">
          <label>Visitor name</label>
          <input v-model="uvName" type="text" class="pass-input uv-input" placeholder="e.g. Vikram" />
        </div>
        <div class="uv-field">
          <label>Phone <span class="optional">(optional)</span></label>
          <div class="phone-input-group">
            <span class="phone-prefix">+91</span>
            <input
              :value="uvPhone"
              @input="onUvPhoneInput"
              type="text"
              inputmode="numeric"
              maxlength="10"
              class="pass-input uv-input phone-input"
              placeholder="98XXXXXXXX"
            />
          </div>
        </div>
        <div class="uv-field">
          <label>Vehicle number <span class="optional">(optional)</span></label>
          <input v-model="uvVehicle" type="text" class="pass-input uv-input" placeholder="e.g. DL 4C AB 1234" />
        </div>
        <div class="uv-field">
          <label>Visiting flat</label>
          <select v-model="uvFlat" class="pass-input uv-input">
            <option value="" disabled>Select a flat</option>
            <option v-for="f in flatDirectory" :key="f.flat_id" :value="f.flat_number">
              {{ f.flat_number }} — {{ f.resident_name }}
            </option>
          </select>
        </div>
        <div class="uv-field">
          <label>Reason for visit</label>
          <input v-model="uvPurpose" type="text" class="pass-input uv-input" placeholder="e.g. Says he's a friend of the resident" />
        </div>

        <p v-if="uvError" class="error-msg">{{ uvError }}</p>

        <div class="verify-modal-actions">
          <button class="verify-modal-close" @click="closeUnexpectedForm">Cancel</button>
          <button class="approve-modal-btn" :disabled="uvSending" @click="sendForApproval">
            {{ uvSending ? 'Sending...' : 'Send for Approval' }}
          </button>
        </div>
      </div>
    </div>

    <!-- approvals: unexpected visitors awaiting (or just given) a resident decision -->
    <div class="queue-card">
      <div class="queue-header">
        <span class="queue-title">Approvals</span>
        <span class="waiting-badge">{{ activeApprovals.length }} pending</span>
      </div>

      <div v-if="loading" class="empty-queue">Loading...</div>
      <div v-else-if="activeApprovals.length === 0" class="empty-queue">
        No unexpected visitors waiting on a resident decision
      </div>

      <div v-for="visitor in activeApprovals" :key="visitor.id" class="queue-row">
        <div class="visitor-avatar">{{ visitor.name.charAt(0) }}</div>
        <div class="visitor-info">
          <span class="visitor-name">{{ visitor.name }}</span>
          <span class="visitor-meta">{{ visitor.reason || 'Unexpected visitor' }}</span>
        </div>
        <div class="visitor-code-block">
          <span v-if="visitor.pass_code" class="visitor-code">{{ visitor.pass_code }}</span>
          <span class="visitor-time">{{ formatTime(visitor.created_at) }}</span>
        </div>
        <span :class="['queue-badge', visitor.status === 'awaiting_approval' ? 'waiting' : 'checked_in']">
          {{ visitor.status === 'awaiting_approval' ? 'Waiting for resident' : 'Approved — check in' }}
        </span>

        <!-- resident already approved (status = pre_registered): security checks in -->
        <div v-if="visitor.status === 'pre_registered'" class="queue-actions">
          <button class="approve-btn" @click="checkIn(visitor)" title="Check in">✓</button>
        </div>
        <!-- still pending — nothing for security to do but wait -->
        <div v-else class="queue-actions">
          <span class="visitor-meta">Waiting on resident's app</span>
        </div>
      </div>
    </div>

    <!-- currently inside, with check-out -->
    <div class="queue-card">
      <div class="queue-header">
        <span class="queue-title">Checked in — currently inside</span>
        <span class="waiting-badge in-badge">{{ currentlyInside.length }} inside</span>
      </div>

      <div v-if="loading" class="empty-queue">Loading...</div>
      <div v-else-if="currentlyInside.length === 0" class="empty-queue">
        No one checked in right now
      </div>

      <div v-for="visitor in currentlyInside" :key="visitor.id" class="queue-row">
        <div class="visitor-avatar">{{ visitor.name.charAt(0) }}</div>
        <div class="visitor-info">
          <span class="visitor-name">{{ visitor.name }}</span>
          <span class="visitor-meta">{{ visitor.reason || '—' }}</span>
        </div>
        <div class="visitor-code-block">
          <span v-if="visitor.pass_code" class="visitor-code">{{ visitor.pass_code }}</span>
          <span class="visitor-time">In {{ formatTime(visitor.check_in_time) }}</span>
        </div>
        <span class="queue-badge checked_in">Checked In</span>
        <div class="queue-actions">
          <button class="checkout-btn" @click="checkOut(visitor)">Check Out</button>
        </div>
      </div>
    </div>

    <!-- today's visitor log -->
    <div class="log-card">
      <div class="log-header">
        <span class="queue-title">Today's visitor log</span>
      </div>
      <div class="log-table-wrap">
        <table class="log-table">
          <thead>
            <tr>
              <th>Visitor</th>
              <th>Pass Code</th>
              <th>In</th>
              <th>Out</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in todaysLog" :key="v.id">
              <td>
                <span class="log-name">{{ v.name }}</span>
                <span class="log-purpose">{{ v.reason }}</span>
              </td>
              <td class="log-code">{{ v.pass_code || '—' }}</td>
              <td class="log-time">{{ formatTime(v.check_in_time) }}</td>
              <td class="log-time">{{ formatTime(v.check_out_time) }}</td>
              <td>
                <span :class="['log-badge', v.status]">
                  {{ statusLabel(v) }}
                </span>
              </td>
            </tr>
            <tr v-if="!loading && todaysLog.length === 0">
              <td colspan="5" class="empty-queue">Nothing checked in or out yet today</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<style scoped>
.security-dashboard {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 12px;
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

/* ADDED */
.btn-outline {
  height: 42px; padding: 0 18px; border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft); background: var(--color-surface);
  color: var(--c-800); font-size: var(--font-size-md); font-weight: 700;
  white-space: nowrap; transition: all var(--transition-fast); flex-shrink: 0;
}
.btn-outline:hover { border-color: var(--c-600); background: var(--color-bg); }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.verify-banner {
  background: linear-gradient(150deg, var(--c-900), var(--c-800));
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.verify-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.verify-label {
  font-size: var(--font-size-xs);
  color: var(--c-100);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.verify-sub {
  font-size: var(--font-size-md);
  color: #fff;
  font-weight: 600;
}

.pass-input {
  width: 180px;
  height: 46px;
  padding: 0 14px;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-family: ui-monospace, monospace;
  font-weight: 700;
  letter-spacing: 1px;
  background: #fff;
  color: var(--c-900);
  outline: none;
  flex-shrink: 0;
}

.verify-btn {
  height: 46px;
  padding: 0 22px;
  border-radius: var(--radius-md);
  background: var(--c-100);
  color: var(--c-900);
  font-weight: 800;
  font-size: var(--font-size-md);
  flex-shrink: 0;
  transition: opacity var(--transition-fast);
}

.verify-btn:hover { opacity: 0.85; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.verify-modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: 32px 28px;
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

/* ADDED: unexpected-visitor form uses the same modal shell, left-aligned */
.uv-modal { text-align: left; align-items: stretch; max-width: 420px; }
.uv-field { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.uv-field label { font-size: var(--font-size-xs); font-weight: 700; color: var(--c-800); }
.uv-input { width: 100%; font-family: var(--font-family); font-weight: 500; letter-spacing: normal; font-size: var(--font-size-sm); color: var(--color-text-primary); background: var(--color-surface-soft); border: 1.5px solid var(--color-border-soft); }

.phone-input-group { display: flex; align-items: center; gap: 8px; }
.phone-prefix {
  height: 46px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  color: var(--color-text-secondary);
  font-weight: 600;
  flex-shrink: 0;
}
.phone-input { flex: 1; }
.optional { font-weight: 500; color: var(--color-text-muted); }
.error-msg { font-size: var(--font-size-xs); color: var(--color-danger); }

.verify-modal-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 4px;
}

.verify-modal-icon.success {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.verify-modal-icon.error {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}

.verify-modal-title {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--c-900);
}

.verify-modal-sub {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
}

.verify-detail-grid {
  width: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-top: 4px;
  text-align: left;
}

.verify-detail-row {
  display: flex;
  align-items: center;
  padding: 11px 16px;
  border-bottom: 1px solid var(--color-border);
  gap: 12px;
}

.verify-detail-row:last-child { border-bottom: none; }

.vd-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  width: 72px;
  flex-shrink: 0;
}

.vd-value {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.vd-value.code {
  font-family: ui-monospace, monospace;
  color: var(--c-800);
}

.verify-modal-actions {
  display: flex;
  gap: 10px;
  width: 100%;
  margin-top: 8px;
}

.approve-modal-btn {
  flex: 1;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-success);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: opacity var(--transition-fast);
}

.approve-modal-btn:hover { opacity: 0.88; }

.reject-modal-btn {
  flex: 1;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  font-size: var(--font-size-md);
  font-weight: 700;
  border: 1.5px solid var(--color-danger);
  transition: background var(--transition-fast);
}

.reject-modal-btn:hover {
  background: var(--color-danger);
  color: #fff;
}

.verify-modal-close {
  height: 42px;
  padding: 0 24px;
  border-radius: var(--radius-md);
  background: var(--color-bg);
  border: 1.5px solid var(--color-border-soft);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 600;
  transition: all var(--transition-fast);
}

.verify-modal-close:hover {
  border-color: var(--c-600);
  color: var(--c-800);
}

.queue-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
  margin-bottom: 20px;
}

.queue-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.queue-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
}

.waiting-badge {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: #9A6412;
  background: #FBEEDA;
  padding: 4px 11px;
  border-radius: var(--radius-pill);
}

.in-badge { color: var(--color-success-text); background: var(--color-success-bg); }

.empty-queue {
  padding: 32px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
}

.queue-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 15px 20px;
  border-bottom: 1px solid var(--color-border);
}

.queue-row:last-child { border-bottom: none; }

.visitor-avatar {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-lg);
}

.visitor-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.visitor-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-primary);
}

.visitor-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.visitor-code-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.visitor-code {
  font-family: ui-monospace, monospace;
  font-size: var(--font-size-sm);
  font-weight: 800;
  color: var(--c-800);
}

.visitor-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.queue-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  flex-shrink: 0;
}

.queue-badge.waiting    { background: var(--color-warning-bg); color: var(--color-warning-text); }
.queue-badge.walkin     { background: var(--color-info-bg);    color: var(--color-info-text);    }
.queue-badge.checked_in { background: var(--color-success-bg); color: var(--color-success-text); }

.queue-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.approve-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: #DDF3E7;
  color: #1E7A50;
  font-size: var(--font-size-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
}

.approve-btn:hover { background: #C6ECD7; }

.reject-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: #FBE9E4;
  color: #B4442F;
  font-size: var(--font-size-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
}

.reject-btn:hover { background: #F5D0C8; }

/* ADDED: check-out action on the "currently inside" list */
.checkout-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 700;
  transition: background var(--transition-fast);
}
.checkout-btn:hover { background: var(--c-900); }

.log-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.log-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.log-table-wrap { overflow-x: auto; }

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.log-table th {
  padding: 12px 20px;
  text-align: left;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  background: var(--color-surface-soft);
  border-bottom: 1px solid var(--color-border);
}

.log-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.log-table tbody tr:last-child td { border-bottom: none; }
.log-table tbody tr:hover { background: var(--color-surface-muted); }

.log-name {
  display: block;
  font-weight: 600;
  color: var(--color-text-primary);
}

.log-purpose {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.log-flat  { color: var(--color-text-secondary); font-weight: 600; }
.log-code  { font-family: ui-monospace, monospace; font-weight: 700; color: var(--c-800); }
.log-time  { color: var(--color-text-secondary); }

.log-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.log-badge.waiting    { background: var(--color-warning-bg); color: var(--color-warning-text); }
.log-badge.walkin     { background: var(--color-info-bg);    color: var(--color-info-text);    }
.log-badge.checked_in { background: var(--color-success-bg); color: var(--color-success-text); }
.log-badge.checked_out{ background: var(--color-bg);         color: var(--color-text-muted);   }
.log-badge.rejected   { background: var(--color-danger-bg);  color: var(--color-danger-text);  }
</style>