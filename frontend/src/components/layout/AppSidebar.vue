<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const navItems = computed(() => {
  if (auth.role === 'resident') {
    return [
      { label: 'Dashboard',    icon: '⊞', to: '/dashboard' },
      { label: 'Complaints',   icon: '⚠', to: '/complaints' },
      { label: 'Amenities',    icon: '★', to: '/amenities' },
      { label: 'Notices',      icon: '🔔', to: '/notices' },
      { label: 'Visitors',     icon: '👤', to: '/visitors' },
      { label: 'Emergency',    icon: '🚨', to: '/emergency' },
      { label: 'Maintenance',  icon: '💳', to: '/maintenance' },
      { label: 'Documents',  icon: '📄', to: '/documents' },
      { label: 'Profile',      icon: '◉', to: '/profile' },
    ]
  }

  if (auth.role === 'secretary') {
    return [
      { label: 'Dashboard',    icon: '⊞', to: '/dashboard' },
      { label: 'Complaints',   icon: '⚠', to: '/sec/complaints' },
      { label: 'Notices',      icon: '🔔', to: '/sec/notices' },
      { label: 'Emergency',    icon: '🚨', to: '/sec/emergency' },
      { label: 'Maintenance',  icon: '💳', to: '/sec/maintenance' },
      { label: 'Residents',    icon: '👥', to: '/sec/residents' },
      { label: 'Documents',  icon: '📄', to: '/sec/documents' },
      { label: 'Amenities',  icon: '🏢', to: '/sec/amenities' },
      { label: 'Vendors',      icon: '🔧', to: '/sec/vendors' },
      { label: 'Vendor Jobs', icon: '📋', to: '/sec/vendors/jobs' },
    ]
  }

  if (auth.role === 'security') {
    return [
      { label: 'Dashboard', icon: '⊞', to: '/gate/dashboard' },
      { label: 'Notices',   icon: '🔔', to: '/notices'},
      { label: 'Emergency', icon: '🚨', to: '/gate/emergency' },
    ]
  }

  return []
})

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

function logout() {
  auth.logout()
  router.push('/')
}

function goHome() {
  if (auth.role === 'security') {
    router.push('/gate/dashboard')
  } else {
    router.push('/dashboard')
  }
}
</script>

<template>
  <aside class="sidebar">

    <!-- logo -->
    <div class="sidebar-logo" @click="goHome">
      <div class="logo-mark">N</div>
      <div class="logo-text">
        <span class="logo-name">Niwaas</span>
        <span class="logo-sub">Society OS</span>
      </div>
    </div>

    <!-- society name -->
    <div class="sidebar-society">
      Raghvendra Sai Society
    </div>

    <!-- nav links -->
    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :class="['nav-item', { active: isActive(item.to) }]"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- user info + logout at bottom -->
    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="user-avatar">{{ auth.name?.charAt(0) || 'U' }}</div>
        <div class="user-info">
          <span class="user-name">{{ auth.name }}</span>
          <span class="user-role">{{ auth.role }}</span>
        </div>
      </div>
      <button class="logout-btn" @click="logout">Sign out</button>
    </div>

  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--color-sidebar-bg);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sidebar);
  overflow-y: auto;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 16px;
  border-bottom: 1px solid var(--color-sidebar-border);
  cursor: pointer;
}

.logo-mark {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, var(--c-100), var(--c-500));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-900);
  font-weight: 800;
  font-size: 18px;
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-name {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--color-text-inverse);
  letter-spacing: -0.4px;
}

.logo-sub {
  font-size: var(--font-size-xs);
  color: var(--color-sidebar-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-society {
  padding: 10px 20px;
  font-size: var(--font-size-xs);
  color: var(--color-sidebar-muted);
  border-bottom: 1px solid var(--color-sidebar-border);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--color-sidebar-text);
  font-size: var(--font-size-md);
  font-weight: 500;
  transition: background var(--transition-fast);
  text-decoration: none;
}

.nav-item:hover {
  background: var(--color-sidebar-hover);
}

.nav-item.active {
  background: var(--color-sidebar-active);
  color: #fff;
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--color-sidebar-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--c-600);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: var(--font-size-md);
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-inverse);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: var(--font-size-xs);
  color: var(--color-sidebar-muted);
  text-transform: capitalize;
}

.logout-btn {
  width: 100%;
  padding: 9px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.07);
  color: var(--color-sidebar-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: background var(--transition-fast);
  text-align: center;
}

.logout-btn:hover {
  background: rgba(255,255,255,0.13);
}
</style>