<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const isEditing  = ref(false)
const successMsg = ref('')

const profile = ref({
  name:         'Ravi Kumar',
  flat:         'A-402, A Wing',
  email:        'ravi@raghvendrasai.in',
  phone:        '+91 98480 11771',
  members:      '4 (2 adults, 2 kids)',
  vehicle:      'TS09 AB 4402',
  occupant_type:'Owner',
})

// editable copy — only committed on save
const draft = ref({ ...profile.value })

const initials = computed(() =>
  profile.value.name.split(' ').map(w => w[0]).join('').toUpperCase()
)

function startEdit() {
  draft.value  = { ...profile.value }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

function saveEdit() {
  // placeholder - replace with API call in Sprint 1
  profile.value   = { ...draft.value }
  isEditing.value = false
  successMsg.value = 'Profile updated successfully. Changes are pending secretary approval.'
  setTimeout(() => successMsg.value = '', 5000)
}

const profileFields = computed(() => [
  { key: 'Full name',     value: profile.value.name,         field: 'name'         },
  { key: 'Flat number',   value: profile.value.flat,         field: 'flat'         },
  { key: 'Email',         value: profile.value.email,        field: 'email'        },
  { key: 'Phone',         value: profile.value.phone,        field: 'phone'        },
  { key: 'Members',       value: profile.value.members,      field: 'members'      },
  { key: 'Vehicle',       value: profile.value.vehicle,      field: 'vehicle'      },
])
</script>

<template>
  <div class="profile-view">

    <div class="page-header">
      <div>
        <h2>Profile</h2>
        <p class="page-sub">Your account details and flat information</p>
      </div>
    </div>

    <div v-if="successMsg" class="success-banner">
      ✓ {{ successMsg }}
    </div>

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
        <div v-if="!isEditing" class="fields-grid">
          <div
            v-for="field in profileFields"
            :key="field.key"
            class="field-item"
          >
            <span class="field-key">{{ field.key }}</span>
            <span class="field-value">{{ field.value }}</span>
          </div>
        </div>

        <!-- edit mode -->
        <div v-else class="edit-grid">
          <div
            v-for="field in profileFields"
            :key="field.field"
            class="edit-field"
          >
            <label>{{ field.key }}</label>
            <input
              v-model="draft[field.field]"
              :disabled="field.field === 'flat'"
              :class="['n-input', { 'n-disabled': field.field === 'flat' }]"
              type="text"
            />
          </div>
        </div>

        <div v-if="isEditing" class="edit-note">
          Profile changes require secretary approval before they take effect.
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
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 20px;
}

.two-col {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  align-items: start;
}

/* avatar card */
.avatar-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 26px;
  box-shadow: var(--shadow-xs);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.avatar {
  width: 88px;
  height: 88px;
  border-radius: 24px;
  background: linear-gradient(150deg, var(--c-800), var(--c-500));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 800;
  margin-bottom: 6px;
}

.profile-name {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--c-900);
}

.profile-meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.verified-badge {
  display: inline-flex;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-success-text);
  background: #DDF3E7;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  margin-top: 4px;
}

.edit-btn {
  width: 100%;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 12px;
  transition: background var(--transition-fast);
}

.edit-btn:hover { background: var(--c-900); }

/* details card */
.details-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-xs);
}

.details-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
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
  height: 36px;
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
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.save-btn:hover { background: var(--c-900); }

/* view mode grid */
.fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 28px;
}

.field-item {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
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
  gap: 4px 16px;
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
  margin-top: 12px;
  margin-bottom: 5px;
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

.edit-note {
  margin-top: 16px;
  padding: 10px 14px;
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  line-height: 1.5;
}
</style>