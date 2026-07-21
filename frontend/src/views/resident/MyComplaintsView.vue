<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

/* ---------------------------------------------------------------
   Community Issues — SHARED channel for common-area problems.
   Every resident sees the same underlying issue list the secretary
   works from (see sec Issues view), but scoped two ways:
     - "My Issues"   -> anything this resident raised or joined,
                        at any status (including Resolved/Rejected).
     - "Open Issues" -> everything Open / In Progress society-wide,
                        so residents can join instead of duplicating.
   Resolved/Rejected issues the resident never participated in are
   never shown to them, in either tab.
--------------------------------------------------------------- */

const router = useRouter()

const currentResident = { name: 'Ravi Kumar', flat: 'A-402' }

const categoryOptions = ['Plumbing', 'Electrical', 'Cleaning', 'Carpentry', 'Security', 'Gardening', 'Other']
const priorityOptions = ['High', 'Medium', 'Low']
const priorityRank = { High: 3, Medium: 2, Low: 1 }

const towerOptions = ['Tower A', 'Tower B', 'Common Area / Society-wide']
const amenityOptions = [
  'Lift', 'Corridor', 'Staircase', 'Garden', 'Clubhouse',
  'Parking', 'Water Tank', 'Security Cabin', 'Gate / Entrance', 'Terrace', 'Other',
]

const DEFAULT_JOIN_DESC = 'Confirmed the same issue for me too'

// Same shape/data the secretary works from — a resident is just a
// different lens over the same issues.
const issues = ref([
  {
    id: 'ISS-2039', title: 'Corridor light flickering', location: '4th floor corridor, Tower A',
    category: 'Electrical', priority: 'Medium', status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null,
    date: '27 Jun',
    aiSummary: 'Residents report a flickering light on the 4th floor corridor landing in Tower A.',
    reports: [
      { resident: 'Ravi Kumar', flat: 'A-402', desc: 'Corridor light flickering on the 4th floor landing', date: '27 Jun', residentPriority: 'High' },
    ],
  },
  {
    id: 'ISS-2046', title: 'Lift lobby light flickering', location: '4th floor corridor, Tower A',
    category: 'Electrical', priority: 'Medium', status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null,
    date: '29 Jun',
    aiSummary: 'A second, separate report of a flickering light near the 4th floor lift lobby in Tower A — likely the same fault as ISS-2039.',
    reports: [
      { resident: 'Meena Sharma', flat: 'A-405', desc: 'Lift lobby light on the 4th floor keeps flickering, happened twice this week', date: '29 Jun', residentPriority: 'Medium' },
    ],
  },
  {
    id: 'ISS-2050', title: 'Terrace water tank overflowing', location: 'Terrace, Tower B',
    category: 'Plumbing', priority: 'High', status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null,
    date: '30 Jun',
    aiSummary: 'The terrace water tank in Tower B is overflowing, wasting water and posing a slip risk below.',
    reports: [
      { resident: 'Karan Mehta', flat: 'B-304', desc: 'Water overflowing from the terrace tank, wasting a lot of water', date: '30 Jun', residentPriority: 'High' },
    ],
  },
  {
    id: 'ISS-2028', title: 'Lift grinding noise', location: 'Lift 2, Tower A (between floors 3–5)',
    category: 'Other', priority: 'Medium', status: 'In Progress',
    vendor: 'OtisCare Lifts', scheduledStart: '2026-06-22T14:00', durationMinutes: 120,
    date: '22 Jun',
    aiSummary: 'Lift 2 in Tower A makes a grinding noise while travelling between the 3rd and 5th floors.',
    reports: [
      { resident: 'Sana Iqbal', flat: 'A-108', desc: 'Lift making grinding noise between floors 3 and 5', date: '22 Jun', residentPriority: 'High' },
    ],
  },
  {
    // Resolved, and this resident was never part of it — must stay hidden.
    id: 'ISS-2031', title: 'Garbage not collected', location: 'B-wing basement',
    category: 'Cleaning', priority: 'Low', status: 'Resolved',
    vendor: 'Clean Society', scheduledStart: '2026-06-24T09:00', durationMinutes: 60,
    date: '24 Jun',
    aiSummary: 'Garbage was not collected from the B-wing basement collection point.',
    reports: [
      { resident: 'Meena Sharma', flat: 'B-201', desc: 'Garbage not collected from B-wing basement', date: '24 Jun', residentPriority: 'Low' },
    ],
  },
])

function isParticipant(issue) {
  return issue.reports.some(r => r.resident === currentResident.name && r.flat === currentResident.flat)
}

function isOwnReport(r) {
  return r.resident === currentResident.name && r.flat === currentResident.flat
}

const visibleIssues = computed(() => issues.value.filter(i => i.status !== 'Merged'))

/* ---------------- Tabs ---------------- */

const activeTab = ref('mine') // 'mine' | 'open'

const mineIssues = computed(() => visibleIssues.value.filter(isParticipant))
const openIssues = computed(() => visibleIssues.value.filter(i => ['Open', 'In Progress'].includes(i.status)))

const mineStatusFilters = ['All', 'Open', 'In Progress', 'Resolved', 'Rejected']
const filterStatus = ref('All')
const filterCategory = ref('all')
const searchQuery = ref('')

const listForTab = computed(() => activeTab.value === 'mine' ? mineIssues.value : openIssues.value)

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return listForTab.value.filter(i => {
    const matchesStatus = activeTab.value === 'open' || filterStatus.value === 'All' || i.status === filterStatus.value
    const matchesCategory = filterCategory.value === 'all' || i.category === filterCategory.value
    const matchesSearch = !q
      || i.title.toLowerCase().includes(q)
      || i.location.toLowerCase().includes(q)
      || i.id.toLowerCase().includes(q)
    return matchesStatus && matchesCategory && matchesSearch
  }).sort((a, b) => priorityRank[b.priority] - priorityRank[a.priority])
})

function statusClass(s) {
  if (s === 'Open') return 'status-open'
  if (s === 'In Progress') return 'status-progress'
  if (s === 'Resolved') return 'status-resolved'
  if (s === 'Rejected') return 'status-rejected'
  return ''
}

function priorityClass(p) {
  if (p === 'High') return 'pri-high'
  if (p === 'Medium') return 'pri-medium'
  return 'pri-low'
}

function categoryIcon(cat) {
  const map = { Plumbing: '🔧', Electrical: '⚡', Cleaning: '🧹', Carpentry: '🪚', Security: '🛡️', Gardening: '🌿', Other: '📋' }
  return map[cat] || '📋'
}

function formatSlot(iso, minutes) {
  if (!iso) return ''
  const d = new Date(iso)
  const datePart = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
  const timePart = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  return `${datePart}, ${timePart}${minutes ? ` · ~${minutes} min` : ''}`
}

/* ---------------- Navigate to home services ---------------- */

function goToServiceRequests() {
  // adjust this path to match your actual route for the home services request page
  router.push('/services')
}

/* ---------------- Detail modal ---------------- */

const showDetail = ref(false)
const selected = ref(null)
const rating = ref(0)

// editing/deleting the resident's own report within the detail modal
const editingReportIdx = ref(null)
const editReportText = ref('')

// joining an issue with an editable description
const showJoinForm = ref(false)
const joinDescription = ref('')

function openDetail(issue) {
  selected.value = issue
  rating.value = 0
  editingReportIdx.value = null
  editReportText.value = ''
  showJoinForm.value = false
  joinDescription.value = ''
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selected.value = null
  editingReportIdx.value = null
  editReportText.value = ''
  showJoinForm.value = false
  joinDescription.value = ''
}

function startJoinFromDetail() {
  showJoinForm.value = true
  joinDescription.value = DEFAULT_JOIN_DESC
}

function cancelJoinForm() {
  showJoinForm.value = false
  joinDescription.value = ''
}

function confirmJoinFromDetail() {
  const issue = selected.value
  if (!issue || isParticipant(issue)) return
  issue.reports.push({
    resident: currentResident.name, flat: currentResident.flat,
    desc: joinDescription.value.trim() || DEFAULT_JOIN_DESC,
    date: 'Today', residentPriority: null,
  })
  showToast(`You've joined ${issue.id}`)
  closeDetail()
}

function startEditReport(idx) {
  editingReportIdx.value = idx
  editReportText.value = selected.value.reports[idx].desc
}

function cancelEditReport() {
  editingReportIdx.value = null
  editReportText.value = ''
}

function saveEditReport(idx) {
  const text = editReportText.value.trim()
  if (!text) return
  selected.value.reports[idx].desc = text
  selected.value.reports[idx].date = 'Today (edited)'
  editingReportIdx.value = null
  editReportText.value = ''
  showToast('Your description was updated')
}

function deleteOwnReport(idx) {
  const issue = selected.value
  if (!issue) return
  const confirmed = window.confirm("Remove your description from this issue? If you're the only one reporting it, the issue itself will be removed.")
  if (!confirmed) return

  issue.reports.splice(idx, 1)

  if (issue.reports.length === 0) {
    // no one is reporting this anymore — remove the issue entirely
    issues.value = issues.value.filter(i => i.id !== issue.id)
    showToast('Issue removed — you were the only one reporting it')
    closeDetail()
  } else {
    showToast('Your description was removed')
    editingReportIdx.value = null
  }
}

/* ---------------- Raise new issue (with AI duplicate check) ---------------- */

const showRaise = ref(false)
const raiseStep = ref('form') // 'form' | 'matches'

const newTitle = ref('')
const newCategory = ref('Electrical')
const newDesc = ref('')
const newPriority = ref('Medium')

// structured location — a complaint can be anywhere, not just inside a flat
const newTower = ref('Tower A')
const newFloor = ref('')
const newUnit = ref('')
const newIsAmenity = ref(false)
const newAmenity = ref(amenityOptions[0])

const duplicateMatches = ref([])

// builds the same kind of human-readable location string the rest
// of the app (list, search, duplicate-check) already works with
const newLocationString = computed(() => {
  const bits = []
  if (newIsAmenity.value) {
    bits.push(newAmenity.value)
  } else if (newUnit.value.trim()) {
    bits.push(`Flat ${newUnit.value.trim()}`)
  }
  if (newFloor.value.trim()) bits.push(`${newFloor.value.trim()} floor`)
  bits.push(newTower.value)
  return bits.join(', ')
})

function openRaise() {
  raiseStep.value = 'form'
  newTitle.value = ''
  newCategory.value = 'Electrical'
  newDesc.value = ''
  newPriority.value = 'Medium'
  newTower.value = 'Tower A'
  newFloor.value = ''
  newUnit.value = ''
  newIsAmenity.value = false
  newAmenity.value = amenityOptions[0]
  duplicateMatches.value = []
  showRaise.value = true
}

function closeRaise() {
  showRaise.value = false
}

const canCheck = computed(() => newTitle.value.trim() && newTower.value && newDesc.value.trim())

function checkForDuplicates() {
  if (!canCheck.value) return
  const words = `${newTitle.value} ${newLocationString.value} ${newDesc.value}`
    .toLowerCase().split(/\W+/).filter(w => w.length > 3)

  duplicateMatches.value = openIssues.value
    .filter(i => i.category === newCategory.value && !isParticipant(i))
    .filter(i => {
      const text = `${i.title} ${i.location} ${i.aiSummary}`.toLowerCase()
      return words.some(w => text.includes(w))
    })
    .slice(0, 3)

  raiseStep.value = 'matches'
}

function joinMatch(issue) {
  issue.reports.push({
    resident: currentResident.name, flat: currentResident.flat,
    desc: newDesc.value.trim(), date: 'Today', residentPriority: newPriority.value,
  })
  showToast(`Joined ${issue.id} — you'll be updated as it progresses`)
  closeRaise()
}

function createNewIssue() {
  const id = `ISS-${2050 + issues.value.length + 1}`
  issues.value.unshift({
    id, title: newTitle.value.trim(), location: newLocationString.value,
    category: newCategory.value, priority: newPriority.value, status: 'Open',
    vendor: null, scheduledStart: null, durationMinutes: null,
    date: 'Today',
    aiSummary: `Reported by ${currentResident.name}: ${newDesc.value.trim()}`,
    reports: [{
      resident: currentResident.name, flat: currentResident.flat,
      desc: newDesc.value.trim(), date: 'Today', residentPriority: newPriority.value,
    }],
  })
  showToast(`${id} raised — you'll be updated as it progresses`)
  closeRaise()
}

/* ---------------- Toast ---------------- */

const toastVisible = ref(false)
const toastText = ref('')
let toastTimer = null

function showToast(text) {
  toastText.value = text
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2600)
}
</script>

<template>
  <div class="community-issues">

    <div class="page-header">
      <div>
        <h2>Community Issues</h2>
        <p class="page-sub">Shared, common-area problems — visible to the whole society</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="goToServiceRequests">🛠️ Request a Service</button>
        <button class="btn-raise" @click="openRaise">+ Raise New</button>
      </div>
    </div>

    <!-- tabs -->
    <div class="tab-group">
      <button :class="['tab', { active: activeTab === 'mine' }]" @click="activeTab = 'mine'">
        My Issues <span class="tab-count">{{ mineIssues.length }}</span>
      </button>
      <button :class="['tab', { active: activeTab === 'open' }]" @click="activeTab = 'open'">
        Open in Society <span class="tab-count">{{ openIssues.length }}</span>
      </button>
    </div>
    <p v-if="activeTab === 'open'" class="tab-hint">
      Already dealing with one of these? Join it instead of raising a duplicate.
    </p>

    <!-- toolbar -->
    <div class="toolbar">
      <input v-model="searchQuery" type="text" placeholder="Search title, location, ID..." class="search-input" />
      <div class="toolbar-row">
        <div v-if="activeTab === 'mine'" class="status-pill-group">
          <button
            v-for="s in mineStatusFilters" :key="s"
            :class="['status-pill', { active: filterStatus === s }]"
            @click="filterStatus = s"
          >{{ s }}</button>
        </div>
        <select v-model="filterCategory" class="filter-select" :class="{ 'ml-auto': activeTab === 'open' }">
          <option value="all">All categories</option>
          <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <!-- issue cards -->
    <div class="issues-list">
      <div v-for="i in filtered" :key="i.id" class="issue-card" @click="openDetail(i)">
        <div class="cat-icon">{{ categoryIcon(i.category) }}</div>
        <div class="card-summary">
          <div class="card-top">
            <span class="issue-title">{{ i.title }}</span>
            <span v-if="isParticipant(i)" class="following-badge">Following</span>
          </div>
          <p class="issue-loc">{{ i.location }} · {{ i.id }}</p>
        </div>
        <span class="reports-badge" title="Residents reporting this">{{ i.reports.length }} reported</span>
        <span :class="['priority-badge', priorityClass(i.priority)]">{{ i.priority }}</span>
        <span :class="['status-badge', statusClass(i.status)]">{{ i.status }}</span>
      </div>

      <div v-if="filtered.length === 0" class="empty-state">
        <p>{{ activeTab === 'mine' ? "You haven't raised or joined any issues yet" : 'No open issues right now' }}</p>
        <span>{{ activeTab === 'mine' ? 'Raise one, or check what\'s already open in the society' : 'Nice — the society is all caught up' }}</span>
      </div>
    </div>

    <!-- detail modal -->
    <div v-if="showDetail" class="modal-overlay" @click.self="closeDetail">
      <div class="modal modal-lg">
        <div class="modal-header">
          <div>
            <h3>{{ selected?.title }}</h3>
            <span class="modal-sub">{{ selected?.id }} · {{ selected?.location }}</span>
          </div>
          <button class="close-btn" @click="closeDetail">✕</button>
        </div>

        <div class="modal-body">
          <div class="badges-row">
            <span class="category-badge">{{ selected?.category }}</span>
            <span :class="['priority-badge', priorityClass(selected?.priority)]">{{ selected?.priority }}</span>
            <span :class="['status-badge', statusClass(selected?.status)]">{{ selected?.status }}</span>
          </div>

          <div class="section">
            <span class="section-label">Summary · {{ selected?.reports.length }} resident(s) reporting</span>
            <p class="ai-summary">{{ selected?.aiSummary }}</p>
            <div class="reports-list">
              <div
                v-for="(r, idx) in selected?.reports" :key="idx"
                :class="['report-card', { 'report-card-own': isOwnReport(r) }]"
              >
                <div class="report-head">
                  <span class="report-resident">
                    {{ r.resident }} · {{ r.flat }}
                    <span v-if="isOwnReport(r)" class="you-badge">You</span>
                  </span>
                  <span class="report-date">{{ r.date }}</span>
                </div>

                <template v-if="editingReportIdx === idx">
                  <textarea
                    v-model="editReportText"
                    class="n-input n-textarea edit-textarea"
                    rows="2"
                  ></textarea>
                  <div class="report-edit-actions">
                    <button class="btn-outline btn-sm" @click="saveEditReport(idx)">Save</button>
                    <button class="btn-outline btn-sm" @click="cancelEditReport">Cancel</button>
                  </div>
                </template>
                <template v-else>
                  <p class="report-desc">{{ r.desc }}</p>
                  <div class="report-foot">
                    <span v-if="r.residentPriority" class="mini-priority-tag" :class="priorityClass(r.residentPriority)">
                      Felt {{ r.residentPriority }} urgency
                    </span>
                    <div v-if="isOwnReport(r)" class="report-own-actions">
                      <button class="link-btn" @click="startEditReport(idx)">✏️ Edit</button>
                      <button class="link-btn link-danger" @click="deleteOwnReport(idx)">🗑️ Delete</button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div v-if="selected?.vendor" class="section">
            <span class="section-label">Assigned</span>
            <div class="resolved-card">
              <span class="vendor-name">{{ selected.vendor }}</span>
              <span class="slot-text">{{ formatSlot(selected.scheduledStart, selected.durationMinutes) }}</span>
            </div>
          </div>

          <div v-if="selected && !isParticipant(selected) && ['Open', 'In Progress'].includes(selected.status)" class="section">
            <template v-if="!showJoinForm">
              <button class="btn-primary" @click="startJoinFromDetail">I'm facing this too — Join</button>
            </template>
            <template v-else>
              <label class="join-label">Your description (feel free to edit or leave as is)</label>
              <textarea
                v-model="joinDescription"
                class="n-input n-textarea"
                rows="2"
              ></textarea>
              <div class="join-actions">
                <button class="btn-primary" @click="confirmJoinFromDetail">Confirm — Join Issue</button>
                <button class="btn-outline" @click="cancelJoinForm">Cancel</button>
              </div>
            </template>
          </div>

          <div v-if="selected?.status === 'Resolved' && isParticipant(selected)" class="section">
            <span class="section-label">Rate this resolution</span>
            <span class="stars">
              <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= rating }" @click="rating = n">★</span>
            </span>
          </div>

          <div v-if="selected?.status === 'Rejected'" class="section">
            <span class="section-label">Rejected</span>
            <p class="report-desc">This issue was reviewed and rejected by the society office.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- raise modal -->
    <div v-if="showRaise" class="modal-overlay" @click.self="closeRaise">
      <div class="modal modal-lg">
        <div class="modal-header">
          <div>
            <h3>Raise a Community Issue</h3>
            <span class="modal-sub">For shared / common-area problems only</span>
          </div>
          <button class="close-btn" @click="closeRaise">✕</button>
        </div>

        <div class="modal-body">

          <template v-if="raiseStep === 'form'">

            <div class="form-block">
              <span class="block-label">What's the issue</span>

              <label>Title</label>
              <input v-model="newTitle" type="text" class="n-input" placeholder="e.g. Corridor light flickering" />

              <label>Category</label>
              <select v-model="newCategory" class="n-input">
                <option v-for="c in categoryOptions" :key="c" :value="c">{{ categoryIcon(c) }} {{ c }}</option>
              </select>

              <label>Describe the issue</label>
              <textarea v-model="newDesc" class="n-input n-textarea" rows="3" placeholder="What did you notice, and when?"></textarea>

              <label>How urgent does this feel to you?</label>
              <div class="priority-options">
                <button
                  v-for="p in priorityOptions" :key="p"
                  :class="['priority-btn', priorityClass(p), { active: newPriority === p }]"
                  @click="newPriority = p"
                >{{ p }}</button>
              </div>
            </div>

            <div class="form-block location-block">
              <span class="block-label">📍 Where is this</span>

              <div class="location-grid">
                <div class="location-field">
                  <span class="location-label">Tower</span>
                  <select v-model="newTower" class="n-input n-select">
                    <option v-for="t in towerOptions" :key="t" :value="t">{{ t }}</option>
                  </select>
                </div>
                <div class="location-field">
                  <span class="location-label">Floor</span>
                  <input v-model="newFloor" type="text" class="n-input" placeholder="e.g. 4th, Ground" />
                </div>
              </div>

              <button
                type="button"
                :class="['amenity-toggle', { active: newIsAmenity }]"
                @click="newIsAmenity = !newIsAmenity"
              >
                <span class="toggle-dot"></span>
                This is at a shared amenity, not a flat
              </button>

              <div v-if="!newIsAmenity" class="location-field full">
                <span class="location-label">Unit / Flat</span>
                <input v-model="newUnit" type="text" class="n-input" placeholder="e.g. A-402" />
              </div>

              <div v-else class="location-field full">
                <span class="location-label">Which amenity?</span>
                <select v-model="newAmenity" class="n-input n-select">
                  <option v-for="a in amenityOptions" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>

              <div class="location-preview">
                📌 {{ newLocationString }}
              </div>
            </div>

            <div class="ai-check-card">
              <div class="ai-check-icon">✨</div>
              <div class="ai-check-text">
                <span class="ai-check-title">AI Duplicate Check</span>
                <span class="ai-check-sub">
                  {{ canCheck
                    ? "We'll scan open issues in your society before you submit"
                    : 'Fill in title, description and tower to run the check' }}
                </span>
              </div>
              <button class="btn-ai-check" :disabled="!canCheck" @click="checkForDuplicates">
                Check Now
              </button>
            </div>
          </template>

          <template v-else>
            <div v-if="duplicateMatches.length" class="section" style="padding-top:0;border-top:none;">
              <span class="section-label">This might already be reported</span>
              <div class="reports-list">
                <div v-for="m in duplicateMatches" :key="m.id" class="report-card match-card">
                  <div class="report-head">
                    <span class="report-resident">{{ m.title }}</span>
                    <span :class="['status-badge', statusClass(m.status)]">{{ m.status }}</span>
                  </div>
                  <p class="report-desc">{{ m.location }} · {{ m.reports.length }} reported</p>
                  <button class="btn-outline join-btn" @click="joinMatch(m)">Join {{ m.id }}</button>
                </div>
              </div>
            </div>
            <div v-else class="section" style="padding-top:0;border-top:none;">
              <span class="section-label">No similar open issues found</span>
              <p class="helper-text">Nothing matching this description is currently open — you're likely the first to report it.</p>
            </div>

            <button class="btn-primary" @click="createNewIssue">
              None of these — Raise as New Issue
            </button>
            <button class="btn-outline back-btn" @click="raiseStep = 'form'">← Back to edit details</button>
          </template>

        </div>
      </div>
    </div>

    <!-- toast -->
    <transition name="toast-fade">
      <div v-if="toastVisible" class="toast">
        <span class="toast-check">✓</span>
        <span>{{ toastText }}</span>
      </div>
    </transition>

  </div>
</template>

<style scoped>
.community-issues { max-width: var(--content-max-width); }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 { font-size: var(--font-size-3xl); font-weight: 800; letter-spacing: -0.4px; }
.page-sub { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 4px; }

.header-actions { display: flex; gap: 10px; }

.btn-raise {
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

.btn-raise:hover { background: var(--c-900); }

/* tabs */
.tab-group {
  display: flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 4px;
  width: fit-content;
  margin-bottom: 10px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 15px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.tab.active { background: var(--c-800); color: #fff; }

.tab-count {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: rgba(0,0,0,0.08);
}

.tab.active .tab-count { background: rgba(255,255,255,0.25); }

.tab-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: 14px;
}

/* toolbar */
.toolbar { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.toolbar-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.search-input {
  height: 42px;
  padding: 0 14px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  width: 100%;
  transition: border-color var(--transition-fast);
}

.search-input:focus { border-color: var(--c-600); }

.status-pill-group {
  display: flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 4px;
}

.status-pill {
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.status-pill.active { background: var(--c-800); color: #fff; }

.filter-select {
  height: 36px;
  padding: 0 10px;
  border: 1.5px solid var(--color-border-soft);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  outline: none;
  cursor: pointer;
}

.ml-auto { margin-left: auto; }

/* issue cards */
.issues-list { display: flex; flex-direction: column; gap: 10px; }

.issue-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  box-shadow: var(--shadow-xs);
  cursor: pointer;
  transition: background var(--transition-fast);
  text-align: left;
}

.issue-card:hover { background: var(--color-surface-muted); }

.cat-icon {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: #EAF6FB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.card-summary { flex: 1; min-width: 0; }

.card-top { display: flex; align-items: center; gap: 8px; }

.issue-title { font-size: var(--font-size-md); font-weight: 700; color: var(--color-text-primary); }

.following-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: #EAF6FB;
  color: var(--c-800);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.issue-loc { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 2px; }

.reports-badge {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.priority-badge, .status-badge {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
}

.pri-high   { background: var(--color-danger-bg);  color: var(--color-danger-text);  }
.pri-medium { background: var(--color-warning-bg); color: var(--color-warning-text); }
.pri-low    { background: var(--color-success-bg); color: var(--color-success-text); }

.status-open     { background: var(--color-info-bg);    color: var(--color-info-text);    }
.status-progress { background: var(--color-warning-bg); color: var(--color-warning-text); }
.status-resolved { background: var(--color-success-bg); color: var(--color-success-text); }
.status-rejected { background: var(--color-danger-bg);  color: var(--color-danger-text);  }

.empty-state { text-align: center; padding: 60px 20px; }
.empty-state p { font-size: var(--font-size-lg); font-weight: 600; color: var(--color-text-muted); margin-bottom: 6px; }
.empty-state span { font-size: var(--font-size-sm); color: var(--color-text-muted); }

/* modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: 20px;
}

.modal {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 460px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-lg { max-width: 560px; }

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.modal-header h3 { font-size: var(--font-size-xl); font-weight: 700; }

.modal-sub {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 3px;
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
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.close-btn:hover { background: var(--color-border); }

.modal-body {
  padding: 20px 24px 26px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.badges-row { display: flex; gap: 8px; flex-wrap: wrap; }

.category-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 700;
  background: var(--color-surface-soft);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.section { padding-top: 14px; border-top: 1px solid var(--color-border); }

.section-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 10px;
}

.ai-summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-style: italic;
  line-height: 1.5;
  margin-bottom: 12px;
}

.reports-list { display: flex; flex-direction: column; gap: 8px; }

.report-card {
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.report-card-own {
  border-color: var(--c-600);
  background: #EAF6FB;
}

.report-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 4px; }
.report-resident { display: flex; align-items: center; gap: 6px; font-size: var(--font-size-xs); font-weight: 700; color: var(--color-text-primary); }
.report-date { font-size: var(--font-size-xs); color: var(--color-text-muted); white-space: nowrap; }
.report-desc { font-size: var(--font-size-sm); color: var(--color-text-secondary); line-height: 1.5; }

.you-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: var(--c-800);
  color: #fff;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.report-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.mini-priority-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.report-own-actions {
  display: flex;
  gap: 14px;
  margin-left: auto;
}

.link-btn {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--c-800);
}

.link-btn:hover { text-decoration: underline; }

.link-danger { color: var(--color-danger-text); }

.edit-textarea {
  margin-top: 4px;
  background: var(--color-surface);
}

.report-edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.btn-sm {
  height: 32px;
  padding: 0 12px;
  font-size: var(--font-size-xs);
}

.match-card { display: flex; flex-direction: column; gap: 8px; }
.join-btn { align-self: flex-start; }

label, .join-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--c-800);
  margin-top: 10px;
  margin-bottom: 6px;
}

.modal-body > label:first-child { margin-top: 0; }

.join-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.join-actions .btn-primary { margin-top: 0; }

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
.n-select { cursor: pointer; }

.n-textarea {
  height: auto;
  min-height: 64px;
  padding: 10px 13px;
  resize: vertical;
  line-height: 1.5;
}

.helper-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 6px;
  line-height: 1.5;
}

/* raise-form blocks */
.form-block {
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px 16px 18px;
}

.form-block + .form-block { margin-top: 14px; }

.block-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 800;
  color: var(--c-800);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 4px;
}

.form-block label { margin-top: 12px; }
.form-block > label:first-of-type { margin-top: 12px; }

/* priority chips */
.priority-options {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.priority-btn {
  flex: 1;
  height: 38px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 700;
  border: 1.5px solid transparent;
  opacity: 0.55;
  transition: all var(--transition-fast);
}

.priority-btn.active { opacity: 1; border-color: currentColor; }

/* location grid */
.location-block { margin-top: 14px; }

.location-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
  margin-bottom: 10px;
}

.location-field { display: flex; flex-direction: column; }
.location-field.full { margin-top: 10px; }

.location-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 5px;
}

.amenity-toggle {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.amenity-toggle.active {
  border-color: var(--c-800);
  background: #EAF3FB;
  color: var(--c-800);
}

.toggle-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid var(--color-border-strong);
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.amenity-toggle.active .toggle-dot {
  background: var(--c-800);
  border-color: var(--c-800);
  box-shadow: inset 0 0 0 2.5px #EAF3FB;
}

.location-preview {
  margin-top: 12px;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--c-800);
  background: #EAF6FB;
  border-radius: var(--radius-md);
  padding: 9px 12px;
}

/* AI duplicate-check card */
.ai-check-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(155deg, var(--c-800), var(--c-500));
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  color: #fff;
}

.ai-check-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
}

.ai-check-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ai-check-title { font-size: var(--font-size-sm); font-weight: 800; }
.ai-check-sub { font-size: var(--font-size-xs); opacity: 0.85; line-height: 1.4; }

.btn-ai-check {
  flex-shrink: 0;
  height: 40px;
  padding: 0 18px;
  border-radius: var(--radius-pill);
  background: #fff;
  color: var(--c-800);
  font-size: var(--font-size-sm);
  font-weight: 800;
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.btn-ai-check:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-ai-check:not(:disabled):hover { opacity: 0.88; }

.btn-primary {
  width: 100%;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--c-800);
  color: #fff;
  font-size: var(--font-size-md);
  font-weight: 700;
  margin-top: 4px;
  transition: background var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: var(--c-900); }

.btn-outline {
  height: 42px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border-soft);
  background: var(--color-surface);
  color: var(--c-800);
  font-size: var(--font-size-sm);
  font-weight: 700;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.btn-outline:hover:not(:disabled) { border-color: var(--c-600); background: var(--color-surface-soft); }

.back-btn { width: 100%; margin-top: 8px; }

.resolved-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--color-surface-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}

.vendor-name { font-weight: 700; color: var(--color-text-primary); }
.slot-text { font-size: var(--font-size-xs); font-weight: 500; color: var(--color-text-muted); }

.stars { font-size: 19px; letter-spacing: 2px; }
.star { color: var(--color-border-strong); cursor: pointer; }
.star.filled { color: #E0A030; }

/* toast */
.toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: var(--radius-md);
  background: var(--color-success-bg);
  color: var(--color-success-text);
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: var(--shadow-lg);
  z-index: var(--z-modal);
}

.toast-check {
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

.toast-fade-enter-active, .toast-fade-leave-active {
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.toast-fade-enter-from, .toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
}
</style>