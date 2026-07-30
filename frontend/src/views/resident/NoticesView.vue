<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api/axios' // adjust path if this file lives elsewhere

const searchQuery = ref('')
const filterTag   = ref('all')
const notices     = ref([])
const loading     = ref(true)
const loadError   = ref('')

const tags = ['all', 'General', 'Maintenance', 'Security', 'Event', 'Urgent']

const tagColors = {
  General:     { accent: '#49769F', tagBg: '#EAF0F4' },
  Maintenance: { accent: '#E0A030', tagBg: '#FBF1DE' },
  Security:    { accent: '#B4442F', tagBg: '#FBE9E4' },
  Event:       { accent: '#3AA06B', tagBg: '#E4F5ED' },
  Urgent:      { accent: '#C43D3D', tagBg: '#FBE9E4' },
}

async function fetchNotices() {
  loading.value   = true
  loadError.value = ''
  try {
    const params = {}
    if (filterTag.value !== 'all') params.tag = filterTag.value
    const res = await api.get('/notices', { params })
    notices.value = res.data.notices
  } catch (err) {
    loadError.value = err.response?.data?.error || 'Failed to load notices'
    console.error('Failed to load notices', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchNotices)

// re-fetch from the server when the tag filter changes, rather than
// filtering client-side — keeps behavior consistent with the backend's
// own relevance-based filtering (e.g. residents only seeing their tower)
watch(filterTag, fetchNotices)

// search stays client-side since it's just narrowing what's already loaded
const filteredNotices = computed(() => {
  if (!searchQuery.value) return notices.value
  const q = searchQuery.value.toLowerCase()
  return notices.value.filter(n =>
    n.title.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q)
  )
})

function tagStyle(tag) {
  return tagColors[tag] || tagColors['General']
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="notices-view">

    <div class="page-header">
      <div>
        <h2>Notices</h2>
        <p class="page-sub">Society announcements and updates</p>
      </div>
    </div>

    <!-- search + tag filters -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search notices..."
        class="search-input"
      />
      <div class="tag-filters">
        <button
          v-for="tag in tags"
          :key="tag"
          :class="['filter-btn', { active: filterTag === tag }]"
          @click="filterTag = tag"
        >
          {{ tag === 'all' ? 'All' : tag }}
        </button>
      </div>
    </div>

    <p v-if="loadError" class="error-msg">{{ loadError }}</p>

    <!-- notices list -->
    <div class="notices-list">
      <div v-if="loading" class="empty-state">
        <p>Loading notices...</p>
      </div>

      <template v-else>
        <div
          v-for="notice in filteredNotices"
          :key="notice.id"
          class="notice-card"
        >
          <div
            class="notice-accent"
            :style="{ background: tagStyle(notice.tag).accent }"
          ></div>

          <div class="notice-body">
            <div class="notice-meta">
              <span
                class="notice-tag"
                :style="{
                  color: tagStyle(notice.tag).accent,
                  background: tagStyle(notice.tag).tagBg
                }"
              >
                {{ notice.tag }}
              </span>
              <span class="notice-date">{{ formatDate(notice.created_at) }}</span>
              <span class="notice-expiry">Expires {{ formatDate(notice.expiry_date) }}</span>
            </div>
            <h3 class="notice-title">{{ notice.title }}</h3>
            <p class="notice-text">{{ notice.description }}</p>
          </div>

        </div>

        <div v-if="filteredNotices.length === 0" class="empty-state">
          <p>No notices found</p>
          <span>Try a different search or tag filter</span>
        </div>
      </template>
    </div>

  </div>
</template>

<style scoped>
.notices-view {
  max-width: var(--content-max-width);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
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

.toolbar {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
}

.search-input:focus { border-color: var(--c-600); }

.tag-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.filter-btn.active {
  background: var(--c-800);
  border-color: var(--c-800);
  color: #fff;
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-bottom: 14px;
}

.notices-list {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.notice-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  box-shadow: var(--shadow-xs);
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.notice-accent {
  width: 4px;
  flex-shrink: 0;
  border-radius: 4px;
  align-self: stretch;
}

.notice-body {
  flex: 1;
  min-width: 0;
}

.notice-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.notice-tag {
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
}

.notice-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.notice-expiry {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-left: auto;
}

.notice-title {
  font-size: var(--font-size-lg);
  font-weight: 800;
  color: var(--c-900);
  margin-bottom: 6px;
}

.notice-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-state p {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.empty-state span {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
</style>