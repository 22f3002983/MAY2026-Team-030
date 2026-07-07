<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppNavbar from './components/layout/AppNavbar.vue'

const route = useRoute()
const auth = useAuthStore()

// login page has no sidebar or navbar
const showLayout = computed(() => route.name !== 'login')
</script>

<template>
  <div class="app">

    <!-- login page - no layout wrapper -->
    <router-view v-if="!showLayout" />

    <!-- all other pages - with sidebar and navbar -->
    <template v-else>
      <AppSidebar />
      <div class="app-body">
        <AppNavbar />
        <main class="app-content">
          <router-view /> <!-- current page renders -->
        </main>
      </div>
    </template>

  </div>
</template>

<style>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
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