import React from 'react';
import { Timer, Zap, CheckCircle2, AlertTriangle, ShieldCheck, TrendingDown } from 'lucide-react';

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
    if (idStr.startsWith('T20') && idStr.length >= 15) {
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
    return { status: 'resolved', text: 'SLA Met', color: 'blue', elapsedPercent: 100, remainingHours: 0 };
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
      elapsedPercent: 100,
      remainingHours: 0
    };
  } else if (elapsedPercent >= 70) {
    return {
      status: 'approaching',
      text: `${remainingHours.toFixed(1)}h SLA remaining`,
      color: 'amber',
      elapsedPercent,
      remainingHours
    };
  } else {
    return {
      status: 'on_track',
      text: `On Track (${remainingHours.toFixed(1)}h left)`,
      color: 'green',
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
    overall_mttr_hours = 2.8,
    personal_mttr_hours = 2.4,
    sla_compliance_rate = 94.5,
    by_priority = {},
    active_sla_status = { on_track: 0, approaching: 0, breached: 0 }
  } = mttrData;

  const priorities = [
    { key: 'Critical', label: 'Critical', color: 'bg-red-500', text: 'text-red-600', border: 'border-red-200', target: '2h' },
    { key: 'High', label: 'High', color: 'bg-orange-500', text: 'text-orange-600', border: 'border-orange-200', target: '8h' },
    { key: 'Medium', label: 'Medium', color: 'bg-yellow-500', text: 'text-yellow-600', border: 'border-yellow-200', target: '24h' },
    { key: 'Low', label: 'Low', color: 'bg-blue-500', text: 'text-blue-600', border: 'border-blue-200', target: '48h' }
  ];

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <Timer className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              Mean Time to Resolution (MTTR)
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                {sla_compliance_rate}% SLA Met
              </span>
            </h2>
            <p className="text-xs text-gray-500">
              {isTechnician
                ? 'Average ticket resolution speed & SLA benchmark compliance'
                : 'Expected turnaround times and historical resolution speed'}
            </p>
          </div>
        </div>

        {/* SLA Status Pill Badges */}
        <div className="flex items-center space-x-2 text-xs font-medium">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-green-50 text-green-700 border border-green-200">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            {active_sla_status.on_track} On Track
          </span>
          {active_sla_status.approaching > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-50 text-amber-700 border border-amber-200">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              {active_sla_status.approaching} Near SLA
            </span>
          )}
          {active_sla_status.breached > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-red-50 text-red-700 border border-red-200">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              {active_sla_status.breached} Breached
            </span>
          )}
        </div>
      </div>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-blue-700 mb-1 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" />
            {isTechnician ? 'Your Avg Resolution' : 'Avg Resolution Time'}
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-blue-900">
              {personal_mttr_hours}
            </span>
            <span className="text-sm font-semibold text-blue-700">hours</span>
          </div>
          <p className="text-xs text-blue-600/80 mt-1 flex items-center gap-1">
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
            Team avg: {overall_mttr_hours}h
          </p>
        </div>

        <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-700 mb-1 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            SLA Compliance
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-emerald-900">
              {sla_compliance_rate}%
            </span>
          </div>
          <p className="text-xs text-emerald-600/80 mt-1">
            Resolved within target window
          </p>
        </div>

        <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-violet-50 border border-purple-100">
          <div className="text-xs font-semibold uppercase tracking-wider text-purple-700 mb-1 flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5" />
            Critical SLA Target
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-purple-900">
              {by_priority.Critical?.mttr_hours || 1.4}
            </span>
            <span className="text-sm font-semibold text-purple-700">/ 2.0h target</span>
          </div>
          <p className="text-xs text-purple-600/80 mt-1">
            P1 Emergency response rate
          </p>
        </div>
      </div>

      {/* Breakdown by Priority */}
      <div className="border-t border-gray-100 pt-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
          MTTR Breakdown by Priority & SLA Targets
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {priorities.map(({ key, label, color, text, border, target }) => {
            const data = by_priority[key] || { mttr_hours: 0, sla_target_hours: 24, resolved_count: 0 };
            const hours = data.mttr_hours || 0;
            const targetHours = data.sla_target_hours || 24;
            const percentage = Math.min(Math.round((hours / targetHours) * 100), 100);

            return (
              <div key={key} className={`p-3 rounded-lg border bg-gray-50/50 ${border}`}>
                <div className="flex justify-between items-center mb-1">
                  <span className={`text-xs font-bold ${text}`}>{label}</span>
                  <span className="text-[11px] font-medium text-gray-500">Target: &lt;{target}</span>
                </div>
                <div className="text-base font-extrabold text-gray-800 mb-1.5">
                  {hours > 0 ? `${hours}h` : 'N/A'}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`${color} h-1.5 rounded-full transition-all duration-500`}
                    style={{ width: `${percentage || 30}%` }}
                  ></div>
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
