// ── Phone number helpers ────────────────────────────────────────────
// Storage format in the DB:      +91XXXXXXXXXX   (no space)
// Display format in the UI:      +91 XXXXXXXXXX  (single space)
// Input fields only ever collect the 10 local digits; the +91 prefix
// is shown as a fixed, non-editable label next to the input.

/**
 * Strip anything that isn't a digit and cap at `max` digits (default 10).
 * Use this on every keystroke of a raw phone-number input.
 */
export function digitsOnly(value, max = 10) {
  return String(value || '').replace(/\D/g, '').slice(0, max)
}

/**
 * Turn 10 raw digits into the value that should be saved/sent to the
 * backend, e.g. "9876543210" -> "+919876543210".
 * Returns '' if there aren't 10 digits to work with.
 */
export function toStoredPhone(digits) {
  const d = digitsOnly(digits)
  return d.length === 10 ? `+91${d}` : ''
}

/**
 * Pull just the 10 local digits back out of any stored/raw phone value,
 * e.g. "+919876543210", "919876543210" or "9876543210" -> "9876543210".
 * Used to pre-fill an editable phone input from a value that came from
 * the backend.
 */
export function extractDigits(stored) {
  const d = String(stored || '').replace(/\D/g, '')
  return d.length > 10 ? d.slice(-10) : d
}

/**
 * Format any stored/raw phone value for display, e.g.
 * "+919876543210" -> "+91 9876543210". Returns '' for empty input so
 * callers can fall back to their own placeholder (e.g. '—').
 */
export function formatPhoneDisplay(stored) {
  const d = extractDigits(stored)
  return d ? `+91 ${d}` : ''
}