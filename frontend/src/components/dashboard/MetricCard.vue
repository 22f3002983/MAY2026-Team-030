<script setup>
defineProps({
  label: String,
  value: String,
  sub:   String,
  icon:  String,
  tint:  String,
})
</script>

<template>
  <div class="metric-card">
    <div class="metric-top">
      <span class="metric-label">{{ label }}</span>
      <div class="metric-icon" :style="{ background: tint }">{{ icon }}</div>
    </div>
    <div class="metric-value">{{ value }}</div>
    <div class="metric-sub">{{ sub }}</div>
  </div>
</template>

<style scoped>
.metric-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
  box-shadow: var(--shadow-xs);
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.metric-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 600;
}

.metric-icon {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.metric-value {
  font-size: 29px;
  font-weight: 800;
  color: var(--c-900);
  margin-top: 12px;
  letter-spacing: -0.5px;
  line-height: 1;
}

.metric-sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 4px;
}
</style>