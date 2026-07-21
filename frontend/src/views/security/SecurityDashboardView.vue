<script setup>
import { ref, computed } from 'vue'
import MetricCard from '../../components/dashboard/MetricCard.vue'

// ===== ADDED: mock "resident directory" — in the real app this is a lookup
// against the flats/residents table, used so security can pick a flat
// instead of typing a resident's name blind. =====
const flatDirectory = [
  { flat: 'A-402', resident_name: 'Ravi Kumar' },
  { flat: 'B-210', resident_name: 'Priya Menon' },
  { flat: 'C-105', resident_name: 'Arjun Nair' },
  { flat: 'B-201', resident_name: 'Meena Sharma' },
]

function residentForFlat(flat) {
  return flatDirectory.find(f => f.flat === flat)?.resident_name || ''
}

let nextId = 100
function generateId() { return nextId++ }

function generatePassCode() {
  return 'GATE-' + (4000 + Math.floor(Math.random() * 900))
}

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function isToday(iso) {
  if (!iso) return false
  return iso.slice(0, 10) === todayStr()
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

// ===== CHANGED: this is now the single "source of truth" table — the same
// shape of row that the resident's Visitors.vue writes into. Security never
// keeps its own separate list; it reads/writes this one. In production this
// whole ref is replaced by API calls (GET /gate/passes?date=today etc). =====
const passRecords = ref([
  // pre-registered pass, arrived, not yet checked in — security scans the code
  {
    id: 1, pass_code: 'GATE-7712', name: 'Rahul Verma', phone: '98765 43210',
    flat: 'A-402', resident_name: 'Ravi Kumar', visitor_type: 'guest', purpose: 'Guest',
    vehicle_number: null, resident_note: null, registration_type: 'pre_register',
    pass_code_expiry: '2026-07-11T23:59:59', status: 'expected',
    check_in_time: null, check_out_time: null, revoked_at: null, times_code_used: 0,
    created_at: '2026-07-10T09:00:00',
  },
  // pre-registered, already checked in — currently inside
  {
    id: 2, pass_code: 'GATE-6640', name: 'Amazon Courier', phone: null,
    flat: 'B-210', resident_name: 'Priya Menon', visitor_type: 'delivery', purpose: 'Parcel delivery',
    vehicle_number: null, resident_note: null, registration_type: 'pre_register',
    pass_code_expiry: '2026-07-11T18:00:00', status: 'checked_in',
    check_in_time: '2026-07-11T11:40:00', check_out_time: null, revoked_at: null, times_code_used: 1,
    created_at: '2026-07-11T09:15:00',
  },
  // checked in AND out earlier today — will show in today's log only
  {
    id: 3, pass_code: 'GATE-5521', name: 'Swiggy Delivery', phone: null,
    flat: 'A-402', resident_name: 'Ravi Kumar', visitor_type: 'delivery', purpose: 'Food delivery',
    vehicle_number: null, resident_note: null, registration_type: 'walk_in',
    pass_code_expiry: '2026-07-11T14:00:00', status: 'checked_out',
    check_in_time: '2026-07-11T13:10:00', check_out_time: '2026-07-11T13:22:00', revoked_at: null, times_code_used: 1,
    created_at: '2026-07-11T13:08:00',
  },
  {
    id: 4, pass_code: 'GATE-4410', name: 'Meena Sharma (guest)', phone: '90111 22334',
    flat: 'B-201', resident_name: 'Meena Sharma', visitor_type: 'guest', purpose: 'Family',
    vehicle_number: null, resident_note: null, registration_type: 'pre_register',
    pass_code_expiry: '2026-07-11T20:00:00', status: 'checked_in',
    check_in_time: '2026-07-11T12:02:00', check_out_time: null, revoked_at: null, times_code_used: 1,
    created_at: '2026-07-11T08:30:00',
  },
  // ADDED: revoked pass — proves verify() correctly blocks it even though not expired
  {
    id: 5, pass_code: 'GATE-9981', name: 'Suresh (revoked)', phone: null,
    flat: 'C-105', resident_name: 'Arjun Nair', visitor_type: 'other', purpose: 'Newspaper vendor',
    vehicle_number: null, resident_note: null, registration_type: 'walk_in',
    pass_code_expiry: '2026-07-12T23:59:59', status: 'expected',
    check_in_time: null, check_out_time: null, revoked_at: '2026-07-11T09:00:00', times_code_used: 0,
    created_at: '2026-07-11T08:45:00',
  },
  // ADDED: expired pass — never arrived before the code lapsed
  {
    id: 6, pass_code: 'GATE-8552', name: 'Amit (cousin)', phone: null,
    flat: 'A-402', resident_name: 'Ravi Kumar', visitor_type: 'guest', purpose: 'Guest',
    vehicle_number: null, resident_note: null, registration_type: 'pre_register',
    pass_code_expiry: '2026-07-11T10:00:00', status: 'expected',
    check_in_time: null, check_out_time: null, revoked_at: null, times_code_used: 0,
    created_at: '2026-07-10T18:00:00',
  },
  // ADDED: yesterday's checked-out visitor — proves today's log hides other days
  {
    id: 7, pass_code: 'GATE-3120', name: 'Plumber (walk-in)', phone: null,
    flat: 'C-105', resident_name: 'Arjun Nair', visitor_type: 'vendor_staff', purpose: 'Service',
    vehicle_number: null, resident_note: null, registration_type: 'walk_in',
    pass_code_expiry: '2026-07-10T12:00:00', status: 'checked_out',
    check_in_time: '2026-07-10T10:15:00', check_out_time: '2026-07-10T10:50:00', revoked_at: null, times_code_used: 1,
    created_at: '2026-07-10T10:12:00',
  },
  // ADDED: unexpected visitor already sent for resident approval, still pending
  {
    id: 8, pass_code: null, name: 'Vikram (says he\'s a friend)', phone: '98111 22333',
    flat: 'A-402', resident_name: 'Ravi Kumar', visitor_type: 'guest', purpose: 'Says he\'s meeting the resident',
    vehicle_number: 'UP 16 CD 4471', resident_note: null, registration_type: 'gate_approval',
    pass_code_expiry: null, status: 'pending_approval',
    check_in_time: null, check_out_time: null, revoked_at: null, times_code_used: 0,
    created_at: '2026-07-11T15:05:00',
  },
])

// ===== computed views — this IS the "security should only see today's log,
// checked-in ones, and approvals" scoping. No full visitor directory, no
// other days, no upcoming-but-not-arrived pre-registrations are exposed. =====

// Approvals: unexpected visitors still waiting on the resident's decision,
// plus ones the resident just approved but who haven't been checked in yet.
const activeApprovals = computed(() =>
  passRecords.value.filter(v =>
    v.status === 'pending_approval' ||
    (v.registration_type === 'gate_approval' && v.status === 'expected' && isToday(v.created_at))
  )
)

// Currently inside — this is what "check out" acts on.
const currentlyInside = computed(() =>
  passRecords.value.filter(v => v.status === 'checked_in')
)

// Today's resolved log — only things that actually happened today.
const todaysLog = computed(() =>
  passRecords.value
    .filter(v => ['checked_in', 'checked_out', 'rejected'].includes(v.status))
    .filter(v => isToday(v.check_in_time) || isToday(v.check_out_time))
    .sort((a, b) => new Date(b.check_in_time || b.check_out_time) - new Date(a.check_in_time || a.check_out_time))
)

const metrics = computed(() => [
  { label: 'Visitors Inside',   value: String(currentlyInside.value.length), sub: 'live count',     icon: '✓',  tint: '#4E8EA2' },
  { label: 'Awaiting Approval', value: String(passRecords.value.filter(v => v.status === 'pending_approval').length), sub: 'at the gate', icon: '🛡', tint: '#E0A030' },
  { label: 'Pre-registered',    value: String(passRecords.value.filter(v => v.registration_type === 'pre_register' && v.status === 'expected' && !v.revoked_at).length), sub: 'expected today', icon: '📅', tint: '#78BDE9' },
  { label: 'Deliveries',        value: String(todaysLog.value.filter(v => v.visitor_type === 'delivery').length), sub: 'today', icon: '📦', tint: '#49769F' },
])

function statusLabel(status) {
  const map = {
    expected: 'Awaiting check-in',
    pending_approval: 'Waiting for resident',
    checked_in: 'Checked In',
    checked_out: 'Checked Out',
    rejected: 'Rejected',
    revoked: 'Revoked',
    expired: 'Expired',
  }
  return map[status] || status
}

// =====================================================================
// VERIFY A PASS CODE — this is the actual "check against the DB" step.
// Order matters: not found -> revoked -> expired -> already used -> valid.
// =====================================================================
const passCode = ref('')
const verifyResult = ref(null)

function verify() {
  const code = passCode.value.trim().toUpperCase()
  if (!code) return

  const record = passRecords.value.find(v => v.pass_code && v.pass_code.toUpperCase() === code)

  if (!record) {
    verifyResult.value = { outcome: 'not_found' }
  } else if (record.revoked_at) {
    verifyResult.value = { outcome: 'revoked', visitor: record }
  } else if (record.pass_code_expiry && new Date() > new Date(record.pass_code_expiry)) {
    verifyResult.value = { outcome: 'expired', visitor: record }
  } else if (record.status === 'checked_in') {
    verifyResult.value = { outcome: 'already_in', visitor: record }
  } else if (record.status === 'checked_out') {
    verifyResult.value = { outcome: 'already_used', visitor: record }
  } else {
    verifyResult.value = { outcome: 'valid', visitor: record }
  }
  passCode.value = ''
}

function closeVerifyModal() {
  verifyResult.value = null
}

// ADDED: real check-in — was missing entirely before (old "approve" only
// worked on the in-memory queue, never touched an actual pass record).
function checkIn(record) {
  record.status = 'checked_in'
  record.check_in_time = new Date().toISOString()
  record.times_code_used += 1
}

// ADDED: check-out — did not exist before at all.
function checkOut(record) {
  record.status = 'checked_out'
  record.check_out_time = new Date().toISOString()
}

function rejectAtGate(record) {
  record.status = 'rejected'
  record.check_in_time = record.check_in_time || new Date().toISOString()
}

// =====================================================================
// UNEXPECTED VISITOR -> send to resident for approval (was missing).
// Security cannot approve entry for someone with no pass themselves;
// they can only log the visitor and push the decision to the resident,
// same as the "unexpected visitor" alert the resident sees in Visitors.vue.
// =====================================================================
const showUnexpectedForm = ref(false)
const uvName    = ref('')
const uvPhone   = ref('')
const uvVehicle = ref('')
const uvFlat    = ref('')
const uvPurpose = ref('')
const uvError   = ref('')

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

function sendForApproval() {
  uvError.value = ''
  if (!uvName.value.trim()) { uvError.value = 'Visitor name is required'; return }
  if (!uvFlat.value) { uvError.value = 'Select which flat they are visiting'; return }

  passRecords.value.unshift({
    id: generateId(),
    pass_code: null,
    name: uvName.value.trim(),
    phone: uvPhone.value.trim() || null,
    flat: uvFlat.value,
    resident_name: residentForFlat(uvFlat.value),
    visitor_type: 'guest',
    purpose: uvPurpose.value.trim() || 'Unexpected visitor',
    vehicle_number: uvVehicle.value.trim() || null,
    resident_note: null,
    registration_type: 'gate_approval',
    pass_code_expiry: null,
    status: 'pending_approval',
    check_in_time: null,
    check_out_time: null,
    revoked_at: null,
    times_code_used: 0,
    created_at: new Date().toISOString(),
  })

  closeUnexpectedForm()
}

// ===== DEMO ONLY: stands in for the resident's Approve/Deny tap on their
// phone (see Visitors.vue securityAlerts -> approveAtGate). In production
// this dashboard just receives a realtime/webhook update when the resident
// responds — security never makes this decision themselves. Kept here,
// clearly labeled, so the flow can be demonstrated end-to-end. =====
const GATE_APPROVAL_WINDOW_MIN = 15

function simulateResidentApprove(record) {
  record.status = 'expected'
  record.pass_code = generatePassCode()
  const d = new Date()
  d.setMinutes(d.getMinutes() + GATE_APPROVAL_WINDOW_MIN)
  record.pass_code_expiry = d.toISOString()
}

function simulateResidentDeny(record) {
  record.status = 'rejected'
}
</script>

<template>
  <div class="security-dashboard">

    <div class="page-header">
      <div>
        <h2>Gate Dashboard</h2>
        <p class="page-sub">Live visitor and entry status — Raghvendra Sai Society</p>
      </div>
      <!-- ADDED: entry point for logging someone with no pass code -->
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

        <template v-else-if="verifyResult.outcome === 'revoked'">
          <div class="verify-modal-icon error">✕</div>
          <h3 class="verify-modal-title">Pass Revoked</h3>
          <p class="verify-modal-sub">{{ verifyResult.visitor.resident_name }} revoked this pass. Do not allow entry — ask the visitor to contact the resident.</p>
          <button class="verify-modal-close" @click="closeVerifyModal">Close</button>
        </template>

        <template v-else-if="verifyResult.outcome === 'expired'">
          <div class="verify-modal-icon error">✕</div>
          <h3 class="verify-modal-title">Pass Expired</h3>
          <p class="verify-modal-sub">This code expired {{ formatTime(verifyResult.visitor.pass_code_expiry) }}. Ask the resident to reissue it, or log the visitor for a fresh approval.</p>
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
              <span class="vd-label">Purpose</span>
              <span class="vd-value">{{ verifyResult.visitor.purpose }}</span>
            </div>
            <div class="verify-detail-row">
              <span class="vd-label">Visiting</span>
              <span class="vd-value">{{ verifyResult.visitor.resident_name }}</span>
            </div>
            <div class="verify-detail-row">
              <span class="vd-label">Flat</span>
              <span class="vd-value">{{ verifyResult.visitor.flat }}</span>
            </div>
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
              <span class="vd-value">{{ formatTime(verifyResult.visitor.pass_code_expiry) }}</span>
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

    <!-- ADDED: log-an-unexpected-visitor form -->
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
          <input v-model="uvPhone" type="text" class="pass-input uv-input" placeholder="98xxx xxxxx" />
        </div>
        <div class="uv-field">
          <label>Vehicle number <span class="optional">(optional)</span></label>
          <input v-model="uvVehicle" type="text" class="pass-input uv-input" placeholder="e.g. DL 4C AB 1234" />
        </div>
        <div class="uv-field">
          <label>Visiting flat</label>
          <select v-model="uvFlat" class="pass-input uv-input">
            <option value="" disabled>Select a flat</option>
            <option v-for="f in flatDirectory" :key="f.flat" :value="f.flat">{{ f.flat }} — {{ f.resident_name }}</option>
          </select>
        </div>
        <div class="uv-field">
          <label>Reason for visit</label>
          <input v-model="uvPurpose" type="text" class="pass-input uv-input" placeholder="e.g. Says he's a friend of the resident" />
        </div>

        <p v-if="uvError" class="error-msg">{{ uvError }}</p>

        <div class="verify-modal-actions">
          <button class="verify-modal-close" @click="closeUnexpectedForm">Cancel</button>
          <button class="approve-modal-btn" @click="sendForApproval">Send for Approval</button>
        </div>
      </div>
    </div>

    <!-- approvals: unexpected visitors awaiting (or just given) a resident decision -->
    <div class="queue-card">
      <div class="queue-header">
        <span class="queue-title">Approvals</span>
        <span class="waiting-badge">{{ activeApprovals.length }} pending</span>
      </div>

      <div v-if="activeApprovals.length === 0" class="empty-queue">
        No unexpected visitors waiting on a resident decision
      </div>

      <div v-for="visitor in activeApprovals" :key="visitor.id" class="queue-row">
        <div class="visitor-avatar">{{ visitor.name.charAt(0) }}</div>
        <div class="visitor-info">
          <span class="visitor-name">{{ visitor.name }}</span>
          <span class="visitor-meta">{{ visitor.purpose }} · {{ visitor.flat }} ({{ visitor.resident_name }})</span>
        </div>
        <div class="visitor-code-block">
          <span v-if="visitor.pass_code" class="visitor-code">{{ visitor.pass_code }}</span>
          <span class="visitor-time">{{ formatTime(visitor.created_at) }}</span>
        </div>
        <span :class="['queue-badge', visitor.status === 'pending_approval' ? 'waiting' : 'checked_in']">
          {{ visitor.status === 'pending_approval' ? 'Waiting for resident' : 'Approved — check in' }}
        </span>

        <!-- resident already approved: security just checks them in -->
        <div v-if="visitor.status === 'expected'" class="queue-actions">
          <button class="approve-btn" @click="checkIn(visitor)" title="Check in">✓</button>
        </div>
        <!-- still pending: demo-only stand-in for the resident's own decision -->
        <div v-else class="queue-actions">
          <button class="approve-btn" @click="simulateResidentApprove(visitor)" title="Simulate resident approval (demo)">✓</button>
          <button class="reject-btn"  @click="simulateResidentDeny(visitor)" title="Simulate resident denial (demo)">✕</button>
        </div>
      </div>
    </div>

    <!-- ADDED: currently inside, with check-out -->
    <div class="queue-card">
      <div class="queue-header">
        <span class="queue-title">Checked in — currently inside</span>
        <span class="waiting-badge in-badge">{{ currentlyInside.length }} inside</span>
      </div>

      <div v-if="currentlyInside.length === 0" class="empty-queue">
        No one checked in right now
      </div>

      <div v-for="visitor in currentlyInside" :key="visitor.id" class="queue-row">
        <div class="visitor-avatar">{{ visitor.name.charAt(0) }}</div>
        <div class="visitor-info">
          <span class="visitor-name">{{ visitor.name }}</span>
          <span class="visitor-meta">{{ visitor.purpose }} · {{ visitor.flat }}</span>
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

    <!-- today's log — CHANGED: now actually scoped to today + resolved entries only -->
    <div class="log-card">
      <div class="log-header">
        <span class="queue-title">Today's visitor log</span>
      </div>
      <div class="log-table-wrap">
        <table class="log-table">
          <thead>
            <tr>
              <th>Visitor</th>
              <th>Flat</th>
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
                <span class="log-purpose">{{ v.purpose }}</span>
              </td>
              <td class="log-flat">{{ v.flat }}</td>
              <td class="log-code">{{ v.pass_code || '—' }}</td>
              <td class="log-time">{{ formatTime(v.check_in_time) }}</td>
              <td class="log-time">{{ formatTime(v.check_out_time) }}</td>
              <td>
                <span :class="['log-badge', v.status]">
                  {{ statusLabel(v.status) }}
                </span>
              </td>
            </tr>
            <tr v-if="todaysLog.length === 0">
              <td colspan="6" class="empty-queue">Nothing checked in or out yet today</td>
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