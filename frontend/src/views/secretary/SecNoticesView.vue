<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'


const showForm    = ref(false)
const searchQuery = ref('')
const notices     = ref([])
const loading     = ref(true)
const error       = ref('')
const formError   = ref('')
const blocks      = ref([])   // real tower values from Flat table, via /flats/blocks

// --- filters ---
const statusFilter    = ref('active')   // 'active' | 'expired' | 'all' — defaults to active/non-expired
const tagFilter        = ref('All')      // 'All' | one of `tags`
const relevanceFilter = ref('all')       // 'all' | block value


const newNotice = ref({
  title:       '',
  body:        '',
  tag:         'General',
  relevance:   'all',
  expiry_date: '',
})


const tags = [
  'General', 'Maintenance', 'Security', 'Event', 'Urgent',
]


// built from actual Flat.tower values instead of hardcoded block_a/b/c —
// keeps notice.relevance in sync with what residents are filtered against
// (resident.flat.tower) on the backend
const relevanceOptions = computed(() => [
  { value: 'all', label: 'All Residents' },
  ...blocks.value.map(b => ({ value: b, label: `Block ${b} Only` })),
])

// filter dropdown for relevance needs its own "All" (meaning "don't filter"),
// separate from the notice-level "all residents" value used in the form
const relevanceFilterOptions = computed(() => [
  { value: 'all', label: 'All Blocks' },
  ...blocks.value.map(b => ({ value: b, label: `Block ${b}` })),
])


const tagColors = {
  General:      { accent: '#49769F', tagBg: '#EAF0F4' },
  Maintenance:  { accent: '#E0A030', tagBg: '#FBF1DE' },
  Security:     { accent: '#B4442F', tagBg: '#FBE9E4' },
  Event:        { accent: '#3AA06B', tagBg: '#E4F5ED' },
  Urgent:       { accent: '#C43D3D', tagBg: '#FBE9E4' },
}


onMounted(async () => {
  await Promise.all([fetchNotices(), fetchBlocks()])
})


async function fetchBlocks() {
  try {
    const res = await api.get('/flats/blocks')
    blocks.value = res.data.blocks
  } catch (err) {
    // non-fatal — relevanceOptions just falls back to 'All Residents' only
    console.error('Failed to load blocks', err)
  }
}


async function fetchNotices() {
  loading.value = true
  try {
    const response = await api.get('/notices')
    notices.value  = response.data.notices
  } catch (err) {
    error.value = 'Failed to load notices'
  } finally {
    loading.value = false
  }
}


function isExpired(dateStr) {
  if (!dateStr) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const exp = new Date(dateStr)
  return exp < today
}


function toggleUrgent() {
  tagFilter.value = tagFilter.value === 'Urgent' ? 'All' : 'Urgent'
}


const filteredNotices = computed(() => {
  let list = notices.value

  // status: active (default) hides expired notices, expired shows only expired, all shows everything
  if (statusFilter.value === 'active') {
    list = list.filter(n => !isExpired(n.expiry_date))
  } else if (statusFilter.value === 'expired') {
    list = list.filter(n => isExpired(n.expiry_date))
  }

  if (tagFilter.value !== 'All') {
    list = list.filter(n => n.tag === tagFilter.value)
  }

  // block filter: keep notices targeted at the selected block, plus notices meant for everyone
  if (relevanceFilter.value !== 'all') {
    list = list.filter(n => n.relevance === relevanceFilter.value)
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(n =>
      n.title.toLowerCase().includes(q) ||
      n.description.toLowerCase().includes(q)
    )
  }

  return list
})


async function postNotice() {
  formError.value = ''


  if (!newNotice.value.title || !newNotice.value.body || !newNotice.value.expiry_date) {
    formError.value = 'Title, body and expiry date are required'
    return
  }


  try {
    await api.post('/notices', {
      title:       newNotice.value.title,
      description: newNotice.value.body,
      tag:         newNotice.value.tag,
      relevance:   newNotice.value.relevance,
      expiry_date: newNotice.value.expiry_date,
    })


    newNotice.value = { title: '', body: '', tag: 'General', relevance: 'all', expiry_date: '' }
    showForm.value  = false
    await fetchNotices()


  } catch (err) {
    formError.value = err.response?.data?.error || 'Failed to post notice'
  }
}


async function deleteNotice(id) {
  try {
    await api.delete(`/notices/${id}`)
    await fetchNotices()
  } catch (err) {
    error.value = 'Failed to delete notice'
  }
}


function tagStyle(tag) {
  return tagColors[tag] || tagColors['General']
}


function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short',
  })
}


// resolves the raw relevance value (e.g. 'all', 'A', 'B') to a readable label
function relevanceLabel(relevance) {
  if (relevance === 'all') return 'All residents'
  return `Block ${relevance}`
}
</script>


<template>
  <div class="sec-notices">


    <div class="page-header">
      <div>
        <h2>Notices</h2>
        <p class="page-sub">{{ filteredNotices.length }} of {{ notices.length }} notices shown</p>
      </div>
      <button class="btn-add" @click="showForm = true">+ Post a notice</button>
    </div>


    <input
      v-model="searchQuery"
      type="text"
      placeholder="Search notices..."
      class="search-input"
    />

    <div class="filter-bar">
      <select v-model="statusFilter" class="n-input filter-input">
        <option value="active">Active (non-expired)</option>
        <option value="expired">Expired</option>
        <option value="all">All</option>
      </select>

      <select v-model="tagFilter" class="n-input filter-input">
        <option value="All">All Tags</option>
        <option v-for="t in tags" :key="t" :value="t">{{ t }}</option>
      </select>

      <select v-model="relevanceFilter" class="n-input filter-input">
        <option v-for="r in relevanceFilterOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
      </select>

      <button
        class="urgent-toggle"
        :class="{ active: tagFilter === 'Urgent' }"
        @click="toggleUrgent"
      >
        ⚡ Urgent
      </button>
    </div>


    <!-- loading -->
    <div v-if="loading" class="empty-state"><p>Loading notices...</p></div>
    <div v-else-if="error" class="empty-state"><p>{{ error }}</p></div>


    <div v-else class="notices-list">
      <div
        v-for="notice in filteredNotices"
        :key="notice.id"
        class="notice-card"
      >
        <div class="notice-accent" :style="{ background: tagStyle(notice.tag).accent }"></div>


        <div class="notice-body">
          <div class="notice-meta">
            <span
              class="notice-tag"
              :style="{ color: tagStyle(notice.tag).accent, background: tagStyle(notice.tag).tagBg }"
            >
              {{ notice.tag }}
            </span>
            <span class="notice-date">{{ formatDate(notice.created_at) }}</span>
            <span class="notice-relevance">{{ relevanceLabel(notice.relevance) }}</span>
            <span class="notice-expiry">Expires {{ notice.expiry_date }}</span>
          </div>
          <h3 class="notice-title">{{ notice.title }}</h3>
          <p class="notice-text">{{ notice.description }}</p>
        </div>


        <button class="delete-btn" @click="deleteNotice(notice.id)">✕</button>
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
          <input v-model="newNotice.title" type="text" placeholder="e.g. Water supply disruption" class="n-input" />


          <label>Body *</label>
          <textarea v-model="newNotice.body" placeholder="Full notice details..." class="n-input n-textarea" />


          <div class="two-col">
            <div>
              <label>Tag</label>
              <select v-model="newNotice.tag" class="n-input">
                <option v-for="t in tags" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div>
              <label>Relevance</label>
              <select v-model="newNotice.relevance" class="n-input">
                <option v-for="r in relevanceOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
            </div>
          </div>


          <label>Expiry Date *</label>
          <input v-model="newNotice.expiry_date" type="date" class="n-input" />


          <p v-if="formError" class="error-msg">{{ formError }}</p>
        </div>


        <div class="modal-footer">
          <button class="btn-secondary" @click="showForm = false">Cancel</button>
          <button class="btn-primary" @click="postNotice">Post Notice</button>
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
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  margin-bottom: 12px;
  transition: border-color var(--transition-fast);
}


.search-input:focus { border-color: var(--c-600); }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-input {
  width: auto;
  min-width: 150px;
  flex: 1 1 150px;
}

.urgent-toggle {
  height: 42px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.urgent-toggle:hover {
  border-color: #C43D3D;
  color: #C43D3D;
}

.urgent-toggle.active {
  background: #FBE9E4;
  border-color: #C43D3D;
  color: #C43D3D;
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


.notice-body { flex: 1; min-width: 0; }


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


.notice-date      { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.notice-relevance { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: 600; }
.notice-expiry    { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: auto; }


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


.modal-header h3 { font-size: var(--font-size-xl); font-weight: 700; }


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
</style>