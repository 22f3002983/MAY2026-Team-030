<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MetricCard from '../components/dashboard/MetricCard.vue'
import api from '../api/axios'

const router = useRouter()
const auth = useAuthStore()

// ---------------------------------------------------------------------------
// Secretary dashboard — live data from GET /api/summary/secretary.
// This overrides the hardcoded ROLE_CONFIG.secretary values below once it
// loads; the hardcoded values remain as a fallback while loading / if the
// request fails, so the dashboard never renders blank.
// (Resident and security dashboards are untouched — still on mock data.)
// ---------------------------------------------------------------------------
const secretarySummary = ref(null)
const expandedComplaint = ref(null)
function toggleComplaint(id) {
  expandedComplaint.value = expandedComplaint.value === id ? null : id
}

function formatINR(amount) {
  const n = Number(amount) || 0
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`
  return `₹${Math.round(n)}`
}

function priorityLabel(priority) {
  return { high: 'High', medium: 'Medium', low: 'Low' }[priority] || priority
}

// maps issue priority -> the feed-chip color classes already defined in
// <style scoped> below (in_progress = amber, completed = green, high = red)
function priorityClass(priority) {
  return { high: 'high', medium: 'in_progress', low: 'completed' }[priority] || 'assigned'
}

async function loadSecretarySummary() {
  try {
    const res = await api.get('/summary/secretary')
    secretarySummary.value = res.data
  } catch (err) {
    console.error('Failed to load secretary dashboard summary', err)
  }
}

// ---------------------------------------------------------------------------
// Resident dashboard — live data from GET /api/summary/resident.
// Same override pattern as secretary above: hardcoded ROLE_CONFIG.resident
// stays as a loading/error fallback.
// ---------------------------------------------------------------------------
const residentSummary = ref(null)

function formatINRFull(amount) {
  return `₹${Math.round(Number(amount) || 0).toLocaleString('en-IN')}`
}

// backend sends zero-padded day ("02 Jul") — strip the leading zero to match
// the original "2 Jul" style
function trimDay(dateStr) {
  return dateStr ? dateStr.replace(/^0/, '') : dateStr
}

function formatShortDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getDate()} ${d.toLocaleString('en-IN', { month: 'short' })}`
}

function issueStatusLabel(status) {
  return { open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', closed: 'Closed' }[status] || status
}

function issueStatusClass(status) {
  return { open: 'assigned', in_progress: 'in_progress', resolved: 'completed', closed: 'completed' }[status] || 'assigned'
}

async function loadResidentSummary() {
  try {
    const res = await api.get('/summary/resident')
    residentSummary.value = res.data
  } catch (err) {
    console.error('Failed to load resident dashboard summary', err)
  }
}

onMounted(() => {
  if (auth.role === 'secretary') loadSecretarySummary()
  if (auth.role === 'resident') loadResidentSummary()
})

/*
  Instead of writing a separate if/else check inside every computed
  property, everything for a given role lives together in one object.
  ROLE_CONFIG[auth.role] gives us metrics + feed + quickActions +
  actionCard in one place, so adding a new role later just means
  adding one new key here instead of touching four different computeds.
*/
const ROLE_CONFIG = {
  resident: {
    metrics: [
      { label: 'Open Complaints', value: '2', sub: '1 in progress', icon: '⚠', tint: '#78BDE9' },
      { label: 'Upcoming Bookings', value: '1', sub: 'Clubhouse · 4 Jul', icon: '📅', tint: '#4E8EA2' },
      { label: 'Pending Dues', value: '₹13,250', sub: 'due 5 Jul', icon: '💳', tint: '#E0A030' },
      { label: 'Latest Notice', value: 'Water cut', sub: '2 Jul, 10 AM', icon: '🔔', tint: '#49769F' },
    ],
    feedTitle: 'Your recent complaints',
    feed: [
      { tag: '043', title: 'Water leakage under kitchen sink', meta: 'Plumbing · 28 Jun', status: 'In Progress', statusClass: 'in_progress' },
      { tag: '038', title: 'Ceiling fan not working', meta: 'Electrical · 24 Jun', status: 'Resolved', statusClass: 'completed' },
      { tag: '031', title: 'Bathroom tiles cracked', meta: 'Carpentry · 18 Jun', status: 'Open', statusClass: 'assigned' },
      { tag: '025', title: 'Water pressure low in tap', meta: 'Plumbing · 12 Jun', status: 'Resolved', statusClass: 'completed' },
    ],
    quickActions: [
      { label: 'Raise a complaint', icon: '⚠', to: '/complaints' },
      { label: 'Book an amenity', icon: '📅', to: '/amenities' },
      { label: 'Pre-register visitor', icon: '👤', to: '/visitors' },
    ],
    feedRoute: '/complaints',
    actionCard: {
      label: 'Reminder',
      text: 'Q2 maintenance of ₹13,250 is due on 5 July.',
      cta: 'View dues',
      to: '/maintenance',
    },
  },

  secretary: {
    metrics: [
      { label: 'Open Complaints', value: '12', sub: '+2 raised today', icon: '⚠', tint: '#78BDE9' },
      { label: 'Pending Dues', value: '₹4.8L', sub: 'across 42 flats', icon: '💳', tint: '#E0A030' },
      { label: 'Active Vendors', value: '4', sub: '5 categories', icon: '🔧', tint: '#4E8EA2' },
      { label: 'Unread Notices', value: '2', sub: 'posted this week', icon: '🔔', tint: '#49769F' },
    ],
    feedTitle: 'Latest complaints',
    feed: [
      { id: '1', tag: 'A4', title: 'Water leakage under kitchen sink', description: 'Water leakage under kitchen sink', meta: 'Ravi Kumar · A-402', status: 'High', statusClass: 'high' },
      { id: '2', tag: 'B2', title: 'Main switch tripping repeatedly', description: 'Main switch tripping repeatedly', meta: 'Priya Menon · B-201', status: 'Medium', statusClass: 'in_progress' },
      { id: '3', tag: 'C1', title: 'Bedroom door hinge broken', description: 'Bedroom door hinge broken', meta: 'Arjun Nair · C-105', status: 'Low', statusClass: 'completed' },
      { id: '4', tag: 'D3', title: 'Low water pressure in bathroom', description: 'Low water pressure in bathroom', meta: 'Sana Khan · D-303', status: 'High', statusClass: 'high' },
    ],
    quickActions: [
      { label: 'Post a notice', icon: '🔔', to: '/sec/notices' },
      { label: 'Broadcast emergency', icon: '🚨', to: '/sec/emergency' },
      { label: 'Manage vendors', icon: '🔧', to: '/sec/vendors' },
    ],
    feedRoute: '/sec/complaints',
    actionCard: {
      label: 'Action needed',
      text: '2 complaints are unassigned and awaiting a vendor.',
      cta: 'Assign vendors',
      to: '/sec/complaints',
    },
  },

  security: {
    metrics: [
      { label: 'Visitors Inside', value: '18', sub: 'live count', icon: '✓', tint: '#4E8EA2' },
      { label: 'Awaiting Approval', value: '2', sub: 'at the gate', icon: '🛡', tint: '#E0A030' },
      { label: 'Pre-registered', value: '27', sub: 'expected today', icon: '📅', tint: '#78BDE9' },
      { label: 'Deliveries', value: '11', sub: 'today', icon: '📦', tint: '#49769F' },
    ],
    feedTitle: '',
    feed: [],
    quickActions: [],
    feedRoute: '',
    actionCard: null,
  },
}

// Fall back to 'resident' config if role is missing/unknown, so the
// dashboard never renders completely blank.
// Fall back to 'resident' config if role is missing/unknown, so the
// dashboard never renders completely blank.
const roleData = computed(() => {
  const base = ROLE_CONFIG[auth.role] ?? ROLE_CONFIG.resident

  if (auth.role === 'secretary' && secretarySummary.value) {
    const s = secretarySummary.value
    return {
      ...base,
      metrics: [
        { label: 'Open Complaints', value: String(s.open_complaints), sub: `+${s.today_complaints} raised today`, icon: '⚠', tint: '#78BDE9' },
        { label: 'Pending Dues', value: formatINR(s.pending_dues), sub: `across ${s.pending_flats} flats`, icon: '💳', tint: '#E0A030' },
        { label: 'Active Vendors', value: String(s.active_vendors), sub: `${s.vendor_categories} categories`, icon: '🔧', tint: '#4E8EA2' },
        { label: 'Unread Notices', value: String(s.unread_notices), sub: 'posted this week', icon: '🔔', tint: '#49769F' },
      ],
      feed: s.recent_complaints.map(c => ({
        id: c.id,
        tag: (c.tower && c.floor != null) ? `${c.tower}${c.floor}` : c.category.slice(0, 2).toUpperCase(),
        title: c.title,
        description: c.description,
        meta: [c.resident_name, c.flat_number].filter(Boolean).join(' · ') || '—',
        status: priorityLabel(c.priority),
        statusClass: priorityClass(c.priority),
      })),
      actionCard: s.unassigned > 0 ? {
        label: 'Action needed',
        text: `${s.unassigned} complaint${s.unassigned !== 1 ? 's' : ''} ${s.unassigned !== 1 ? 'are' : 'is'} unassigned and awaiting a vendor.`,
        cta: 'Assign vendors',
        to: '/sec/complaints',
      } : null,
    }
  }

  if (auth.role === 'resident' && residentSummary.value) {
    const s = residentSummary.value
    return {
      ...base,
      metrics: [
        { label: 'Open Complaints', value: String(s.open_complaints), sub: `${s.in_progress} in progress`, icon: '⚠', tint: '#78BDE9' },
        { label: 'Upcoming Bookings', value: s.upcoming_booking ? '1' : '0', sub: s.upcoming_booking ? `${s.upcoming_booking.amenity_name} · ${formatShortDate(s.upcoming_booking.date)}` : 'None scheduled', icon: '📅', tint: '#4E8EA2' },
        { label: 'Pending Dues', value: formatINRFull(s.pending_due), sub: s.next_due_date ? `due ${trimDay(formatShortDate(s.next_due_date))}` : 'all paid', icon: '💳', tint: '#E0A030' },
        { label: 'Latest Notice', value: s.latest_notice?.title || 'No notices', sub: s.latest_notice ? `${trimDay(s.latest_notice.date)}, ${s.latest_notice.time}` : '', icon: '🔔', tint: '#49769F' },
      ],
      feed: s.recent_complaints.map(c => ({
        tag: c.id.slice(-3).toUpperCase(),
        title: c.description,
        meta: `${(c.category || '').charAt(0).toUpperCase()}${(c.category || '').slice(1)} · ${formatShortDate(c.created_at)}`,
        status: issueStatusLabel(c.status),
        statusClass: issueStatusClass(c.status),
      })),
      actionCard: s.pending_due > 0 ? {
        label: 'Reminder',
        text: `Maintenance of ${formatINRFull(s.pending_due)} is due${s.next_due_date ? ' on ' + trimDay(formatShortDate(s.next_due_date)) : ''}.`,
        cta: 'View dues',
        to: '/maintenance',
      } : null,
    }
  }

  return base
})

const metrics = computed(() => roleData.value.metrics)
const quickActions = computed(() => roleData.value.quickActions)
const actionCard = computed(() => roleData.value.actionCard)

const feed = computed(() => ({
  title: roleData.value.feedTitle,
  rows: roleData.value.feed,
}))

function goToFeed() {
  router.push(roleData.value.feedRoute)
}

function goTo(path) {
  router.push(path)
}
</script>

<template>
  <div class="dashboard">

    <div class="welcome-line">
      <span>Good day, <strong>{{ auth.name }}</strong></span>
      <span class="welcome-sub">Here is what is happening in Raghvendra Sai Society</span>
    </div>

    <div v-if="activeEmergency" class="emergency-banner" @click="goTo('/emergency')">
      <span class="emergency-icon">🚨</span>
      <div class="emergency-content">
        <span class="emergency-title">
          Active emergency<span v-if="activeEmergencyCount > 1"> · {{ activeEmergencyCount }} alerts</span>
        </span>
        <span class="emergency-text">{{ activeEmergency.message }}</span>
        <span class="emergency-meta">
          {{ activeEmergency.created_by_name || 'Unknown' }} · {{ formatAlertTime(activeEmergency.created_at) }}
        </span>
      </div>
      <span class="emergency-cta">View →</span>
    </div>

    <div class="metrics-grid">
      <MetricCard v-for="m in metrics" :key="m.label" :label="m.label" :value="m.value" :sub="m.sub" :icon="m.icon"
        :tint="m.tint" />
    </div>

    <div class="main-grid">


      <div class="feed-panel" v-if="feed.title">
        <div class="feed-header">
          <span class="feed-title">{{ feed.title }}</span>
          <button class="view-all-btn" @click="goToFeed">
            View all →
          </button>
        </div>
        <TransitionGroup v-if="feed.rows.length" name="feed-row" tag="div" class="feed-list">
          <div v-for="(row, i) in feed.rows" :key="row.id ?? row.tag" class="feed-row-wrap"
            :style="{ '--row-delay': `${i * 40}ms` }">
            <div class="feed-row">
              <div class="feed-tag">{{ row.tag }}</div>
              <div class="feed-content">
                <span class="feed-title-text">{{ row.title }}</span>
                <span class="feed-meta">{{ row.meta }}</span>
              </div>
              <span :class="['feed-chip', row.statusClass]">{{ row.status }}</span>
              <button class="feed-toggle-btn" :class="{ open: expandedComplaint === row.id }"
                @click="toggleComplaint(row.id)" aria-label="Show complaint details">
                ▾
              </button>
            </div>
            <Transition name="shutter">
              <div class="feed-shutter" v-if="expandedComplaint === row.id">
                <p class="feed-shutter-text">{{ row.description }}</p>
              </div>
            </Transition>
          </div>
        </TransitionGroup>
        <div class="feed-empty" v-else>
          <span class="feed-empty-icon">📭</span>
          <span class="feed-empty-text">No complaints yet</span>
        </div>
      </div>

      <div class="side-panel">

        <div class="action-card" v-if="actionCard">
          <span class="action-label">{{ actionCard.label }}</span>
          <p class="action-text">{{ actionCard.text }}</p>
          <button class="action-cta" @click="goTo(actionCard.to)">
            {{ actionCard.cta }}
          </button>
        </div>

        <div class="quick-actions-card" v-if="quickActions.length">
          <span class="qa-title">Quick actions</span>
          <div class="qa-list">
            <button v-for="qa in quickActions" :key="qa.label" class="qa-btn" @click="goTo(qa.to)">
              <span class="qa-icon">{{ qa.icon }}</span>
              {{ qa.label }}
            </button>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.dashboard {
  max-width: var(--content-max-width);
}

.welcome-line {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 22px;
}

.welcome-line span {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
}

.welcome-line strong {
  color: var(--color-text-primary);
}

.welcome-sub {
  font-size: var(--font-size-sm) !important;
  color: var(--color-text-muted) !important;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(212px, 1fr));
  gap: 16px;
  margin-bottom: 22px;
}

.main-grid {
  display: grid;
  grid-template-columns: 1.55fr 1fr;
  gap: 18px;
  align-items: start;
}

.feed-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-xs);
  min-width: 0;
  min-height: 280px;
  display: flex;
  flex-direction: column;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.feed-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
}

.view-all-btn {
  font-size: var(--font-size-sm);
  color: var(--c-800);
  font-weight: 700;
  transition: color var(--transition-fast), transform 0.15s ease;
}


.view-all-btn:hover {
  color: var(--c-900);
  transform: translateX(2px);
}


.feed-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.feed-row-wrap {
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  animation: row-in 0.35s ease-out both;
  animation-delay: var(--row-delay, 0ms);
}
@keyframes row-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.feed-row-wrap:last-child {
  border-bottom: none;
}

.feed-row {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  padding: 12px 6px;
  border-radius: var(--radius-md);
  transition: background 0.18s ease;
}


.feed-row:hover {
  background: var(--color-surface-soft);
}


.feed-toggle-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: 14px;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), background var(--transition-fast), color var(--transition-fast);
}


.feed-toggle-btn:hover {
  background: var(--color-surface-soft);
  color: var(--c-800);
}


.feed-toggle-btn.open {
  transform: rotate(180deg);
  color: var(--c-800);
}

.feed-shutter {
  padding: 0 6px 14px 61px;
  overflow: hidden;
}
.shutter-enter-active,
.shutter-leave-active {
  transition: max-height 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease;
  max-height: 120px;
}
.shutter-enter-from,
.shutter-leave-to {
  max-height: 0;
  opacity: 0;
}


.feed-row-move {
  transition: transform 0.25s ease;
}


.feed-shutter-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  background: var(--color-surface-soft);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.feed-tag {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: #EAF6FB;
  color: var(--c-800);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-xs);
}


.feed-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted);
}


.feed-empty-icon {
  font-size: 26px;
  opacity: 0.6;
}

.feed-empty-text {
  font-size: var(--font-size-md);
  font-weight: 600;
}

.feed-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-title-text {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: normal;
  overflow-wrap: break-word;
  word-break: break-word;
}

.feed-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.feed-chip {
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
  transition: background 0.18s ease, color 0.18s ease, transform 0.15s ease;
}


.feed-row:hover .feed-chip {
  transform: scale(1.04);
}

.feed-chip.in_progress {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.feed-chip.completed {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.feed-chip.assigned {
  background: var(--color-info-bg);
  color: var(--color-info-text);
}

.feed-chip.high {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}


.side-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.action-card {
  background: linear-gradient(155deg, var(--c-900), var(--c-800));
  border-radius: var(--radius-lg);
  padding: 20px;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-label {
  font-size: var(--font-size-sm);
  opacity: 0.7;
  font-weight: 600;
}

.action-text {
  font-size: var(--font-size-md);
  font-weight: 700;
  line-height: 1.4;
}

.action-cta {
  align-self: flex-start;
  margin-top: 6px;
  padding: 9px 16px;
  border-radius: var(--radius-md);
  background: var(--c-100);
  color: var(--c-900);
  font-size: var(--font-size-sm);
  font-weight: 700;
  transition: opacity var(--transition-fast);
}


.action-cta:hover {
  opacity: 0.85;
}


.quick-actions-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
  box-shadow: var(--shadow-xs);
}

.qa-title {
  display: block;
  font-size: var(--font-size-md);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 12px;
}

.qa-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.qa-btn {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: left;
  transition: background var(--transition-fast);
}

.qa-btn:hover {
  background: #E9F4FA;
  color: var(--c-800);
}

.qa-icon {
  font-size: 16px;
  color: var(--c-500);
}

.security-note {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 28px;
  text-align: center;
  box-shadow: var(--shadow-xs);
}

.security-note p {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  margin-bottom: 20px;
}

.security-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.sec-action-btn {
  height: 42px;
  padding: 0 20px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}


.sec-action-btn:hover {
  background: var(--c-900);
}

.emergency-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  margin-bottom: 22px;
  cursor: pointer;
  transition: box-shadow var(--transition-fast);
}

.emergency-banner:hover {
  box-shadow: var(--shadow-sm);
}

.emergency-icon {
  font-size: 26px;
  flex-shrink: 0;
}

.emergency-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.emergency-title {
  font-size: var(--font-size-sm);
  font-weight: 800;
  color: var(--color-danger-text);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.emergency-text {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.emergency-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.emergency-cta {
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-danger-text);
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
