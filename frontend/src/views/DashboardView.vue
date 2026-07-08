<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MetricCard from '../components/dashboard/MetricCard.vue'

const router = useRouter()
const auth = useAuthStore()

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
      { label: 'Open Complaints',   value: '2',        sub: '1 in progress',     icon: '⚠',  tint: '#78BDE9' },
      { label: 'Upcoming Bookings', value: '1',        sub: 'Clubhouse · 4 Jul', icon: '📅', tint: '#4E8EA2' },
      { label: 'Pending Dues',      value: '₹13,250',  sub: 'due 5 Jul',         icon: '💳', tint: '#E0A030' },
      { label: 'Latest Notice',     value: 'Water cut',sub: '2 Jul, 10 AM',      icon: '🔔', tint: '#49769F' },
    ],
    feedTitle: 'Your recent complaints',
    feed: [
      { tag: '043', title: 'Water leakage under kitchen sink', meta: 'Plumbing · 28 Jun',   status: 'In Progress', statusClass: 'in_progress' },
      { tag: '038', title: 'Ceiling fan not working',          meta: 'Electrical · 24 Jun', status: 'Resolved',    statusClass: 'completed'   },
      { tag: '031', title: 'Bathroom tiles cracked',           meta: 'Carpentry · 18 Jun',  status: 'Open',        statusClass: 'assigned'    },
      { tag: '025', title: 'Water pressure low in tap',        meta: 'Plumbing · 12 Jun',   status: 'Resolved',    statusClass: 'completed'   },
    ],
    quickActions: [
      { label: 'Raise a complaint',    icon: '⚠',  to: '/complaints/raise' },
      { label: 'Book an amenity',      icon: '📅', to: '/amenities'        },
      { label: 'Pre-register visitor', icon: '👤', to: '/visitors'         },
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
      { label: 'Open Complaints', value: '12',    sub: '+2 raised today',  icon: '⚠',  tint: '#78BDE9' },
      { label: 'Pending Dues',    value: '₹4.8L', sub: 'across 42 flats',  icon: '💳', tint: '#E0A030' },
      { label: 'Active Vendors',  value: '4',     sub: '5 categories',     icon: '🔧', tint: '#4E8EA2' },
      { label: 'Unread Notices',  value: '2',     sub: 'posted this week', icon: '🔔', tint: '#49769F' },
    ],
    feedTitle: 'Latest complaints',
    feed: [
      { tag: 'A4', title: 'Water leakage under kitchen sink', meta: 'Ravi Kumar · A-402',  status: 'High',   statusClass: 'high'        },
      { tag: 'B2', title: 'Main switch tripping repeatedly',  meta: 'Priya Menon · B-201', status: 'Medium', statusClass: 'in_progress' },
      { tag: 'C1', title: 'Bedroom door hinge broken',        meta: 'Arjun Nair · C-105',  status: 'Low',    statusClass: 'completed'   },
      { tag: 'D3', title: 'Low water pressure in bathroom',   meta: 'Sana Khan · D-303',   status: 'High',   statusClass: 'high'        },
    ],
    quickActions: [
      { label: 'Post a notice',       icon: '🔔', to: '/sec/notices'   },
      { label: 'Broadcast emergency', icon: '🚨', to: '/sec/emergency' },
      { label: 'Manage vendors',      icon: '🔧', to: '/sec/vendors'   },
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
      { label: 'Visitors Inside',   value: '18', sub: 'live count',     icon: '✓',  tint: '#4E8EA2' },
      { label: 'Awaiting Approval', value: '2',  sub: 'at the gate',    icon: '🛡', tint: '#E0A030' },
      { label: 'Pre-registered',    value: '27', sub: 'expected today', icon: '📅', tint: '#78BDE9' },
      { label: 'Deliveries',        value: '11', sub: 'today',          icon: '📦', tint: '#49769F' },
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
const roleData = computed(() => ROLE_CONFIG[auth.role] ?? ROLE_CONFIG.resident)

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

    <div class="main-grid">

      <div class="feed-panel" v-if="feed.rows.length">
        <div class="feed-header">
          <span class="feed-title">{{ feed.title }}</span>
          <button class="view-all-btn" @click="goToFeed">
            View all →
          </button>
        </div>
        <div class="feed-list">
          <div v-for="row in feed.rows" :key="row.tag" class="feed-row">
            <div class="feed-tag">{{ row.tag }}</div>
            <div class="feed-content">
              <span class="feed-title-text">{{ row.title }}</span>
              <span class="feed-meta">{{ row.meta }}</span>
            </div>
            <span :class="['feed-chip', row.statusClass]">{{ row.status }}</span>
          </div>
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
            <button
              v-for="qa in quickActions"
              :key="qa.label"
              class="qa-btn"
              @click="goTo(qa.to)"
            >
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
}

.feed-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-xs);
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
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-row {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 12px 6px;
  border-bottom: 1px solid var(--color-border);
}

.feed-row:last-child {
  border-bottom: none;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
}

.feed-chip.in_progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.feed-chip.completed   { background: var(--color-success-bg); color: var(--color-success-text); }
.feed-chip.assigned    { background: var(--color-info-bg);    color: var(--color-info-text);    }
.feed-chip.high        { background: var(--color-danger-bg);  color: var(--color-danger-text);  }

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.action-cta:hover { opacity: 0.85; }

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

.sec-action-btn:hover { background: var(--c-900); }
</style>
