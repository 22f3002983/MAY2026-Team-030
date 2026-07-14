<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth        = useAuthStore()
const showConfirm = ref(false)
const alertSent   = ref(false)

const contacts = [
  { label: 'Security — Gate 1',  num: '+91 91234 00001', icon: '🛡', tint: '#0A4174' },
  { label: 'Society Secretary',  num: '+91 98765 40002', icon: '👤', tint: '#4E8EA2' },
  { label: 'Ambulance',          num: '108',             icon: '📞', tint: '#C43D3D' },
  { label: 'Fire Brigade',       num: '101',             icon: '🚨', tint: '#E0A030' },
]

function triggerSOS() {
  showConfirm.value = true
}

function confirmSOS() {
  showConfirm.value = false
  alertSent.value   = true
  setTimeout(() => alertSent.value = false, 5000)
}
</script>

<template>
  <div class="emergency-view">

    <div class="page-header">
      <div>
        <h2>Emergency</h2>
        <p class="page-sub">Alert security and the secretary instantly</p>
      </div>
    </div>

    <!-- alert sent banner -->
    <div v-if="alertSent" class="alert-banner">
      🚨 SOS sent — Security and the secretary have been notified. Help is on the way.
    </div>

    <div class="two-col">

      <!-- left - SOS button -->
      <div class="sos-panel">
        <h3 class="sos-title">Emergency SOS</h3>
        <p class="sos-sub">
          Press to alert security and the secretary with your flat number instantly.
        </p>

        <div class="sos-btn-wrap">
          <button class="sos-btn" @click="triggerSOS">
            SOS
          </button>
        </div>

        <p class="sos-flat">Flat A-402 · {{ auth.name }}</p>
      </div>

      <!-- right - emergency contacts -->
      <div class="contacts-panel">
        <h3 class="contacts-title">Emergency contacts</h3>
        <div class="contacts-list">
          <div
            v-for="contact in contacts"
            :key="contact.label"
            class="contact-card"
          >
            <div class="contact-icon" :style="{ background: contact.tint }">
              {{ contact.icon }}
            </div>
            <div class="contact-info">
              <span class="contact-label">{{ contact.label }}</span>
              <span class="contact-num">{{ contact.num }}</span>
            </div>
            <a :href="'tel:' + contact.num" class="call-btn">📞</a>
          </div>
        </div>
      </div>

    </div>

    <!-- confirm modal -->
    <div v-if="showConfirm" class="modal-overlay" @click.self="showConfirm = false">
      <div class="confirm-modal">

        <div class="confirm-icon">🚨</div>
        <h3 class="confirm-title">Send emergency alert?</h3>
        <p class="confirm-sub">
          This will immediately notify <strong>security and the secretary</strong>
          with your flat number. Use only for genuine emergencies.
        </p>

        <div class="confirm-preview">
          SOS triggered by {{ auth.name }} — Flat A-402. Please respond immediately.
        </div>

        <div class="confirm-actions">
          <button class="cancel-btn" @click="showConfirm = false">Cancel</button>
          <button class="send-btn" @click="confirmSOS">Yes, send now</button>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.emergency-view {
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

.alert-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  font-size: var(--font-size-md);
  font-weight: 600;
  margin-bottom: 20px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: start;
}

/* SOS panel */
.sos-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 30px;
  box-shadow: var(--shadow-xs);
  text-align: center;
}

.sos-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 8px;
}

.sos-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 28px;
  max-width: 300px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.5;
}

.sos-btn-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 22px;
}

.sos-btn {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #E8756F, #C43D3D);
  color: #fff;
  font-size: var(--font-size-2xl);
  font-weight: 800;
  box-shadow: 0 12px 30px rgba(196,61,61,0.35);
  animation: pulse 2s infinite;
  transition: opacity var(--transition-fast);
}

.sos-btn:hover { opacity: 0.9; }

@keyframes pulse {
  0%   { box-shadow: 0 12px 30px rgba(196,61,61,0.35); }
  50%  { box-shadow: 0 12px 46px rgba(196,61,61,0.55); }
  100% { box-shadow: 0 12px 30px rgba(196,61,61,0.35); }
}

.sos-flat {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* contacts panel */
.contacts-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.contacts-title {
  font-size: var(--font-size-md);
  font-weight: 800;
  color: var(--c-900);
}

.contacts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contact-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  gap: 14px;
}

.contact-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
}

.contact-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.contact-label {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-text-primary);
}

.contact-num {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.call-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: #E9F4FA;
  color: var(--c-800);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  text-decoration: none;
  transition: background var(--transition-fast);
}

.call-btn:hover { background: #D4EBF7; }

/* confirm modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,29,57,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.confirm-modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: 28px;
  width: 100%;
  max-width: 420px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.confirm-icon {
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background: #FBE9E4;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.confirm-title {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--c-900);
}

.confirm-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.confirm-preview {
  width: 100%;
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 13px 15px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  text-align: left;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 12px;
  width: 100%;
  margin-top: 4px;
}

.cancel-btn {
  flex: 1;
  height: 46px;
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.cancel-btn:hover { background: var(--color-border); }

.send-btn {
  flex: 1;
  height: 46px;
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, #D45B5B, #B43333);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 800;
  box-shadow: 0 6px 16px rgba(196,61,61,0.3);
  transition: opacity var(--transition-fast);
}

.send-btn:hover { opacity: 0.9; }
</style>