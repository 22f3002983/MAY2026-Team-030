<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();

const selectedRole = ref("resident");
const email = ref("");
const password = ref("");
const inviteCode = ref("");
const needsInviteCode = ref(false);
const error = ref("");
const loading = ref(false);

const roles = [
  { value: "resident", label: "Resident" },
  { value: "secretary", label: "Secretary" },
  { value: "security", label: "Security" },
];

async function login() {
  error.value = "";
  loading.value = true;

  if (!email.value || !password.value) {
    error.value = "Please enter your email and password";
    loading.value = false;
    return;
  }

  if (needsInviteCode.value && !inviteCode.value) {
    error.value = "Please enter your invite code";
    loading.value = false;
    return;
  }

  try {
    const user = await auth.login(email.value, password.value, inviteCode.value || null);

    if (user.role === "security") {
      router.push("/gate/dashboard");
    } else {
      router.push("/dashboard");
    }
  } catch (err) {
    const backendError = err.response?.data?.error;

    if (backendError === "invite_code_required") {
      needsInviteCode.value = true;
      error.value = err.response.data.message;
    } else if (err.response?.status === 401) {
      error.value = "Invalid email or password";
    } else if (err.response?.status === 400) {
      error.value = backendError || "Invalid invite code";
    } else {
      error.value = "Something went wrong. Please try again.";
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <!-- left panel -->
    <div class="login-left">
      <div class="login-logo">
        <div class="logo-mark">N</div>
        <div>
          <div class="logo-name">Niwaas</div>
          <div class="logo-sub">Society OS</div>
        </div>
      </div>

      <div class="login-hero">
        <div class="society-pill">Raghvendra Sai Society · Hyderabad</div>
        <h1>Your society,<br />running itself.</h1>
        <p class="tagline">"Dial a Secretary… Not Anymore."</p>
        <ul class="feature-list">
          <li>Raise and track complaints instantly</li>
          <li>Book amenities and pre-register visitors</li>
          <li>One-tap emergency broadcast to security</li>
        </ul>
      </div>

      <div class="login-footer">© 2026 Niwaas</div>
    </div>

    <!-- right panel - form -->
    <div class="login-right">
      <div class="login-form">
        <h2>Welcome back</h2>
        <p class="form-sub">Sign in to your society portal</p>

        <!-- role selector -->
        <div class="field-label">I am a</div>
        <div class="role-grid">
          <button
            v-for="r in roles"
            :key="r.value"
            :class="['role-btn', { active: selectedRole === r.value }]"
            @click="selectedRole = r.value"
          >
            {{ r.label }}
          </button>
        </div>

        <!-- email -->
        <label>Email address</label>
        <input
          v-model="email"
          type="email"
          placeholder="you@society.com"
          class="n-input"
        />

        <!-- password -->
        <label>Password</label>
        <input
          v-model="password"
          type="password"
          placeholder="••••••••"
          class="n-input"
        />

        <!-- invite code — only shown once the backend tells us it's needed -->
        <template v-if="needsInviteCode">
          <label>Invite code</label>
          <input
            v-model="inviteCode"
            type="text"
            placeholder="e.g. NW-7XQ2A"
            class="n-input"
            style="text-transform: uppercase"
          />
        </template>

        <!-- error message -->
        <p v-if="error" class="error-msg">{{ error }}</p>

        <!-- submit -->
        <button class="btn-primary" @click="login" :disabled="loading">
          {{
            loading
              ? "Signing in..."
              : "Sign in as " +
                roles.find((r) => r.value === selectedRole)?.label
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-shell {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  min-height: 100vh;
}

.login-left {
  background: linear-gradient(
    155deg,
    var(--c-900) 0%,
    var(--c-800) 52%,
    var(--c-600) 100%
  );
  color: #fff;
  padding: 52px 58px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.login-logo {
  display: flex;
  align-items: center;
  gap: 13px;
}

.logo-mark {
  width: 46px;
  height: 46px;
  border-radius: var(--radius-lg);
  background: linear-gradient(150deg, var(--c-100), var(--c-500));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-900);
  font-weight: 800;
  font-size: 20px;
}

.logo-name {
  font-size: var(--font-size-3xl);
  font-weight: 800;
  letter-spacing: -0.5px;
}

.logo-sub {
  font-size: var(--font-size-xs);
  opacity: 0.7;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.society-pill {
  display: inline-block;
  padding: 6px 13px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.1);
  font-size: var(--font-size-sm);
  font-weight: 600;
  margin-bottom: 22px;
}

h1 {
  font-size: var(--font-size-hero);
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -1px;
  margin: 0 0 16px;
}

.tagline {
  font-size: var(--font-size-lg);
  opacity: 0.82;
  font-style: italic;
  margin: 0 0 26px;
}

.feature-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 13px;
  font-size: var(--font-size-md);
  opacity: 0.9;
}

.feature-list li::before {
  content: "✓  ";
  font-weight: 700;
  color: var(--c-100);
}

.login-footer {
  font-size: var(--font-size-xs);
  opacity: 0.55;
}

.login-right {
  background: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 30px;
}

.login-form {
  width: 100%;
  max-width: 392px;
}

h2 {
  font-size: var(--font-size-4xl);
  font-weight: 800;
  letter-spacing: -0.6px;
  color: var(--c-900);
}

.form-sub {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  margin: 6px 0 24px;
}

.field-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 9px;
}

.role-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 9px;
  margin-bottom: 20px;
}

.role-btn {
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-bg);
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.role-btn.active {
  border-color: var(--c-800);
  background: #e8f0fa;
  color: var(--c-800);
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-bottom: 6px;
  margin-top: 4px;
}

.n-input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  margin-bottom: 14px;
  outline: none;
  transition: border-color var(--transition-fast);
}

.n-input:focus {
  border-color: var(--c-600);
  background: #eaf6fb;
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-bottom: 10px;
}

.btn-primary {
  width: 100%;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-lg);
  font-weight: 700;
  box-shadow: var(--shadow-btn);
  transition: background var(--transition-fast);
  margin-top: 4px;
}

.btn-primary:hover {
  background: var(--c-900);
}

@media (max-width: 768px) {
  .login-shell {
    grid-template-columns: 1fr;
  }
  .login-left {
    display: none;
  }
}
</style>