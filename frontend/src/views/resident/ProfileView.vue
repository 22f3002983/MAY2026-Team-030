<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/axios'
import { digitsOnly, toStoredPhone, extractDigits, formatPhoneDisplay } from '../../utils/phone'

const auth = useAuthStore()

const isEditing  = ref(false)
const successMsg = ref('')

const profile = ref({
  name: '', flat: '', email: '', phone: '', members: '',
  vehicle1: '', vehicle1_no: '', vehicle2: '', vehicle2_no: '',
  occupant_type: '',
})

async function loadProfile() {
  const res = await api.get('/auth/me')
  const u = res.data.user
  profile.value = {
    name: u.name,
    flat: u.flat_number || '',
    email: u.email,
    phone: u.phone,
    members: u.household_size,
    vehicle1: u.vehicle1_name || '',
    vehicle1_no: u.vehicle1_number || '',
    vehicle2: u.vehicle2_name || '',
    vehicle2_no: u.vehicle2_number || '',
    occupant_type: u.occupant_type,
  }
}

onMounted(loadProfile)


// editable copy — only committed on save
const draft = ref({ ...profile.value })

const initials = computed(() =>
  profile.value.name.split(' ').map(w => w[0]).join('').toUpperCase()
)

function startEdit() {
  draft.value  = { ...profile.value }
  phoneDigits.value = extractDigits(profile.value.phone)
  saveError.value = ''
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

const phoneDigits = ref('')
const saveError = ref('')

function onPhoneInput(e) {
  phoneDigits.value = digitsOnly(e.target.value)
}

async function saveEdit() {
  saveError.value = ''
  if (phoneDigits.value.length !== 10) {
    saveError.value = 'Enter a valid 10-digit phone number'
    return
  }
  try {
    await api.patch('/profile', {
      name: draft.value.name,
      phone: toStoredPhone(phoneDigits.value),
      household_size: draft.value.members,
      vehicle1_name: draft.value.vehicle1,
      vehicle1_number: draft.value.vehicle1_no,
      vehicle2_name: draft.value.vehicle2,
      vehicle2_number: draft.value.vehicle2_no,
    })
    await loadProfile()
    isEditing.value = false
    successMsg.value = 'Profile updated successfully.'
    setTimeout(() => successMsg.value = '', 5000)
  } catch (err) {
    saveError.value = err.response?.data?.error || 'Could not save changes'
  }
}

const showPasswordForm  = ref(false)
const changingPassword  = ref(false)
const pwError   = ref('')
const pwSuccess = ref('')
const pwForm = ref({ current_password: '', new_password: '', confirm_password: '' })

function togglePasswordForm() {
  showPasswordForm.value = !showPasswordForm.value
  pwForm.value = { current_password: '', new_password: '', confirm_password: '' }
  pwError.value = ''
  pwSuccess.value = ''
}

async function changePassword() {
  pwError.value = ''

  if (!pwForm.value.current_password || !pwForm.value.new_password) {
    pwError.value = 'Current and new password are required'
    return
  }
  if (pwForm.value.new_password.length < 6) {
    pwError.value = 'New password must be at least 6 characters'
    return
  }
  if (pwForm.value.new_password !== pwForm.value.confirm_password) {
    pwError.value = 'New passwords do not match'
    return
  }

  changingPassword.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: pwForm.value.current_password,
      new_password:      pwForm.value.new_password,
    })
    pwSuccess.value = 'Password updated successfully.'
    pwForm.value = { current_password: '', new_password: '', confirm_password: '' }
    setTimeout(() => {
      showPasswordForm.value = false
      pwSuccess.value = ''
    }, 2000)
  } catch (err) {
    pwError.value = err.response?.data?.error || 'Could not change password'
  } finally {
    changingPassword.value = false
  }
}

const showEmailForm  = ref(false)
const changingEmail  = ref(false)
const emailError     = ref('')
const emailSuccess   = ref('')
const emailForm = ref({ new_email: '', current_password: '' })

function toggleEmailForm() {
  showEmailForm.value = !showEmailForm.value
  emailForm.value = { new_email: '', current_password: '' }
  emailError.value = ''
  emailSuccess.value = ''
}

async function changeEmail() {
  emailError.value = ''

  if (!emailForm.value.new_email || !emailForm.value.current_password) {
    emailError.value = 'New email and current password are required'
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailForm.value.new_email)) {
    emailError.value = 'Enter a valid email address'
    return
  }

  changingEmail.value = true
  try {
    await api.post('/auth/change-email', {
      new_email:         emailForm.value.new_email,
      current_password:  emailForm.value.current_password,
    })
    await loadProfile()
    emailSuccess.value = 'Email updated successfully.'
    emailForm.value = { new_email: '', current_password: '' }
    setTimeout(() => {
      showEmailForm.value = false
      emailSuccess.value = ''
    }, 2000)
  } catch (err) {
    emailError.value = err.response?.data?.error || 'Could not update email'
  } finally {
    changingEmail.value = false
  }
}

// fields grouped into logical sections instead of one flat grid —
// personal details vs vehicle details read very differently and were
// getting visually jumbled together before
const personalFields = computed(() => [
  { key: 'Full name',   value: profile.value.name,    field: 'name' },
  { key: 'Flat number', value: profile.value.flat,    field: 'flat' },
  { key: 'Email',       value: profile.value.email,   field: 'email' },
  { key: 'Phone',       value: formatPhoneDisplay(profile.value.phone) || profile.value.phone, field: 'phone' },
  { key: 'Members',     value: profile.value.members, field: 'members' },
])

const vehicleFields = computed(() => [
  { key: 'Vehicle 1 name',   value: profile.value.vehicle1,    field: 'vehicle1' },
  { key: 'Vehicle 1 number', value: profile.value.vehicle1_no, field: 'vehicle1_no' },
  { key: 'Vehicle 2 name',   value: profile.value.vehicle2,    field: 'vehicle2' },
  { key: 'Vehicle 2 number', value: profile.value.vehicle2_no, field: 'vehicle2_no' },
])

// email is read-only same as flat — it isn't part of the PATCH payload above
const readonlyFields = ['flat', 'email']
</script>

<template>
  <div class="profile-view">

    <div class="page-header">
      <div>
        <h2>Profile</h2>
        <p class="page-sub">Your account details and flat information</p>
      </div>
    </div>

    <transition name="fade">
      <div v-if="successMsg" class="success-banner">
        <span class="banner-icon">✓</span> {{ successMsg }}
      </div>
    </transition>

    <div class="two-col">

      <!-- left - avatar card -->
      <div class="avatar-card">
        <div class="avatar">{{ initials }}</div>
        <h3 class="profile-name">{{ profile.name }}</h3>
        <p class="profile-meta">{{ profile.flat }}</p>
        <span class="verified-badge">Verified resident</span>
        <button
          v-if="!isEditing"
          class="edit-btn"
          @click="startEdit"
        >
          Edit profile
        </button>
      </div>

      <!-- right - account details -->
      <div class="details-card">
        <div class="details-header">
          <span class="details-title">Account details</span>
          <div v-if="isEditing" class="edit-actions">
            <button class="cancel-btn" @click="cancelEdit">Cancel</button>
            <button class="save-btn" @click="saveEdit">Save changes</button>
          </div>
        </div>

        <!-- view mode -->
        <template v-if="!isEditing">
          <div class="fields-section">
            <span class="section-label">Personal</span>
            <div class="fields-grid">
              <div v-for="field in personalFields" :key="field.key" class="field-item">
                <span class="field-key">{{ field.key }}</span>
                <span class="field-value">{{ field.value || '—' }}</span>
              </div>
            </div>
          </div>

          <div class="fields-section">
            <span class="section-label">Vehicles</span>
            <div class="fields-grid">
              <div v-for="field in vehicleFields" :key="field.key" class="field-item">
                <span class="field-key">{{ field.key }}</span>
                <span class="field-value">{{ field.value || '—' }}</span>
              </div>
            </div>
          </div>
        </template>

        <!-- edit mode -->
        <template v-else>
          <div v-if="saveError" class="pw-error">{{ saveError }}</div>
          <div class="fields-section">
            <span class="section-label">Personal</span>
            <div class="edit-grid">
              <div v-for="field in personalFields" :key="field.field" class="edit-field">
                <label>{{ field.key }}</label>
                <div v-if="field.field === 'phone'" class="phone-input-group">
                  <span class="phone-prefix">+91</span>
                  <input
                    :value="phoneDigits"
                    @input="onPhoneInput"
                    type="text"
                    inputmode="numeric"
                    maxlength="10"
                    class="n-input phone-input"
                  />
                </div>
                <input
                  v-else
                  v-model="draft[field.field]"
                  :disabled="readonlyFields.includes(field.field)"
                  :class="['n-input', { 'n-disabled': readonlyFields.includes(field.field) }]"
                  type="text"
                />
              </div>
            </div>
          </div>

          <div class="fields-section">
            <span class="section-label">Vehicles</span>
            <div class="edit-grid">
              <div v-for="field in vehicleFields" :key="field.field" class="edit-field">
                <label>{{ field.key }}</label>
                <input v-model="draft[field.field]" class="n-input" type="text" />
              </div>
            </div>
          </div>
        </template>

        <!-- security — kept as a compact row rather than its own big card,
             the password form only expands what it actually needs -->
        <div class="fields-section security-section">
          <div class="security-row">
            <div>
              <span class="section-label">Security</span>
              <p class="security-sub">Change the password used to sign in</p>
            </div>
            <button v-if="!showPasswordForm" class="link-action-btn" @click="togglePasswordForm">
              Change password
            </button>
          </div>

          <div v-if="showPasswordForm" class="password-form">
            <div v-if="pwError" class="pw-error">{{ pwError }}</div>
            <div v-if="pwSuccess" class="pw-success">✓ {{ pwSuccess }}</div>

            <div class="edit-grid">
              <div class="edit-field">
                <label>Current password</label>
                <input v-model="pwForm.current_password" type="password" class="n-input" autocomplete="current-password" />
              </div>
              <div class="edit-field">
                <label>New password</label>
                <input v-model="pwForm.new_password" type="password" class="n-input" autocomplete="new-password" />
              </div>
              <div class="edit-field">
                <label>Confirm new password</label>
                <input v-model="pwForm.confirm_password" type="password" class="n-input" autocomplete="new-password" />
              </div>
            </div>

            <div class="edit-actions pw-actions">
              <button class="cancel-btn" @click="togglePasswordForm">Cancel</button>
              <button class="save-btn" :disabled="changingPassword" @click="changePassword">
                {{ changingPassword ? 'Saving…' : 'Update password' }}
              </button>
            </div>
          </div>

          <div class="security-row security-row-divider">
            <div>
              <span class="section-label">Email</span>
              <p class="security-sub">Update the email used to sign in</p>
            </div>
            <button v-if="!showEmailForm" class="link-action-btn" @click="toggleEmailForm">
              Change email
            </button>
          </div>

          <div v-if="showEmailForm" class="password-form">
            <div v-if="emailError" class="pw-error">{{ emailError }}</div>
            <div v-if="emailSuccess" class="pw-success">✓ {{ emailSuccess }}</div>

            <div class="edit-grid">
              <div class="edit-field">
                <label>New email</label>
                <input v-model="emailForm.new_email" type="email" class="n-input" autocomplete="email" />
              </div>
              <div class="edit-field">
                <label>Current password</label>
                <input v-model="emailForm.current_password" type="password" class="n-input" autocomplete="current-password" />
              </div>
            </div>

            <div class="edit-actions pw-actions">
              <button class="cancel-btn" @click="toggleEmailForm">Cancel</button>
              <button class="save-btn" :disabled="changingEmail" @click="changeEmail">
                {{ changingEmail ? 'Saving…' : 'Update email' }}
              </button>
            </div>
          </div>
        </div>

      </div>

    </div>

  </div>
</template>

<style scoped>
.profile-view {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
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

.success-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 20px;
}

.banner-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-success-text);
  color: #fff;
  font-size: 11px;
  flex-shrink: 0;
}

.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-fast); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.two-col {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  align-items: start;
}

/* avatar card */
.avatar-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 32px 26px;
  box-shadow: var(--shadow-xs);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: sticky;
  top: 20px;
}

.avatar {
  width: 84px;
  height: 84px;
  border-radius: 22px;
  background: linear-gradient(150deg, var(--c-800), var(--c-500));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 4px;
}

.profile-name {
  font-size: var(--font-size-xl);
  font-weight: 800;
  color: var(--c-900);
  line-height: 1.3;
}

.profile-meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.verified-badge {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-success-text);
  background: #DDF3E7;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  margin-top: 6px;
  margin-bottom: 4px;
}

.edit-btn {
  width: 100%;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 10px;
  transition: background var(--transition-fast);
}

.edit-btn:hover { background: var(--c-900); }

/* details card */
.details-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 26px 28px;
  box-shadow: var(--shadow-xs);
}

.details-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-border);
}

.details-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
}

.edit-actions {
  display: flex;
  gap: 10px;
}

.cancel-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: background var(--transition-fast);
}

.cancel-btn:hover { background: var(--color-border); }

.save-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.save-btn:hover { background: var(--c-900); }

.save-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* field sections — separates "Personal" from "Vehicles" so the two
   groups of fields don't blur together in one big undifferentiated grid */
.fields-section + .fields-section {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid var(--color-border);
}

.section-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 800;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}

/* security section — a compact row, not a whole card of its own */
.security-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.security-row .section-label { margin-bottom: 4px; }

.security-row-divider {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--color-border);
}

.security-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.link-action-btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 6px;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--c-800);
  transition: color var(--transition-fast);
}

.link-action-btn:hover {
  color: var(--c-900);
  text-decoration: underline;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

.pw-actions {
  margin-top: 4px;
}

.pw-error {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.pw-success {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

/* view mode grid */
.fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px 32px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-key {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.field-value {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

/* edit mode grid */
.edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
}

.edit-field {
  display: flex;
  flex-direction: column;
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-bottom: 6px;
}

.n-input {
  width: 100%;
  height: 42px;
  padding: 0 13px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface-soft);
  color: var(--color-text-primary);
  outline: none;
  font-family: var(--font-family);
  transition: border-color var(--transition-fast);
}

.n-input:focus  { border-color: var(--c-600); }

.n-disabled {
  background: var(--color-bg);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.phone-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phone-prefix {
  height: 42px;
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

.phone-input {
  flex: 1;
}

@media (max-width: 720px) {
  .two-col {
    grid-template-columns: 1fr;
  }
  .avatar-card {
    position: static;
  }
  .fields-grid,
  .edit-grid {
    grid-template-columns: 1fr;
  }
}
</style>