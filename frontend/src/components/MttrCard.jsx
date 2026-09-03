import React from 'react';
import { Timer, Zap, CheckCircle2, Clock } from 'lucide-react';

/**
 * Priority SLA standard thresholds in hours
 */
export const SLA_TARGETS = {
  critical: 2.0,
  high: 8.0,
  medium: 24.0,
  low: 48.0
};

/**
 * Formats an MTTR/turnaround value (in hours) for display.
 * Values under one hour are shown as whole minutes (e.g. 0.5h -> 48m),
 * anything at or above one hour is shown in hours (e.g. 1.2h).
 * Returns null for null/undefined/empty values.
 */
export const formatMttrValue = (hours) => {
  if (hours === null || hours === undefined || hours === '') return null;
  const h = Number(hours);
  if (Number.isNaN(h)) return null;
  if (h < 1) {
    const mins = Math.round(h * 60);
    return { value: mins, unit: 'min', unitLabel: 'minutes', short: `${mins}m` };
  }
  return { value: h, unit: 'h', unitLabel: 'hours', short: `${h}h` };
};

/**
 * Calculates current SLA status for an active ticket
 */
export const calculateTicketSla = (ticket) => {
  if (!ticket) return { status: 'on_track', text: 'On Track', color: 'green', elapsedPercent: 0, remainingHours: 0 };

  const priority = (ticket.priority || 'medium').toLowerCase();
  const targetHours = SLA_TARGETS[priority] || 24.0;

  // Determine creation time
  let createdAt = ticket.created_at ? new Date(ticket.created_at) : null;
  if (!createdAt || isNaN(createdAt.getTime())) {
    // Try parsing from ticket ID e.g. T20250804103000
    const idStr = String(ticket.id || '');
    if (/^T\d{8}\./.test(idStr)) {
      // Current format T{YYYYMMDD}.{seq} — only the creation date is encoded
      createdAt = new Date(`${idStr.substring(1, 5)}-${idStr.substring(5, 7)}-${idStr.substring(7, 9)}T00:00:00Z`);
    } else if (idStr.startsWith('T20') && idStr.length >= 15) {
      const yr = idStr.substring(1, 5);
      const mo = idStr.substring(5, 7);
      const dy = idStr.substring(7, 9);
      const hr = idStr.substring(9, 11);
      const mn = idStr.substring(11, 13);
      createdAt = new Date(`${yr}-${mo}-${dy}T${hr}:${mn}:00Z`);
    }
  }

  if (!createdAt || isNaN(createdAt.getTime())) {
    return { status: 'on_track', text: 'On Track', color: 'green', elapsedPercent: 25, remainingHours: targetHours };
  }

  const isResolved = ['completed', 'resolved', 'closed'].includes((ticket.status || '').toLowerCase());
  
  if (isResolved) {
    let resolvedAt = ticket.resolved_at ? new Date(ticket.resolved_at) : null;
    let durationHours = null;
    if (resolvedAt && !isNaN(resolvedAt.getTime())) {
      durationHours = Math.max(0.1, (resolvedAt.getTime() - createdAt.getTime()) / (1000 * 60 * 60));
    } else {
      durationHours = 0;
    }

    if (durationHours <= targetHours) {
      return { 
        status: 'resolved', 
        text: 'SLA Met', 
        color: 'blue', 
        isMet: true, 
        elapsedPercent: 100, 
        remainingHours: 0,
        durationHours: durationHours.toFixed(1)
      };
    } else {
      const overdue = Math.round(durationHours - targetHours);
      return { 
        status: 'breached', 
        text: `SLA Breached (+${overdue}h)`, 
        color: 'red', 
        isMet: false, 
        elapsedPercent: 100, 
        remainingHours: 0,
        durationHours: durationHours.toFixed(1)
      };
    }
  }

  const elapsedMs = Date.now() - createdAt.getTime();
  const elapsedHours = Math.max(0.1, elapsedMs / (1000 * 60 * 60));
  const elapsedPercent = Math.min(Math.round((elapsedHours / targetHours) * 100), 100);
  const remainingHours = Math.max(0, targetHours - elapsedHours);

  if (elapsedHours > targetHours) {
    const overdueHours = Math.round(elapsedHours - targetHours);
    return {
      status: 'breached',
      text: overdueHours > 0 ? `SLA Overdue (+${overdueHours}h)` : 'SLA Breached',
      color: 'red',
      isMet: false,
      elapsedPercent: 100,
      remainingHours: 0
    };
  } else if (elapsedPercent >= 70) {
    return {
      status: 'approaching',
      text: `${remainingHours.toFixed(1)}h SLA remaining`,
      color: 'amber',
      isMet: true,
      elapsedPercent,
      remainingHours
    };
  } else {
    return {
      status: 'on_track',
      text: `On Track (${remainingHours.toFixed(1)}h left)`,
      color: 'green',
      isMet: true,
      elapsedPercent,
      remainingHours
    };
  }
};

/**
 * MttrCard Component
 */
const MttrCard = ({ mttrData, isTechnician = true, className = '' }) => {
  if (!mttrData) {
    return null;
  }

  const {
    overall_mttr_hours = null,
    personal_mttr_hours = null,
    avg_work_time_hours = null,
    work_time_logged_count = 0,
    by_priority = {}
  } = mttrData;

  const priorities = [
    { key: 'Critical', label: 'Critical', color: 'bg-red-500', text: 'text-red-600', border: 'border-red-200' },
    { key: 'High', label: 'High', color: 'bg-orange-500', text: 'text-orange-600', border: 'border-orange-200' },
    { key: 'Medium', label: 'Medium', color: 'bg-yellow-500', text: 'text-yellow-600', border: 'border-yellow-200' },
    { key: 'Low', label: 'Low', color: 'bg-blue-500', text: 'text-blue-600', border: 'border-blue-200' }
  ];

  // Max MTTR across tiers — scales the gauge rings. Only use real values (not null).
  const maxMttrHours = Math.max(
    ...priorities.map(p => Number(by_priority[p.key]?.mttr_hours ?? 0)),
    1
  );

  // Pre-format MTTR values so sub-hour durations render in minutes.
  const personalMttr = formatMttrValue(personal_mttr_hours);
  const overallMttr = formatMttrValue(overall_mttr_hours);
  const criticalMttr = formatMttrValue(by_priority.Critical?.mttr_hours);
  const workTimeMttr = formatMttrValue(avg_work_time_hours);

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <Timer className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              Mean Time to Resolution (MTTR)
            </h2>
            <p className="text-xs text-gray-500">
              {isTechnician
                ? 'Average ticket resolution speed by priority tier'
                : 'Expected turnaround times and historical resolution speed'}
            </p>
          </div>
        </div>

      </div>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-blue-700 mb-1 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" />
            {isTechnician ? 'Your Avg Resolution' : 'Personal MTTR'}
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-blue-900">
              {personalMttr ? personalMttr.value : '—'}
            </span>
            {personalMttr && <span className="text-sm font-semibold text-blue-700">{personalMttr.unitLabel}</span>}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-700 mb-1 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {isTechnician ? 'Overall MTTR' : 'Overall Turnaround'}
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-emerald-900">
              {overallMttr ? overallMttr.value : '—'}
            </span>
            {overallMttr && <span className="text-sm font-semibold text-emerald-700">{overallMttr.unitLabel}</span>}
          </div>
          <p className="text-xs text-emerald-600/80 mt-1">
            {isTechnician ? 'Average resolution time across all tickets' : 'Average turnaround across all your tickets'}
          </p>
        </div>

        <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-violet-50 border border-purple-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-purple-700 mb-1 flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5" />
            {isTechnician ? 'Critical Ticket MTTR' : 'Emergency Turnaround'}
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-purple-900">
              {criticalMttr ? criticalMttr.value : '—'}
            </span>
            {criticalMttr && <span className="text-sm font-semibold text-purple-700">{criticalMttr.unitLabel}</span>}
          </div>
        </div>

        {/* Avg Work Time — actual technician effort (independent of customer wait / MTTR) */}
        <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-700 mb-1 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            Avg Work Time
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-amber-900">
              {workTimeMttr ? workTimeMttr.value : '—'}
            </span>
            {workTimeMttr && <span className="text-sm font-semibold text-amber-700">{workTimeMttr.unitLabel}</span>}
          </div>
          <p className="text-xs text-amber-600/80 mt-1">
            {isTechnician ? 'Hands-on effort per ticket' : 'Technician effort per ticket'}
            {work_time_logged_count > 0 ? ` • ${work_time_logged_count} logged` : ''}
          </p>
        </div>
      </div>

      {/* Breakdown by Priority with Radial Gauge Speedometers */}
      <div className="border-t border-gray-100 pt-5">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600 flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5 text-[#00ABE4]" />
            {isTechnician ? 'Priority Tier Speedometer' : 'Turnaround Time by Tier'}
          </h4>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {priorities.map(({ key, label, text, border }) => {
            const data = by_priority[key] || {};
            // null means no resolved tickets yet — show "no data" state
            const hours = data.mttr_hours != null ? Number(data.mttr_hours) : null;
            const percentage = hours !== null ? Math.min(Math.round((hours / maxMttrHours) * 100), 100) : 0;
            
            // SVG circular progress calculation
            const radius = 32;
            const circumference = 2 * Math.PI * radius;
            const strokeDashoffset = circumference - (percentage / 100) * circumference;

            const strokeColor = key === 'Critical' ? '#EF4444' : key === 'High' ? '#F97316' : key === 'Medium' ? '#EAB308' : '#3B82F6';

            return (
              <div key={key} className={`p-4 rounded-xl border bg-white shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center ${border}`}>
                <div className="flex items-center justify-between w-full mb-2">
                  <span className={`text-xs font-bold ${text}`}>{label}</span>
                </div>

                {/* Circular Gauge Meter */}
                <div className="relative w-20 h-20 my-1 flex items-center justify-center">
                  <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 80 80">
                    {/* Background circle */}
                    <circle
                      cx="40"
                      cy="40"
                      r={radius}
                      className="stroke-gray-100"
                      strokeWidth="6"
                      fill="transparent"
                    />
                    {/* Progress circle */}
                    <circle
                      cx="40"
                      cy="40"
                      r={radius}
                      stroke={strokeColor}
                      strokeWidth="6"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      fill="transparent"
                      className="transition-all duration-700 ease-out"
                    />
                  </svg>
                  {/* Center Text */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-base font-extrabold text-gray-900 tracking-tight">
                      {hours !== null ? formatMttrValue(hours)?.short : '—'}
                    </span>
                    <span className="text-[9px] font-semibold text-gray-400 uppercase">MTTR</span>
                  </div>
                </div>

                {/* Resolved Count Badge */}
                <div className="mt-2 w-full">
                  {hours !== null ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full w-full justify-center">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>{data.resolved_count ?? 0} resolved</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[11px] font-medium text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full w-full justify-center">
                      No resolved tickets yet
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default MttrCard;
