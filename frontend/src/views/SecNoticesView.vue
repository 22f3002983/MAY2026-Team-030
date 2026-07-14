<script setup>
import { ref, computed } from 'vue'

const showForm = ref(false)
const searchQuery = ref('')
const filterTag = ref('all')

const showDeleteConfirm = ref(false)
const pendingDeleteId = ref(null)

const newNotice = ref({
  title: '',
  body: '',
  tag: 'General',
  relevance: 'all',
  expiry_date: '',
  priority: 'normal'
})

const formError = ref('')

const tags = ['General', 'Maintenance', 'Security', 'Event', 'Urgent', 'Expired']
const cat_tags = ['General', 'Maintenance', 'Security', 'Event']
const filterTags = ['all', ...tags]

const relevanceOptions = [
  { value: 'all',     label: 'All Residents' },
  { value: 'block_a', label: 'Block A Only'  },
  { value: 'block_b', label: 'Block B Only'  },
  { value: 'block_c', label: 'Block C Only'  },
]
const priorityOptions = [
  { value: 'normal',    label: 'Normal' },
  { value: 'urgent', label: 'Urgent' },
]

const tagColors = {
  General:     { accent: '#49769F', tagBg: '#EAF0F4' },
  Maintenance: { accent: '#E0A030', tagBg: '#FBF1DE' },
  Security:    { accent: '#B4442F', tagBg: '#FBE9E4' },
  Event:       { accent: '#3AA06B', tagBg: '#E4F5ED' },
  Urgent:      { accent: '#C43D3D', tagBg: '#FBE9E4' },
  Expired:     { accent: '#8A8A8A', tagBg: '#ECECEC' },
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
    is_active: true,
  },
  {
    id: 2,
    title: 'New visitor gate-pass protocol',
    body: 'From 1 July, every visitor must carry a gate pass code. Please pre-register guests through the app before their arrival.',
    tag: 'Security',
    relevance: 'all',
    date: '26 Jun',
    expiry_date: '31 Jul 2026',
    is_active: true,
  },
  {
    id: 3,
    title: 'Society AGM scheduled for 15 July',
    body: 'The Annual General Meeting will be held in the Community Hall at 6 PM on 15 July 2026. Attendance is requested from all flat owners.',
    tag: 'Event',
    relevance: 'all',
    date: '20 Jun',
    expiry_date: '15 Jul 2026',
    is_active: true,
  },
  {
    id: 4,
    title: 'Gym temporarily closed',
    body: 'The gymnasium is closed for equipment maintenance until 10 July 2026. We regret the inconvenience.',
    tag: 'General',
    relevance: 'all',
    date: '18 Jun',
    expiry_date: '10 Jul 2026',
    is_active: true,
  },
])

const filteredNotices = computed(() => {
  return notices.value.filter(n => {
    const matchesSearch = !searchQuery.value
      || n.title.toLowerCase().includes(searchQuery.value.toLowerCase())
      || n.body.toLowerCase().includes(searchQuery.value.toLowerCase())

    let matchesTag
    if (filterTag.value === 'Expired') {
      matchesTag = isExpired(n)
    } else if (filterTag.value === 'all') {
      matchesTag = !isExpired(n)
    } else {
      matchesTag = n.tag === filterTag.value && !isExpired(n)
    }

    return matchesSearch && matchesTag
  })
})

function isExpired(notice) {
  const expiry = new Date(notice.expiry_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return expiry < today
}

function postNotice() {
  formError.value = ''

  if (!newNotice.value.title || !newNotice.value.body || !newNotice.value.expiry_date) {
    formError.value = 'Title, body and expiry date are required'
    return
  }

  notices.value.unshift({
    id: notices.value.length + 1,
    ...newNotice.value,
    date: 'Today',
    is_active: true,
  })

  newNotice.value = { title: '', body: '', tag: 'General', relevance: 'all', priority: 'normal', expiry_date: '' }
  showForm.value = false
}

function confirmDeleteNotice(id) {
  pendingDeleteId.value = id
  showDeleteConfirm.value = true
}

function deleteNotice(id) {
  notices.value = notices.value.filter(n => n.id !== id)
  showDeleteConfirm.value = false
  pendingDeleteId.value = null
}

function tagStyle(tag) {
  return tagColors[tag] || tagColors['General']
}
</script>

<template>
  <div class="sec-notices">

    <div class="page-header">
      <div>
        <h2>Notices</h2>
        <p class="page-sub">{{ notices.length }} active notices posted</p>
      </div>
      <button class="btn-add" @click="showForm = true">+ Post a notice</button>
    </div>

    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search notices..."
        class="search-input"
      />
    </div>
    <div class="tag-filters">
        <button
          v-for="tag in filterTags"
          :key="tag"
          :class="['filter-btn', { active: filterTag === tag }]"
          @click="filterTag = tag"
        >
          {{ tag === 'all' ? 'All' : tag }}
        </button>
      </div>

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
            <span class="notice-relevance">{{ notice.relevance === 'all' ? 'All residents' : notice.relevance }}</span>
            <span class="notice-expiry">Expires {{ notice.expiry_date }}</span>
          </div>
          <h3 class="notice-title">{{ notice.title }}</h3>
          <p class="notice-text">{{ notice.body }}</p>
        </div>

        <button
          v-if="!isExpired(notice)"
          class="delete-btn"
          @click="confirmDeleteNotice(notice.id)"
        >✕</button>
      </div>

      <div v-if="filteredNotices.length === 0" class="empty-state">
        <p>No notices found</p>
      </div>
    </div>

    <!-- post notice modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal">

        <div class="modal-header">
          <h3>Post a Notice</h3>
          <button class="close-btn" @click="showForm = false">✕</button>
        </div>

        <div class="modal-body">
          <label>Title *</label>
          <input
            v-model="newNotice.title"
            type="text"
            placeholder="e.g. Water supply disruption on 5 July"
            class="n-input"
          />

          <label>Body *</label>
          <textarea
            v-model="newNotice.body"
            placeholder="Full notice details..."
            class="n-input n-textarea"
          />
          <div class="two-col">
            <div>
              <label>Tag</label>
              <select v-model="newNotice.tag" class="n-input">
                <option v-for="t in cat_tags" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div>
              <label>Priority</label>
              <select v-model="newNotice.priority" class="n-input">
                <option
                  v-for="p in priorityOptions"
                  :key="p.value"
                  :value="p.value"
                >
                  {{ p.label }}
                </option>
              </select>
            </div>
          </div>



          <div class="two-col">
            <div>
              <label>Relevance</label>
              <select v-model="newNotice.relevance" class="n-input">
                <option
                  v-for="r in relevanceOptions"
                  :key="r.value"
                  :value="r.value"
                >
                  {{ r.label }}
                </option>
              </select>
            </div>
            <div>
              <label>Expiry Date *</label>
              <input v-model="newNotice.expiry_date" type="date" class="n-input" />
            </div>
          </div>

          <p v-if="formError" class="error-msg">{{ formError }}</p>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showForm = false">Cancel</button>
          <button class="btn-primary" @click="postNotice">Post Notice</button>
        </div>

      </div>
    </div>

    <!-- delete confirmation modal -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>Delete Notice</h3>
          <button class="close-btn" @click="showDeleteConfirm = false">✕</button>
        </div>

        <div class="modal-body">
          <p>Are you sure you want to delete this notice? This action cannot be undone.</p>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showDeleteConfirm = false">No</button>
          <button class="btn-danger" @click="deleteNotice(pendingDeleteId)">Yes, Delete</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.sec-notices {
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

.btn-add {
  height: 42px;
  padding: 0 20px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  white-space: nowrap;
  transition: background var(--transition-fast);
}

.btn-add:hover { background: var(--c-900); }

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

.filter-btn:hover {
  border-color: var(--c-600);
  color: var(--c-800);
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

.notice-relevance {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 600;
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

.delete-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.delete-btn:hover {
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
}

.close-btn:hover { background: var(--color-border); }

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
  margin-bottom: 4px;
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

.n-input:focus { border-color: var(--c-600); }

.n-textarea {
  height: 100px;
  padding: 10px 13px;
  resize: vertical;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.error-msg {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  margin-top: 6px;
}

.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 24px 22px;
  border-top: 1px solid var(--color-border);
}

.btn-primary {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  transition: background var(--transition-fast);
}

.btn-primary:hover { background: var(--c-900); }

.btn-secondary {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 600;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  border-color: var(--c-600);
  color: var(--c-800);
}

.modal-small {
  max-width: 400px;
}

.btn-danger {
  flex: 1;
  height: 42px;
  border: none;
  border-radius: var(--radius-md);
  background: #dc2626;
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-danger:hover {
  background: #b91c1c;
}

.toolbar {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.tag-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
</style>