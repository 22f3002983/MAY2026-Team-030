<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import NotificationBell from './NotificationBell.vue'

const route = useRoute()
const auth = useAuthStore()

// convert route name to a readable page title
const pageTitle = computed(() => {
  const titles = {
    'dashboard':      'Dashboard',
    'my-complaints':  'My Complaints',
    'services-request':'Raise a Service Request',
    'amenities':      'Amenities',
    'notices':        'Notices',
    'visitors':       'Visitors',
    'emergency':      'Emergency',
    'maintenance':    'Maintenance',
    'documents':      'Documents',
    'profile':        'Profile',
    'sec-complaints': 'Complaints',
    'sec-vendors':    'Vendor Directory',
    'vendor-jobs':    'Vendor Jobs',
    'sec-notices':    'Notices',
    'sec-emergency':  'Emergency Broadcast',
    'sec-amenities':  'Amenities',
    'sec-residents':  'Residents',
    'sec-maintenance':'Maintenance & Dues',
    'sec-documents':  'Documents',
    'sec-funds':      'Society Funds',
    'sec-electricity':'Electricity Bills',
    'gate-dashboard': 'Gate Dashboard',
    'gate-emergency': 'Emergency Broadcast',
  }
  return titles[route.name] || 'Niwaas'
})
</script>

<template>
  <header class="navbar">

    <!-- left side - page title -->
    <div class="navbar-left">
      <h1 class="page-title">{{ pageTitle }}</h1>
      <span class="society-sub">Raghvendra Sai Society · Hyderabad</span>
    </div>

    <!-- right side - role badge + user name -->
    <div class="navbar-right">
      <span class="role-badge">{{ auth.role }}</span>
      <NotificationBell />
      <div class="navbar-user">
        <div class="navbar-avatar">{{ auth.name?.charAt(0) || 'U' }}</div>
        <span class="navbar-name">{{ auth.name }}</span>
      </div>
    </div>

  </header>
</template>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  height: var(--header-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--content-padding);
  z-index: var(--z-header);
  box-shadow: var(--shadow-xs);
}

.navbar-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.3px;
}

.society-sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.role-badge {
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-info-bg);
  color: var(--color-info-text);
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: capitalize;
}

.navbar-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.navbar-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--c-600);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: var(--font-size-sm);
}

.navbar-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}
</style>