<script setup>
import { ref, computed } from 'vue'

const searchQuery = ref('')
const filterTag = ref('all')

const tags = ['all', 'General', 'Maintenance', 'Security', 'Event', 'Urgent']

const tagColors = {
  General:     { accent: '#49769F', tagBg: '#EAF0F4' },
  Maintenance: { accent: '#E0A030', tagBg: '#FBF1DE' },
  Security:    { accent: '#B4442F', tagBg: '#FBE9E4' },
  Event:       { accent: '#3AA06B', tagBg: '#E4F5ED' },
  Urgent:      { accent: '#C43D3D', tagBg: '#FBE9E4' },
}

// mock data - replace with API call in Sprint 1
const notices = ref([
  {
    id: 1,
    title: 'Water supply disruption on 5 July',
    body: 'Due to pipeline maintenance, water supply will be suspended from 10 AM to 4 PM on 5 July 2026. Please store water accordingly.',
    tag: 'Maintenance',
    relevance: 'all',
    date: '2 Jul',
    expiry_date: '6 Jul 2026',
  },
  {
    id: 2,
    title: 'New visitor gate-pass protocol',
    body: 'From 1 July, every visitor must carry a gate pass code. Please pre-register guests through the app before their arrival.',
    tag: 'Security',
    relevance: 'all',
    date: '26 Jun',
    expiry_date: '31 Jul 2026',
  },
  {
    id: 3,
    title: 'Society AGM scheduled for 15 July',
    body: 'The Annual General Meeting will be held in the Community Hall at 6 PM on 15 July 2026. Attendance is requested from all flat owners.',
    tag: 'Event',
    relevance: 'all',
    date: '20 Jun',
    expiry_date: '15 Jul 2026',
  },
  {
    id: 4,
    title: 'Gym temporarily closed',
    body: 'The gymnasium is closed for equipment maintenance until 10 July 2026. We regret the inconvenience.',
    tag: 'General',
    relevance: 'all',
    date: '18 Jun',
    expiry_date: '10 Jul 2026',
  },
])

const filteredNotices = computed(() => {
  return notices.value.filter(n => {
    const matchesSearch = !searchQuery.value
      || n.title.toLowerCase().includes(searchQuery.value.toLowerCase())
      || n.body.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesTag = filterTag.value === 'all' || n.tag === filterTag.value
    return matchesSearch && matchesTag
  })
})

function tagStyle(tag) {
  return tagColors[tag] || tagColors['General']
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

    <!-- notices list -->
    <div class="notices-list">
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
            <span class="notice-date">{{ notice.date }}, 2026</span>
            <span class="notice-expiry">Expires {{ notice.expiry_date }}</span>
          </div>
          <h3 class="notice-title">{{ notice.title }}</h3>
          <p class="notice-text">{{ notice.body }}</p>
        </div>

      </div>

      <div v-if="filteredNotices.length === 0" class="empty-state">
        <p>No notices found</p>
        <span>Try a different search or tag filter</span>
      </div>
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