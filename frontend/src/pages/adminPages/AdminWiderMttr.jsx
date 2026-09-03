import { useState, useEffect } from 'react';
import { 
  Timer, 
  ShieldCheck, 
  TrendingDown, 
  TrendingUp,
  BarChart3, 
  Clock, 
  Award, 
  RefreshCw, 
  AlertCircle, 
  Download, 
  Zap, 
  Layers 
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { formatMttrValue } from '../../components/MttrCard';
import { adminService } from '../../services/adminService';

const AdminWiderMttr = () => {
  const [mttrData, setMttrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadWiderMttr = async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError('');

      const res = await adminService.getWiderMttrReport();
      setMttrData(res);
    } catch (err) {
      console.error('Failed to load wider MTTR data:', err);
      setError('Unable to load wider MTTR analytics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadWiderMttr();
  }, []);

  // Derived values — computed from API data only, no hardcoded fallbacks
  const globalMttr    = mttrData?.global_mttr_hours ?? null;
  const targetMttr    = mttrData?.target_mttr_hours ?? null;
  const slaRate       = mttrData?.sla_compliance_rate ?? null;
  const auditedCount  = mttrData?.total_audited_tickets ?? null;

  // MTTR display helpers — sub-hour durations render as minutes.
  const fmtMttrText = (hours) => {
    const f = formatMttrValue(hours);
    return f ? `${f.value} ${f.unitLabel}` : '—';
  };
  const fmtMttrShort = (hours) => {
    const f = formatMttrValue(hours);
    return f ? f.short : '—';
  };

  // Peak velocity shift = the shift with the lowest mttr_hours
  const fastestShift  = mttrData?.by_shift?.length
    ? [...mttrData.by_shift].sort((a, b) => a.mttr_hours - b.mttr_hours)[0]
    : null;

  // How much faster than target (only show when we have real data)
  const fasterPct = (globalMttr !== null && targetMttr)
    ? Math.round(((targetMttr - globalMttr) / targetMttr) * 100)
    : null;

  // Priority chart — only use API values, no inline fallbacks
  const priorityChartData = [
    {
      priority: 'Critical (P1)',
      actual: mttrData?.by_priority?.Critical?.actual_mttr_hours ?? null,
      target: mttrData?.by_priority?.Critical?.target_hours ?? null,
    },
    {
      priority: 'High (P2)',
      actual: mttrData?.by_priority?.High?.actual_mttr_hours ?? null,
      target: mttrData?.by_priority?.High?.target_hours ?? null,
    },
    {
      priority: 'Medium (P3)',
      actual: mttrData?.by_priority?.Medium?.actual_mttr_hours ?? null,
      target: mttrData?.by_priority?.Medium?.target_hours ?? null,
    },
    {
      priority: 'Low (P4)',
      actual: mttrData?.by_priority?.Low?.actual_mttr_hours ?? null,
      target: mttrData?.by_priority?.Low?.target_hours ?? null,
    },
  ].filter(d => d.actual !== null);   // hide bars until data arrives

  const handleExportExecutiveReport = () => {
    if (!mttrData) return;

    const reportContent = `=====================================================
TEAMLOGIC AUTOTASK EXECUTIVE MTTR & SLA GOVERNANCE
Generated on: ${new Date().toLocaleString()}
=====================================================

1. GLOBAL FLEET METRICS
- Global Fleet MTTR: ${fmtMttrText(mttrData.global_mttr_hours)} (SLA Target: ${mttrData.target_mttr_hours} Hours)
- SLA Compliance Rate: ${mttrData.sla_compliance_rate}%
- Audited Operational Tickets: ${mttrData.total_audited_tickets}

2. RESOLUTION VELOCITY BY SHIFT
${(mttrData.by_shift || []).map(s => `  * ${s.shift}: MTTR ${fmtMttrShort(s.mttr_hours)} | Resolved: ${s.tickets_resolved} | SLA: ${s.sla_rate}% (Active Techs: ${s.active_techs})`).join('\n')}

3. RESOLUTION SPEED BY CATEGORY
${(mttrData.by_category || []).map(c => `  * ${c.category}: MTTR ${fmtMttrShort(c.mttr_hours)} | Tickets: ${c.tickets} | SLA: ${c.sla_compliance}%`).join('\n')}

4. TOP TECHNICIAN PERFORMANCE LEADERBOARD
${(mttrData.technician_leaderboard || []).map((t, idx) => `  #${idx + 1} ${t.name} (${t.shift}): MTTR ${fmtMttrShort(t.mttr_hours)} | Resolved: ${t.resolved} | SLA: ${t.sla_rate}% | Skills: ${t.skills}`).join('\n')}
=====================================================`;

    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href  = url;
    link.download = `Executive_MTTR_Report_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen">
          <Header />
          <main className="p-6 md:p-8 flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-purple-600 mx-auto" />
              <p className="text-sm text-gray-500 font-medium">Loading MTTR analytics…</p>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <Timer className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center flex-wrap gap-2">
                    <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                      MTTR Reports
                    </h1>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                      <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                      Executive Leadership Scope
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mt-0.5">
                    Multi-shift Mean Time to Resolution, technician speed rankings, category SLA health, and operational performance trends.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleExportExecutiveReport}
                  disabled={!mttrData}
                  className="flex items-center space-x-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Executive Report</span>
                </button>

                <button
                  onClick={() => loadWiderMttr(true)}
                  disabled={loading || refreshing}
                  className="p-2.5 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  title="Refresh MTTR"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-[#00ABE4]' : ''}`} />
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Top 4 Executive KPI Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

              {/* 1. Global MTTR */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Fleet Global MTTR</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">
                    {globalMttr !== null ? fmtMttrText(globalMttr) : '—'}
                  </h3>
                  {fasterPct !== null ? (
                    <p className={`text-xs font-medium mt-0.5 flex items-center gap-1 ${fasterPct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {fasterPct >= 0
                        ? <><TrendingDown className="w-3.5 h-3.5" /> {fasterPct}% Faster than Target ({targetMttr}h)</>
                        : <><TrendingUp className="w-3.5 h-3.5" /> {Math.abs(fasterPct)}% Slower than Target ({targetMttr}h)</>
                      }
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400 mt-0.5">SLA Target: {targetMttr}h</p>
                  )}
                </div>
                <div className="w-11 h-11 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                  <Timer className="w-5 h-5" />
                </div>
              </div>

              {/* 2. SLA Compliance Rate */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">SLA Compliance Rate</p>
                  <h3 className={`text-2xl font-bold mt-1 ${slaRate !== null && slaRate >= 95 ? 'text-emerald-600' : slaRate !== null ? 'text-amber-500' : 'text-gray-400'}`}>
                    {slaRate !== null ? `${slaRate}%` : '—'}
                  </h3>
                  <p className={`text-xs font-medium mt-0.5 ${slaRate !== null && slaRate >= 95 ? 'text-emerald-600' : slaRate !== null ? 'text-amber-500' : 'text-gray-400'}`}>
                    {slaRate !== null
                      ? slaRate >= 95 ? 'Above 95% SLA Target' : 'Below 95% SLA Target'
                      : 'No data yet'}
                  </p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <ShieldCheck className="w-5 h-5" />
                </div>
              </div>

              {/* 3. Total Audited Tickets */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Audited Tickets</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">
                    {auditedCount !== null ? auditedCount : '—'}
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">Historical resolution cycles</p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-blue-50 text-[#00ABE4] flex items-center justify-center">
                  <Zap className="w-5 h-5" />
                </div>
              </div>

              {/* 4. Peak Velocity Shift — fully from API */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Peak Velocity Shift</p>
                  <h3 className="text-2xl font-bold text-amber-600 mt-1">
                    {fastestShift ? fastestShift.shift : '—'}
                  </h3>
                  <p className="text-xs text-amber-600 font-medium mt-0.5">
                    {fastestShift ? `${fmtMttrText(fastestShift.mttr_hours)} Average Turnaround` : 'No shift data yet'}
                  </p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Clock className="w-5 h-5" />
                </div>
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

              {/* Bar Chart: Actual MTTR vs SLA Limit by Priority */}
              <div className="lg:col-span-7 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-purple-600" />
                      <h3 className="text-base font-bold text-gray-900">MTTR Speed vs SLA Limits by Priority</h3>
                    </div>
                    <span className="text-xs text-gray-500 font-medium">Hours</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-4">
                    Compares departmental actual resolution duration against contractual SLA breach thresholds.
                  </p>
                </div>

                <div className="h-72 w-full mt-2">
                  {priorityChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={priorityChartData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="priority" axisLine={false} tickLine={false} tick={{ fill: '#475569', fontSize: 12, fontWeight: 500 }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderRadius: '10px', border: 'none', color: '#fff' }}
                          itemStyle={{ color: '#fff', fontSize: '12px' }}
                          formatter={(value, name) => {
                            const fmt = formatMttrValue(Number(value));
                            return [fmt ? `${fmt.value} ${fmt.unitLabel}` : `${value} hours`, name];
                          }}
                        />
                        <Legend verticalAlign="top" align="right" iconType="circle" wrapperStyle={{ fontSize: '12px', paddingBottom: '10px' }} />
                        <Bar dataKey="actual" name="Actual MTTR" fill="#8b5cf6" radius={[6, 6, 0, 0]} maxBarSize={38} />
                        <Bar dataKey="target" name="SLA Limit"   fill="#cbd5e1" radius={[6, 6, 0, 0]} maxBarSize={38} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-gray-400">
                      No priority data available yet
                    </div>
                  )}
                </div>
              </div>

              {/* Shift Turnaround Performance */}
              <div className="lg:col-span-5 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Clock className="w-5 h-5 text-[#00ABE4]" />
                      <h3 className="text-base font-bold text-gray-900">Shift MTTR Velocity</h3>
                    </div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                      {mttrData?.by_shift?.length ?? 0} Shifts
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-4">
                    Resolution velocity and SLA delivery performance grouped by working shift rotation.
                  </p>
                </div>

                <div className="space-y-3.5">
                  {(mttrData?.by_shift || []).length > 0 ? (
                    (mttrData.by_shift).map((shift, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-gray-100 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-gray-900">{shift.shift}</span>
                          <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                            {fmtMttrShort(shift.mttr_hours)} MTTR
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                          <span>{shift.tickets_resolved} Tickets Resolved</span>
                          <span className="text-emerald-600 font-semibold">{shift.sla_rate}% SLA</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1.5 overflow-hidden">
                          <div
                            className="bg-purple-600 h-1.5 rounded-full"
                            style={{ width: `${Math.min(shift.sla_rate, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-6">No shift data available yet</p>
                  )}
                </div>
              </div>

            </div>

            {/* Technician Performance Leaderboard & Category Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

              {/* Leaderboard Table */}
              <div className="lg:col-span-7 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Award className="w-5 h-5 text-amber-500" />
                    <h3 className="text-base font-bold text-gray-900">Technician MTTR Performance Leaderboard</h3>
                  </div>
                  <span className="text-xs font-semibold text-gray-500">Ranked by Velocity</span>
                </div>

                <div className="overflow-x-auto">
                  {(mttrData?.technician_leaderboard || []).length > 0 ? (
                    <table className="w-full text-left text-sm text-gray-600">
                      <thead className="bg-gray-50 text-xs uppercase font-semibold text-gray-500">
                        <tr>
                          <th className="py-2.5 px-3">Rank</th>
                          <th className="py-2.5 px-3">Technician</th>
                          <th className="py-2.5 px-3">Shift</th>
                          <th className="py-2.5 px-3">Avg MTTR</th>
                          <th className="py-2.5 px-3">Resolved</th>
                          <th className="py-2.5 px-3">SLA %</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 text-xs">
                        {mttrData.technician_leaderboard.map((t, idx) => (
                          <tr key={idx} className="hover:bg-gray-50/80 transition-colors">
                            <td className="py-3 px-3 font-bold text-gray-900">
                              <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                                idx === 0 ? 'bg-amber-100 text-amber-800' : idx === 1 ? 'bg-gray-200 text-gray-800' : 'bg-gray-100 text-gray-600'
                              }`}>
                                #{idx + 1}
                              </span>
                            </td>
                            <td className="py-3 px-3 font-semibold text-gray-900">
                              {t.name}
                              <p className="text-[11px] text-gray-400 font-normal">{t.skills}</p>
                            </td>
                            <td className="py-3 px-3 text-gray-700">{t.shift}</td>
                            <td className="py-3 px-3 font-bold text-purple-700">{fmtMttrShort(t.mttr_hours)}</td>
                            <td className="py-3 px-3 text-gray-700">{t.resolved}</td>
                            <td className="py-3 px-3 font-semibold text-emerald-600">{t.sla_rate}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-8">No technician data available yet</p>
                  )}
                </div>
              </div>

              {/* Category MTTR Matrix */}
              <div className="lg:col-span-5 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-indigo-600" />
                    <h3 className="text-base font-bold text-gray-900">Category Turnaround Matrix</h3>
                  </div>
                  <span className="text-xs font-semibold text-gray-500">Domain Velocity</span>
                </div>

                <div className="space-y-3">
                  {(mttrData?.by_category || []).length > 0 ? (
                    mttrData.by_category.map((cat, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-gray-800">{cat.category}</h4>
                          <p className="text-[11px] text-gray-500">
                            {cat.tickets} Closed Requests • {cat.sla_compliance}% On-Time
                          </p>
                        </div>
                        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                          {fmtMttrShort(cat.mttr_hours)} MTTR
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-6">No category data available yet</p>
                  )}
                </div>
              </div>

            </div>

          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminWiderMttr;
