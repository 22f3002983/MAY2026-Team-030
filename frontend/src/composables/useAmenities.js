import { reactive, computed } from 'vue'

// ---------------------------------------------------------------------------
// Current resident (mock — replace with real auth/session data)
// ---------------------------------------------------------------------------
export const currentUser = { id: 'u1', name: 'You', flat: 'A-302' }

// ---------------------------------------------------------------------------
// Amenity catalogue
// ---------------------------------------------------------------------------
// category: 'exclusive' (bookable, private use) | 'public' (shared, open) | 'unbookable' (infra, info-only)
// pricing.type: 'hourly' | 'daily' | null
const state = reactive({
  amenities: [
    {
      id: 1,
      name: 'Community Hall',
      category: 'exclusive',
      icon: '🏛',
      location: 'Clubhouse · Ground Floor',
      description: 'A large hall for weddings, functions and society events.',
      capacity: 100,
      air_conditioned: true,
      decoratable: true,
      features: ['Stage', 'Sound system', 'Tables & chairs', 'Attached pantry'],
      booking_type: 'approval_required',
      pricing: { type: 'daily', rate: 3000, minUnits: 1, unitLabel: 'day' },
      status: 'available',
      status_until: null,
    },
    {
      id: 2,
      name: 'Guest House',
      category: 'exclusive',
      icon: '🏠',
      location: 'Block C · Ground Floor',
      description: 'Two furnished rooms for outstation guests of residents.',
      capacity: 4,
      air_conditioned: true,
      decoratable: false,
      features: ['2 rooms', 'Attached bath', 'Housekeeping'],
      booking_type: 'approval_required',
      pricing: { type: 'daily', rate: 1500, minUnits: 1, unitLabel: 'night' },
      status: 'booked',
      status_until: '2026-07-25',
    },
    {
      id: 3,
      name: 'BBQ Area',
      category: 'exclusive',
      icon: '🍖',
      location: 'Garden Side · near Block B',
      description: 'Outdoor BBQ area next to the garden.',
      capacity: 20,
      air_conditioned: false,
      decoratable: true,
      features: ['Grill stations', 'Seating', 'Outdoor lighting'],
      booking_type: 'automatic',
      pricing: { type: 'hourly', rate: 500, minUnits: 2, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 4,
      name: 'Party Room',
      category: 'exclusive',
      icon: '🎉',
      location: 'Clubhouse · 1st Floor',
      description: 'Indoor party room with a music system.',
      capacity: 40,
      air_conditioned: true,
      decoratable: true,
      features: ['Sound system', 'Dance floor', 'Fridge'],
      booking_type: 'automatic',
      pricing: { type: 'hourly', rate: 700, minUnits: 2, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 5,
      name: 'Terrace',
      category: 'exclusive',
      icon: '🌇',
      location: 'Block A · Rooftop',
      description: 'Open-air rooftop space with skyline views, great for evening get-togethers.',
      capacity: 50,
      air_conditioned: false,
      decoratable: true,
      features: ['Open-air', 'Fairy lights', 'Seating on request'],
      booking_type: 'automatic',
      pricing: { type: 'hourly', rate: 600, minUnits: 2, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 6,
      name: 'Tennis Court',
      category: 'exclusive',
      icon: '🎾',
      location: 'Near Garden',
      description: 'Outdoor synthetic tennis court, book by the hour.',
      capacity: 4,
      air_conditioned: false,
      decoratable: false,
      features: ['Floodlights', 'Racket rental at desk'],
      booking_type: 'automatic',
      pricing: { type: 'hourly', rate: 300, minUnits: 1, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 7,
      name: 'Mini Theatre',
      category: 'exclusive',
      icon: '🎬',
      location: 'Clubhouse · Basement',
      description: 'Private screening room for movie nights and watch parties.',
      capacity: 25,
      air_conditioned: true,
      decoratable: false,
      features: ['Projector & screen', 'Surround sound', 'Recliner seating'],
      booking_type: 'approval_required',
      pricing: { type: 'hourly', rate: 400, minUnits: 2, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 8,
      name: 'Swimming Pool',
      category: 'public',
      icon: '🏊',
      location: 'Clubhouse · Ground Floor',
      description: 'Shared pool, open 6 AM – 9 PM. No booking required.',
      capacity: null,
      air_conditioned: false,
      decoratable: false,
      features: ['Open 6 AM – 9 PM', 'Lifeguard on duty'],
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 9,
      name: 'Gymnasium',
      category: 'public',
      icon: '🏋',
      location: 'Clubhouse · 2nd Floor',
      description: 'Currently under maintenance.',
      capacity: null,
      air_conditioned: true,
      decoratable: false,
      features: ['Cardio & weights', 'Trainer available 6–10 AM'],
      booking_type: null,
      pricing: { type: null },
      status: 'maintenance',
      status_until: '2026-07-10',
    },
    {
      id: 10,
      name: 'Garden',
      category: 'public',
      icon: '🌿',
      location: 'Central Garden',
      description: 'Common garden, open all day. Can be booked exclusively for private events.',
      capacity: 60,
      air_conditioned: false,
      decoratable: true,
      features: ['Open lawn', 'Walking track around'],
      booking_type: 'approval_required',
      special_booking: true, // shared facility, exceptionally bookable for private use
      pricing: { type: 'hourly', rate: 250, minUnits: 2, unitLabel: 'hour' },
      status: 'available',
      status_until: null,
    },
    {
      id: 11,
      name: "Children's Play Area",
      category: 'public',
      icon: '🛝',
      location: 'Block B · Courtyard',
      description: 'Play area for children. Supervised entry only.',
      capacity: null,
      air_conditioned: false,
      decoratable: false,
      features: ['Supervised entry', 'Ages 3–12'],
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 12,
      name: 'Lift — Block A',
      category: 'unbookable',
      icon: '🛗',
      location: 'Block A',
      description: 'Currently operational.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 13,
      name: 'Staircase — Block B',
      category: 'unbookable',
      icon: '🪜',
      location: 'Block B',
      description: 'Railing repair ongoing. Use Block A staircase.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'maintenance',
      status_until: '2026-07-24',
    },
    {
      id: 14,
      name: 'DG Generator',
      category: 'unbookable',
      icon: '⚡',
      location: 'Basement · Utility Room',
      description: 'Backup power for common areas during outages.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 15,
      name: 'Overhead Water Tank',
      category: 'unbookable',
      icon: '🚰',
      location: 'Rooftop · Block C',
      description: 'Being cleaned as part of quarterly maintenance.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'maintenance',
      status_until: '2026-07-23',
    },
    {
      id: 16,
      name: 'Sewage Treatment Plant',
      category: 'unbookable',
      icon: '♻️',
      location: 'Rear Compound',
      description: 'STP operational, serviced monthly.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 17,
      name: 'Basement Parking — Level 1',
      category: 'unbookable',
      icon: '🅿️',
      location: 'Block A · B1',
      description: 'Resident parking, first-come-first-served.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 18,
      name: 'Basement Parking — Level 2',
      category: 'unbookable',
      icon: '🅿️',
      location: 'Block A · B2',
      description: 'Repainting of parking lines in progress.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'maintenance',
      status_until: '2026-07-22',
    },
    {
      id: 19,
      name: 'CCTV & Security',
      category: 'unbookable',
      icon: '📹',
      location: 'Main Gate & Common Areas',
      description: '24x7 monitored security system.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 20,
      name: 'Fire Safety System',
      category: 'unbookable',
      icon: '🧯',
      location: 'All Blocks',
      description: 'Sprinklers and extinguishers, inspected annually.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
    {
      id: 21,
      name: 'Solar Panels',
      category: 'unbookable',
      icon: '☀️',
      location: 'Rooftop · Block A',
      description: 'Powers common-area lighting.',
      capacity: null,
      booking_type: null,
      pricing: { type: null },
      status: 'available',
      status_until: null,
    },
  ],

  // Every booking, across all residents — never expose this list raw to the UI.
  bookings: [
    {
      id: 'b1', amenity_id: 2, user_id: 'u9', user_name: 'Resident B-104',
      start_date: '2026-07-22', end_date: '2026-07-25',
      status: 'confirmed', price: 4500, event_type: 'Guests staying over', guests: 3,
    },
    {
      id: 'b2', amenity_id: 1, user_id: 'u1', user_name: 'You',
      start_date: '2026-08-02', end_date: '2026-08-02',
      status: 'pending_approval', price: 3000, event_type: 'Birthday function', guests: 80,
      created_at: '2026-07-18',
    },
    {
      id: 'b3', amenity_id: 4, user_id: 'u1', user_name: 'You',
      start_date: '2026-07-15', end_date: '2026-07-15', start_time: '18:00', end_time: '21:00',
      status: 'completed', price: 2100, event_type: 'Farewell party', guests: 30,
      created_at: '2026-07-10',
    },
    {
      id: 'b4', amenity_id: 3, user_id: 'u5', user_name: 'Resident C-201',
      start_date: '2026-07-21', end_date: '2026-07-21', start_time: '18:00', end_time: '21:00',
      status: 'confirmed', price: 1500, event_type: 'Family dinner', guests: 15,
    },
    {
      id: 'b5', amenity_id: 5, user_id: 'u1', user_name: 'You',
      start_date: '2026-07-28', end_date: '2026-07-28', start_time: '17:00', end_time: '20:00',
      status: 'confirmed', price: 1800, event_type: 'Kitty party', guests: 20,
      created_at: '2026-07-16',
    },
    {
      id: 'b6', amenity_id: 7, user_id: 'u1', user_name: 'You',
      start_date: '2026-07-30', end_date: '2026-07-30', start_time: '19:00', end_time: '22:00',
      status: 'awaiting_payment', price: 1200, event_type: 'Movie night', guests: 18,
      created_at: '2026-07-19',
    },
    {
      id: 'b7', amenity_id: 2, user_id: 'u1', user_name: 'You',
      start_date: '2026-06-10', end_date: '2026-06-12',
      status: 'cancelled', price: 4500, event_type: 'Guests staying over', guests: 2,
      created_at: '2026-06-01',
    },
  ],
})

const BLOCKING_STATUSES = ['confirmed', 'pending_approval', 'awaiting_payment']

// ---------------------------------------------------------------------------
// Derived views
// ---------------------------------------------------------------------------
export const amenities = computed(() => state.amenities)

export const myBookings = computed(() =>
  state.bookings
    .filter(b => b.user_id === currentUser.id)
    .map(b => ({ ...b, amenity: state.amenities.find(a => a.id === b.amenity_id) }))
    .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
)

export const myUpcomingBookings = computed(() =>
  myBookings.value.filter(b => ['pending_approval', 'awaiting_payment', 'confirmed'].includes(b.status))
)

export const myPastBookings = computed(() =>
  myBookings.value.filter(b => ['completed', 'cancelled', 'rejected'].includes(b.status))
)

export function bookingsForAmenity(amenityId) {
  return state.bookings.filter(b => b.amenity_id === amenityId && BLOCKING_STATUSES.includes(b.status))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function toMinutes(t) {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function datesOverlap(aStart, aEnd, bStart, bEnd) {
  return aStart <= bEnd && bStart <= aEnd
}

// Bookability is controlled purely by booking_type — the secretary can flip any
// amenity (exclusive, shared, or otherwise) bookable/unbookable regardless of category.
export function isBookable(amenity) {
  return !!amenity.booking_type
}

export function statusLabel(status) {
  return {
    available: 'Available',
    booked: 'Booked',
    maintenance: 'Maintenance',
    closed: 'Closed',
  }[status] || status
}

export function bookingStatusLabel(status) {
  return {
    pending_approval: 'Pending approval',
    awaiting_payment: 'Approved · payment due',
    confirmed: 'Confirmed',
    completed: 'Completed',
    cancelled: 'Cancelled',
    rejected: 'Not approved',
  }[status] || status
}

// ---------------------------------------------------------------------------
// Availability — only reveals the blocking window for the queried slot,
// never the full calendar of other residents' bookings.
// ---------------------------------------------------------------------------
export function checkAvailability(amenityId, { date, startTime, endTime, endDate }) {
  const amenity = state.amenities.find(a => a.id === amenityId)
  const existing = bookingsForAmenity(amenityId)
  const isHourly = amenity.pricing.type === 'hourly'
  const rangeEnd = endDate || date

  const conflict = existing.find(b => {
    if (!datesOverlap(date, rangeEnd, b.start_date, b.end_date)) return false
    if (isHourly && b.start_time && date === b.start_date) {
      return toMinutes(startTime) < toMinutes(b.end_time) && toMinutes(b.start_time) < toMinutes(endTime)
    }
    return true
  })

  if (conflict) {
    return {
      available: false,
      message: isHourly
        ? `Already booked until ${conflict.end_time} on ${conflict.start_date}.`
        : `Already booked through ${conflict.end_date}.`,
      bookedUntil: isHourly ? conflict.end_time : conflict.end_date,
    }
  }
  return { available: true, message: 'This slot is free.' }
}

export function calculatePrice(amenity, units) {
  if (!amenity.pricing?.rate) return 0
  return amenity.pricing.rate * Math.max(units, amenity.pricing.minUnits || 1)
}

// ---------------------------------------------------------------------------
// Booking actions
// ---------------------------------------------------------------------------
export function createBooking({ amenity, date, endDate, startTime, endTime, eventType, guests, price, pay }) {
  const needsApproval = amenity.booking_type === 'approval_required'
  const status = needsApproval ? 'pending_approval' : (pay ? 'confirmed' : 'awaiting_payment')

  const booking = {
    id: `b${Date.now()}`,
    amenity_id: amenity.id,
    user_id: currentUser.id,
    user_name: currentUser.name,
    start_date: date,
    end_date: endDate || date,
    start_time: startTime || null,
    end_time: endTime || null,
    status,
    price,
    event_type: eventType,
    guests,
    created_at: new Date().toISOString().slice(0, 10),
  }
  state.bookings.push(booking)
  return booking
}

export function payForBooking(bookingId) {
  const booking = state.bookings.find(b => b.id === bookingId)
  if (booking) booking.status = 'confirmed'
}

export function cancelBooking(bookingId) {
  const booking = state.bookings.find(b => b.id === bookingId)
  if (booking) booking.status = 'cancelled'
}

// ---------------------------------------------------------------------------
// Secretary — amenity CRUD
// ---------------------------------------------------------------------------
export function addAmenity(data) {
  const id = state.amenities.length ? Math.max(...state.amenities.map(a => a.id)) + 1 : 1
  const amenity = {
    id,
    name: data.name,
    category: data.category || 'exclusive',
    icon: data.icon || '⭐',
    location: data.location || '',
    tower: data.tower || '',
    floor: data.floor || '',
    description: data.description || '',
    capacity: data.capacity ?? null,
    air_conditioned: data.air_conditioned ?? false,
    decoratable: data.decoratable ?? false,
    features: data.features || [],
    booking_type: data.booking_type || null, // null = not bookable
    pricing: data.pricing || { type: null },
    status: data.status || 'available',
    status_until: data.status_until || null,
  }
  state.amenities.push(amenity)
  return amenity
}

export function updateAmenity(id, patch) {
  const amenity = state.amenities.find(a => a.id === id)
  if (!amenity) return null
  Object.assign(amenity, patch)
  return amenity
}

// Returns { ok: true } or { ok: false, reason } — blocks deletion if there are
// bookings that are still pending, awaiting payment, or confirmed.
export function deleteAmenity(id) {
  const active = bookingsForAmenity(id)
  if (active.length) {
    return { ok: false, reason: `${active.length} active booking(s) exist for this amenity. Cancel or complete them first.` }
  }
  const idx = state.amenities.findIndex(a => a.id === id)
  if (idx !== -1) state.amenities.splice(idx, 1)
  return { ok: true }
}

// Toggle bookability independent of category. Passing a booking_type of null
// makes the amenity unbookable; 'automatic' or 'approval_required' makes it bookable.
export function setBookable(id, bookingType) {
  return updateAmenity(id, { booking_type: bookingType })
}

export function setMaintenance(id, until) {
  return updateAmenity(id, { status: 'maintenance', status_until: until || null })
}

export function clearMaintenance(id) {
  return updateAmenity(id, { status: 'available', status_until: null })
}

export function setRate(id, pricing) {
  return updateAmenity(id, { pricing })
}

// ---------------------------------------------------------------------------
// Secretary — approvals
// ---------------------------------------------------------------------------
export const pendingApprovals = computed(() =>
  state.bookings
    .filter(b => b.status === 'pending_approval')
    .map(b => ({ ...b, amenity: state.amenities.find(a => a.id === b.amenity_id) }))
    .sort((a, b) => new Date(a.created_at || a.start_date) - new Date(b.created_at || b.start_date))
)

export function approveBooking(bookingId) {
  const booking = state.bookings.find(b => b.id === bookingId)
  if (booking) booking.status = 'awaiting_payment'
}

export function rejectBooking(bookingId, reason) {
  const booking = state.bookings.find(b => b.id === bookingId)
  if (booking) {
    booking.status = 'rejected'
    if (reason) booking.reject_reason = reason
  }
}

// ---------------------------------------------------------------------------
// Secretary — full booking history per amenity, with timeframe classification.
// Unlike bookingsForAmenity() (used for conflict-checking against residents),
// this exposes everything so the secretary has full visibility.
// ---------------------------------------------------------------------------
export function bookingTimeframe(booking) {
  const today = new Date().toISOString().slice(0, 10)
  if (['cancelled', 'rejected', 'completed'].includes(booking.status)) return 'past'
  if (booking.end_date < today) return 'past'
  if (booking.start_date <= today && today <= booking.end_date) return 'ongoing'
  return 'upcoming'
}

export function allBookingsForAmenity(amenityId) {
  return state.bookings
    .filter(b => b.amenity_id === amenityId)
    .map(b => ({ ...b, timeframe: bookingTimeframe(b) }))
    .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
}

// ---------------------------------------------------------------------------
// Recommendation engine — rule-based scoring over event type / guest count / budget
// ---------------------------------------------------------------------------
const EVENT_AFFINITY = {
  'Birthday party': { 4: 3, 5: 3, 3: 2, 10: 2 },
  'Wedding function': { 1: 3, 10: 1 },
  'Family gathering': { 3: 3, 5: 2, 4: 2 },
  'Movie / watch party': { 7: 3 },
  'Kids party': { 3: 3, 4: 2, 5: 1 },
  'Guests staying over': { 2: 3 },
  'Small meeting': { 1: 2, 7: 1 },
  'Sports session': { 6: 3 },
}

export function recommend({ eventType, guests, budget, hours = 3 }) {
  const candidates = state.amenities.filter(a => isBookable(a) && a.status === 'available')

  const scored = candidates.map(a => {
    let score = 0
    const affinity = EVENT_AFFINITY[eventType]?.[a.id] || 0
    score += affinity * 10

    if (a.capacity && guests) {
      if (a.capacity >= guests) score += 15 - Math.min(15, (a.capacity - guests) * 0.3)
      else score -= 20 // too small
    }

    const units = a.pricing.type === 'hourly' ? hours : 1
    const price = calculatePrice(a, units)
    if (budget) {
      if (price <= budget) score += 10 - Math.min(10, (budget - price) / budget * 10)
      else score -= 15
    }

    return { amenity: a, score, estimatedPrice: price }
  })

  return scored
    .filter(s => s.score > -10)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
}

export const EVENT_TYPES = Object.keys(EVENT_AFFINITY)