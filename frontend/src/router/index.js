import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import LandingView from '@/views/LandingView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // public route - no login needed
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },

    // resident routes
    {
      path: "/dashboard",
      name: "dashboard",
      component: () => import("../views/DashboardView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: '/',
      name: 'landing',
      component: LandingView
    },

    {
      path: '/services',
      name: 'services-request',
      component: () => import('../views/resident/ServiceRequestView.vue'),
      meta: { requiresAuth: true, role: 'resident' }
    },
    {
      path: '/complaints',
      name: 'my-complaints',
      component: () => import('../views/resident/MyComplaintsView.vue'),
      meta: { requiresAuth: true, role: 'resident' }
    },
    {
      path: "/amenities",
      name: "amenities",
      component: () => import("../views/resident/AmenitiesView.vue"),
      meta: { requiresAuth: true, role: "resident" },
    },
    {
      path: "/notices",
      name: "notices",
      component: () => import("../views/resident/NoticesView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: '/emergency',
      name: 'emergency',
      component: () => import('../views/resident/EmergencyView.vue'),
      meta: { requiresAuth: true, role: 'resident' }
    },
    {
      path: '/visitors',
      name: 'visitors',
      component: () => import('../views/resident/VisitorPreRegView.vue'),
      meta: { requiresAuth: true, role: 'resident' }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/resident/ProfileView.vue'),
      meta: { requiresAuth: true, role: 'resident' }
    },
    {
      path: "/maintenance",
      name: "maintenance",
      component: () => import("../views/resident/MaintenanceDuesView.vue"),
      meta: { requiresAuth: true, role: "resident" },
    },
    {
      path: "/documents",
      name: "documents",
      component: () => import("../views/resident/DocumentsView.vue"),
      meta: { requiresAuth: true, role: "resident" },
    },

    // // secretary routes
    {
      path: '/sec/complaints',
      name: 'sec-complaints',
      component: () => import('../views/secretary/SecComplaintsView.vue'),
      meta: { requiresAuth: true, role: 'secretary' }
    },
    {
      path: "/sec/vendors",
      name: "sec-vendors",
      component: () => import("../views/secretary/VendorDirectoryView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },
    {
      path: "/sec/vendors/jobs",
      name: "vendor-jobs",
      component: () => import("../views/secretary/VendorJobsView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },
    {
      path: '/sec/emergency',
      name: 'sec-emergency',
      component: () => import('../views/secretary/SecEmergencyView.vue'),
      meta: { requiresAuth: true, role: 'secretary' }
    },
    {
      path: "/sec/notices",
      name: "sec-notices",
      component: () => import("../views/secretary/SecNoticesView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },
    {
      path: '/sec/amenities',
      name: 'sec-amenities',
      component: () => import('../views/secretary/SecAmenitiesView.vue'),
      meta: { requiresAuth: true, role: 'secretary' }
    },
    {
      path: '/sec/residents',
      name: 'sec-residents',
      component: () => import('../views/secretary/SecResidentsView.vue'),
      meta: { requiresAuth: true, role: 'secretary' }
    },
    {
      path: '/sec/maintenance',
      name: 'sec-maintenance',
      component: () => import('../views/secretary/SecMaintenanceView.vue'),
      meta: { requiresAuth: true, role: 'secretary' }
    },
    {
      path: "/sec/documents",
      name: "sec-documents",
      component: () => import("../views/secretary/SecDocumentsView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },
    {
      path: "/sec/funds",
      name: "sec-funds",
      component: () => import("../views/secretary/SecFundsView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },
    {
      path: "/sec/electricity",
      name: "sec-electricity",
      component: () => import("../views/secretary/ElectricityBillsView.vue"),
      meta: { requiresAuth: true, role: "secretary" },
    },

    // // security routes
    {
      path: "/gate/dashboard",
      name: "gate-dashboard",
      component: () => import("../views/security/SecurityDashboardView.vue"),
      meta: { requiresAuth: true, role: "security" },
    },
    {
      path: "/gate/emergency",
      name: "gate-emergency",
      component: () => import("../views/security/GateEmergencyView.vue"),
      meta: { requiresAuth: true },
    },

    // catch all - if route doesn't exist send back to login
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

// this runs before every route change
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  // must be awaited — restoreSession now verifies the session with the
  // backend (GET /auth/me) instead of just reading localStorage, so the
  // auth checks below need the resolved result, not a stale ref value.
  await auth.restoreSession()

  // not logged in + protected route → go to login
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: 'landing' })
    return
  }
  // logged in + wrong role for this route → go to correct home
  if (to.meta.role && to.meta.role !== auth.role) {
    next({ name: auth.role === 'security' ? 'gate-dashboard' : 'dashboard' })
    return
  }

  // already logged in + trying to visit login → go to correct home
  if (to.name === 'login' && auth.isLoggedIn) {
    next({ name: auth.role === 'security' ? 'gate-dashboard' : 'dashboard' })
    return
  }

  next()
});

export default router;