<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppNavbar from './components/layout/AppNavbar.vue'
import AppChatWidget from './components/layout/AppChatWidget.vue'

const route = useRoute()
const auth = useAuthStore()

// login page has no sidebar or navbar
const showLayout = computed(() => {
  return !['login', 'landing'].includes(route.name)
})
</script>

<template>
  <div class="app">
    <Transition name="layout-fade" mode="out-in">
      <router-view v-if="!showLayout" key="no-layout" />

      <div v-else key="layout" class="app-shell">
        <AppSidebar />
        <div class="app-body">
          <AppNavbar />
          <main class="app-content">
            <router-view /> <!-- current page renders -->
          </main>
        </div>
        <AppChatWidget />
      </div>
    </Transition>
  </div>
</template>

<style>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

.app-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.layout-fade-enter-active,
.layout-fade-leave-active {
  transition: opacity 0.15s ease;
}
.layout-fade-enter-from,
.layout-fade-leave-to {
  opacity: 0;
}

.app > .login-shell {
  flex: 1;
  width: 100%;
}

.app-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: var(--sidebar-width);
  min-height: 100vh;
  transition: margin-left var(--transition-base);
}

.app-content {
  flex: 1;
  padding: var(--content-padding);
  overflow-y: auto;
}
</style>