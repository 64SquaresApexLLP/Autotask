/**
 * Authoritative Canonical Date and Time Utilities for CTTC.
 * 
 * Solves the ECMAScript ISO parsing problem where naive date strings without
 * timezone indicator (e.g. "2026-10-15T09:06:18") are incorrectly parsed as
 * local browser time instead of canonical UTC.
 */

export const SLA_TARGETS = {
  critical: 2.0,
  high: 8.0,
  medium: 24.0,
  low: 48.0
};

/**
 * Parses any date value safely into a valid JavaScript Date object representing
 * the canonical UTC instant.
 *
 * @param {string|number|Date} dateVal - Date string, timestamp, or Date instance
 * @returns {Date|null} Valid Date object or null if unparseable
 */
export const parseIsoDate = (dateVal) => {
  if (!dateVal) return null;

  if (dateVal instanceof Date) {
    return isNaN(dateVal.getTime()) ? null : dateVal;
  }

  if (typeof dateVal === 'number') {
    const d = new Date(dateVal);
    return isNaN(d.getTime()) ? null : d;
  }

  let str = String(dateVal).trim();
  if (!str) return null;

  // Handle ticket number fallback e.g. T20261015.0013 or T20250804103000
  if (/^T\d{8}\./.test(str)) {
    const yr = str.substring(1, 5);
    const mo = str.substring(5, 7);
    const dy = str.substring(7, 9);
    str = `${yr}-${mo}-${dy}T00:00:00Z`;
  } else if (str.startsWith('T20') && str.length >= 15 && !str.includes('-')) {
    const yr = str.substring(1, 5);
    const mo = str.substring(5, 7);
    const dy = str.substring(7, 9);
    const hr = str.substring(9, 11);
    const mn = str.substring(11, 13);
    str = `${yr}-${mo}-${dy}T${hr}:${mn}:00Z`;
  }

  // Normalize space separator to ISO 'T'
  if (str.includes(' ') && !str.includes('T')) {
    str = str.replace(' ', 'T');
  }

  // Check if string has timezone indicator (Z or +/-HH:MM or +/-HHMM)
  const hasTimezone = /Z$|[+-]\d{2}(:?\d{2})?$/i.test(str);
  if (!hasTimezone) {
    // If naive ISO format, treat as canonical UTC instant by appending 'Z'
    str = `${str}Z`;
  }

  const parsed = new Date(str);
  return isNaN(parsed.getTime()) ? null : parsed;
};

/**
 * Format a date value to the user's localized date string (e.g. "10/15/2026")
 */
export const formatLocalDate = (dateVal, fallback = '—') => {
  const d = parseIsoDate(dateVal);
  if (!d) return fallback;
  return d.toLocaleDateString();
};

/**
 * Format a date value to the user's localized date and time string
 */
export const formatLocalDateTime = (dateVal, fallback = '—') => {
  const d = parseIsoDate(dateVal);
  if (!d) return fallback;
  return d.toLocaleString();
};

/**
 * Calculate elapsed duration in hours between creation and current time (or resolution).
 *
 * @param {string|Date} createdAt - Ticket creation timestamp
 * @param {string|Date} [resolvedAt] - Optional resolution timestamp
 * @returns {number} Elapsed hours
 */
export const getElapsedHours = (createdAt, resolvedAt = null) => {
  const start = parseIsoDate(createdAt);
  if (!start) return 0;

  const end = resolvedAt ? parseIsoDate(resolvedAt) : new Date();
  if (!end) return 0;

  const elapsedMs = Math.max(0, end.getTime() - start.getTime());
  return Math.max(0.01, elapsedMs / (1000 * 60 * 60));
};

/**
 * Authoritative SLA calculation shared between MttrCard, dashboard, and reports.
 */
export const calculateSlaStatus = (priority, createdAt, resolvedAt = null, status = 'Open') => {
  const pKey = (priority || 'medium').toLowerCase();
  const targetHours = SLA_TARGETS[pKey] || 24.0;
  const start = parseIsoDate(createdAt);

  if (!start) {
    return {
      status: 'on_track',
      text: 'On Track',
      color: 'green',
      elapsedHours: 0,
      targetHours,
      elapsedPercent: 0,
      remainingHours: targetHours,
      isMet: true
    };
  }

  const isResolved = ['completed', 'resolved', 'closed'].includes((status || '').toLowerCase());
  const elapsedHours = getElapsedHours(start, isResolved ? resolvedAt : null);

  if (isResolved) {
    const isMet = elapsedHours <= targetHours;
    if (isMet) {
      return {
        status: 'resolved',
        text: 'SLA Met',
        color: 'blue',
        elapsedHours: Number(elapsedHours.toFixed(1)),
        targetHours,
        elapsedPercent: 100,
        remainingHours: 0,
        isMet: true
      };
    } else {
      const overdueHours = Math.round(elapsedHours - targetHours);
      return {
        status: 'breached',
        text: `SLA Breached (+${overdueHours}h)`,
        color: 'red',
        elapsedHours: Number(elapsedHours.toFixed(1)),
        targetHours,
        elapsedPercent: 100,
        remainingHours: 0,
        isMet: false
      };
    }
  }

  // Active Ticket
  const isBreached = elapsedHours > targetHours;
  const elapsedPercent = Math.min(100, Math.round((elapsedHours / targetHours) * 100));
  const remainingHours = Math.max(0, Number((targetHours - elapsedHours).toFixed(1)));

  if (isBreached) {
    const overdueHours = (elapsedHours - targetHours).toFixed(1);
    return {
      status: 'breached',
      text: `SLA Breached (+${overdueHours}h)`,
      color: 'red',
      elapsedHours: Number(elapsedHours.toFixed(1)),
      targetHours,
      elapsedPercent: 100,
      remainingHours: 0,
      isMet: false
    };
  }

  // Warning if approaching SLA limit (>= 75% elapsed)
  if (elapsedPercent >= 75) {
    return {
      status: 'approaching',
      text: `Approaching SLA (${remainingHours}h left)`,
      color: 'amber',
      elapsedHours: Number(elapsedHours.toFixed(1)),
      targetHours,
      elapsedPercent,
      remainingHours,
      isMet: true
    };
  }

  return {
    status: 'on_track',
    text: `On Track (${remainingHours}h left)`,
    color: 'green',
    elapsedHours: Number(elapsedHours.toFixed(1)),
    targetHours,
    elapsedPercent,
    remainingHours,
    isMet: true
  };
};
