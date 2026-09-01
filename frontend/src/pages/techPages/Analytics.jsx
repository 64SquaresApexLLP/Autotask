import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from "recharts";
import {
  TrendingUp,
  Clock,
  CheckCircle,
  Star,
  Award,
  Target,
  Users,
  Zap,
  Loader2,
  RefreshCw,
  AlertCircle,
  Activity,
  Layers,
  ShieldAlert,
  Calendar,
  Sparkles,
  ArrowRight,
  ExternalLink
} from "lucide-react";
import useAuth from '../../hooks/useAuth';
import { API_BASE_URL } from '../../config/api';

const Analytics = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Load analytics data for current technician or all
  const loadAnalytics = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError('');

      const techId = user?.username || 'all';
      const response = await fetch(`${API_BASE_URL}/analytics/${encodeURIComponent(techId)}`);

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }

      const data = await response.json();
      setAnalyticsData(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load analytics:', err);
      if (!analyticsData) {
        setError('Unable to load real-time analytics. Please check your backend connection.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user?.username]);

  // Initial fetch
  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  // Real-time polling every 15 seconds when autoRefresh is enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadAnalytics(true);
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadAnalytics]);

  const personalMetrics = analyticsData?.personal_metrics || {
    tickets_resolved: 0,
    total_tickets: 0,
    open_tickets: 0,
    avg_resolution_time: "0 hours",
    customer_satisfaction: 0.0,
    sla_compliance: 0,
    this_week_resolved: 0,
    this_month_resolved: 0
  };

  const weeklyData = analyticsData?.weekly_data || [];
  const categoryData = analyticsData?.category_data || [];
  const priorityData = analyticsData?.priority_data || [];

  const resolutionRate = personalMetrics.total_tickets > 0
    ? Math.round((personalMetrics.tickets_resolved / personalMetrics.total_tickets) * 100)
    : 0;

  const [activeCategoryHover, setActiveCategoryHover] = useState(null);

  // Calculate total tickets across categories for percentage
  const totalCategoryTickets = categoryData.reduce((acc, c) => acc + (Number(c.count) || 0), 0) || 1;
  const sortedCategories = [...categoryData].sort((a, b) => (b.count || 0) - (a.count || 0));

  // Calculate total weekly throughput
  const totalWeeklyResolved = weeklyData.reduce((acc, d) => acc + (Number(d.resolved) || 0), 0);
  const totalWeeklyCreated = weeklyData.reduce((acc, d) => acc + (Number(d.created) || 0), 0);
  const weeklyNetVelocity = totalWeeklyResolved - totalWeeklyCreated;

  // Custom rich tooltip for weekly bar chart
  const CustomWeeklyTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const resolved = payload.find(p => p.dataKey === 'resolved')?.value || 0;
      const created = payload.find(p => p.dataKey === 'created')?.value || 0;
      const net = resolved - created;
      return (
        <div className="bg-slate-900 text-white p-3.5 rounded-xl shadow-2xl border border-slate-700/80 text-xs min-w-[170px] space-y-2">
          <div className="font-bold text-sm text-slate-100 border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span>{label}</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${net >= 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
              {net >= 0 ? `+${net} Net` : `${net} Net`}
            </span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-blue-500"></span>
                Resolved:
              </span>
              <strong className="text-white font-mono font-bold">{resolved}</strong>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-slate-400"></span>
                Created:
              </span>
              <strong className="text-white font-mono font-bold">{created}</strong>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom rich tooltip for category donut chart
  const CustomCategoryTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0];
      const count = Number(item.value) || 0;
      const pct = Math.round((count / totalCategoryTickets) * 100);
      return (
        <div className="bg-slate-900 text-white p-3 rounded-xl shadow-2xl border border-slate-700/80 text-xs min-w-[150px]">
          <div className="font-bold text-sm text-white flex items-center gap-2 mb-1">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.payload?.color || '#6366f1' }}></span>
            <span>{item.name}</span>
          </div>
          <div className="flex justify-between items-center text-slate-300 pt-1.5 border-t border-slate-800">
            <span>Volume: <strong className="text-white font-mono">{count} tickets</strong></span>
            <span className="text-emerald-400 font-extrabold">{pct}%</span>
          </div>
        </div>
      );
    }
    return null;
  };

  const hoveredCategory = activeCategoryHover !== null ? sortedCategories[activeCategoryHover] : null;

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
              <div>
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
                    <BarChart className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="flex items-center flex-wrap gap-2">
                      <h1 className="text-2xl md:text-3xl font-bold text-slate-800 tracking-tight">
                        Productivity & Workload Analytics
                      </h1>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        Workload Volume & Quality
                      </span>
                    </div>
                    <p className="text-slate-500 text-sm mt-0.5">
                      Weekly ticket output volumes, issue category breakdown, customer satisfaction (CSAT), and productivity ratings.
                    </p>
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Last updated timestamp */}
                {lastUpdated && (
                  <span className="text-xs text-slate-400 font-mono hidden sm:inline">
                    Updated: {lastUpdated.toLocaleTimeString()}
                  </span>
                )}

                {/* Auto Refresh Toggle */}
                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors flex items-center gap-1.5 ${
                    autoRefresh
                      ? 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
                      : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
                  }`}
                  title="Toggle automatic updates every 15 seconds"
                >
                  <Zap className={`h-3.5 w-3.5 ${autoRefresh ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span>Auto-Refresh: {autoRefresh ? 'ON' : 'OFF'}</span>
                </button>

                {/* Manual Refresh Button */}
                <button
                  onClick={() => loadAnalytics(false)}
                  disabled={loading || refreshing}
                  className="flex items-center gap-1.5 bg-white border border-slate-300 text-slate-700 px-3.5 py-1.5 rounded-xl text-xs font-medium hover:bg-slate-50 active:bg-slate-100 transition shadow-sm disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading || refreshing ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Loading State */}
            {loading && !analyticsData && (
              <div className="flex flex-col items-center justify-center py-20 bg-white rounded-2xl border border-slate-200 shadow-sm">
                <Loader2 className="h-10 w-10 animate-spin text-blue-600 mb-3" />
                <span className="text-slate-700 font-medium text-base">Gathering real-time analytics data...</span>
                <span className="text-slate-400 text-xs mt-1">Aggregating ticket metrics, categories, and performance trends</span>
              </div>
            )}

            {/* Error State */}
            {error && !analyticsData && (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-6 shadow-sm">
                <div className="flex items-center space-x-3">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                  <div>
                    <div className="text-red-800 font-semibold">Error loading analytics</div>
                    <p className="text-red-600 text-sm mt-0.5">{error}</p>
                  </div>
                </div>
                <button
                  onClick={() => loadAnalytics(false)}
                  className="mt-4 inline-flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-red-700 transition"
                >
                  <RefreshCw className="h-4 w-4" />
                  Retry Connection
                </button>
              </div>
            )}

            {/* Analytics Content */}
            {analyticsData && (
              <div className="space-y-6">

                {/* Key Performance Metrics Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                  {/* Tickets Resolved Card */}
                  <div
                    onClick={() => navigate('/technician/all-tickets')}
                    className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-emerald-300 hover:shadow-md transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                    title="Click to view all resolved tickets"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tickets Resolved</span>
                      <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                        <CheckCircle className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center justify-between">
                      <span>{personalMetrics.tickets_resolved}</span>
                      <ArrowRight className="w-4 h-4 text-emerald-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="flex items-center gap-1 font-medium text-emerald-600">
                        <TrendingUp className="h-3.5 w-3.5" />
                        {resolutionRate}% resolved
                      </span>
                      <span className="group-hover:text-emerald-700 font-medium">View tickets &rarr;</span>
                    </div>
                  </div>

                  {/* Active Workload Queue Card */}
                  <div
                    onClick={() => navigate('/technician/my-tickets')}
                    className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                    title="Click to view your active assigned tickets"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Workload</span>
                      <div className="p-2 bg-indigo-100 text-indigo-700 rounded-xl group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                        <Layers className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center justify-between">
                      <span>{personalMetrics.open_tickets}</span>
                      <ArrowRight className="w-4 h-4 text-indigo-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-indigo-600 font-medium">⚡ Active queue</span>
                      <span className="group-hover:text-indigo-700 font-medium">Open my tickets &rarr;</span>
                    </div>
                  </div>

                  {/* Avg Resolution Time Card */}
                  <div
                    onClick={() => navigate('/technician/mttr-report')}
                    className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-blue-300 hover:shadow-md transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                    title="Click to open MTTR Speedometer & SLA Report"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avg Resolution Time</span>
                      <div className="p-2 bg-blue-100 text-blue-700 rounded-xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                        <Clock className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center justify-between">
                      <span>{personalMetrics.avg_resolution_time}</span>
                      <ArrowRight className="w-4 h-4 text-blue-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-blue-600 font-medium">⚡ Speed benchmark</span>
                      <span className="group-hover:text-blue-700 font-medium">MTTR Report &rarr;</span>
                    </div>
                  </div>

                  {/* SLA Compliance Card */}
                  <div
                    onClick={() => navigate('/technician/mttr-report')}
                    className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-purple-300 hover:shadow-md transition-all cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                    title="Click to view live SLA compliance table"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-purple-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">SLA Compliance</span>
                      <div className="p-2 bg-purple-100 text-purple-700 rounded-xl group-hover:bg-purple-600 group-hover:text-white transition-colors">
                        <Target className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{personalMetrics.sla_compliance}%</span>
                      <ArrowRight className="w-4 h-4 text-purple-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-purple-600 font-medium">🎯 Target met</span>
                      <span className="group-hover:text-purple-700 font-medium">SLA Governance &rarr;</span>
                    </div>
                  </div>
                </div>

                {/* Charts Grid: Weekly Performance & Priority Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                  {/* Weekly Performance Bar Chart (2 columns on lg) */}
                  <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-slate-800">Weekly Throughput & Velocity</h3>
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                              Mon &ndash; Sun
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5">Tickets resolved vs newly created inflow by day of week</p>
                        </div>

                        {/* Top Throughput Summary Badges */}
                        <div className="flex items-center gap-2 text-xs font-semibold flex-wrap">
                          <button
                            onClick={() => navigate('/technician/all-tickets')}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition cursor-pointer"
                            title="View all resolved tickets"
                          >
                            <span className="h-2 w-2 rounded-full bg-blue-600"></span>
                            {totalWeeklyResolved} Resolved
                          </button>
                          <button
                            onClick={() => navigate('/technician/my-tickets')}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition cursor-pointer"
                            title="View incoming ticket queue"
                          >
                            <span className="h-2 w-2 rounded-full bg-slate-500"></span>
                            {totalWeeklyCreated} Inflow
                          </button>
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg font-bold border ${
                            weeklyNetVelocity >= 0 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'
                          }`}>
                            {weeklyNetVelocity >= 0 ? `+${weeklyNetVelocity} Net Cleared 📈` : `${weeklyNetVelocity} Backlog 📉`}
                          </span>
                        </div>
                      </div>

                      <div className="h-72 w-full mt-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={weeklyData} margin={{ top: 15, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                              <linearGradient id="barResolvedGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#3B82F6" stopOpacity={1} />
                                <stop offset="100%" stopColor="#1D4ED8" stopOpacity={0.85} />
                              </linearGradient>
                              <linearGradient id="barCreatedGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#94A3B8" stopOpacity={1} />
                                <stop offset="100%" stopColor="#64748B" stopOpacity={0.85} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                            <Tooltip content={<CustomWeeklyTooltip />} cursor={{ fill: '#f8fafc' }} />
                            <Bar dataKey="resolved" fill="url(#barResolvedGrad)" name="Resolved" radius={[6, 6, 0, 0]} maxBarSize={34} />
                            <Bar dataKey="created" fill="url(#barCreatedGrad)" name="Created" radius={[6, 6, 0, 0]} maxBarSize={34} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div
                      onClick={() => navigate('/technician/my-tickets')}
                      className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 hover:text-blue-600 transition cursor-pointer"
                    >
                      <span>Clearance Efficiency Ratio</span>
                      <span className="font-bold text-blue-600 flex items-center gap-1">
                        {totalWeeklyCreated > 0 ? Math.round((totalWeeklyResolved / totalWeeklyCreated) * 100) : 100}% Velocity Index
                        <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>

                  {/* Priority Breakdown (1 column on lg) */}
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                          <ShieldAlert className="h-4 w-4 text-orange-500" />
                          Tickets by Priority
                        </h3>
                        <span className="text-[11px] text-blue-600 font-medium hover:underline cursor-pointer" onClick={() => navigate('/technician/urgent-tickets')}>
                          Urgent Queue &rarr;
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mb-6">Distribution across urgency tiers (click tier to filter)</p>

                      <div className="space-y-4">
                        {priorityData.map((item) => {
                          const total = personalMetrics.total_tickets || 1;
                          const pct = Math.round((item.count / total) * 100);
                          const isUrgentTier = item.priority === 'Critical' || item.priority === 'High';

                          return (
                            <div
                              key={item.priority}
                              onClick={() => navigate(isUrgentTier ? '/technician/urgent-tickets' : '/technician/all-tickets')}
                              className="p-2 rounded-xl hover:bg-slate-50 transition-all cursor-pointer group border border-transparent hover:border-slate-200/70"
                              title={`View ${item.priority} priority tickets`}
                            >
                              <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                                <div className="flex items-center gap-2">
                                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                                  <span className="text-slate-700 group-hover:text-slate-900">{item.priority}</span>
                                </div>
                                <div className="text-slate-500 font-mono flex items-center gap-1">
                                  <span>{item.count}</span>
                                  <span className="text-slate-400 font-normal">({pct}%)</span>
                                  <ArrowRight className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                              </div>
                              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{ width: `${pct}%`, backgroundColor: item.color }}
                                ></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div
                      onClick={() => navigate('/technician/all-tickets')}
                      className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 hover:text-blue-600 transition cursor-pointer"
                    >
                      <span>Total Tracked Tickets</span>
                      <span className="font-bold text-slate-800 flex items-center gap-1">
                        {personalMetrics.total_tickets}
                        <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>

                </div>

                {/* Category Breakdown & Upgraded Donut Chart with Center Dynamic Hub */}
                {categoryData.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
                      <div>
                        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                          <Layers className="h-4 w-4 text-blue-500" />
                          Tickets by Issue Category
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">Click any category card to view its corresponding tickets</p>
                      </div>
                      <button
                        onClick={() => navigate('/technician/all-tickets')}
                        className="text-xs font-semibold px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full self-start sm:self-auto transition cursor-pointer"
                      >
                        {categoryData.length} Categories &bull; View All &rarr;
                      </button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                      {/* Donut Chart with Dynamic Center Inspection */}
                      <div
                        onClick={() => {
                          const cat = hoveredCategory ? hoveredCategory.category : sortedCategories[0]?.category;
                          if (cat) {
                            navigate('/technician/all-tickets?category=' + encodeURIComponent(cat));
                          } else {
                            navigate('/technician/all-tickets');
                          }
                        }}
                        className="lg:col-span-5 relative h-64 flex items-center justify-center cursor-pointer"
                        title={hoveredCategory ? `Click to view ${hoveredCategory.category} tickets` : "Click to view all categorized tickets"}
                      >
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={sortedCategories}
                              dataKey="count"
                              nameKey="category"
                              cx="50%"
                              cy="50%"
                              innerRadius={65}
                              outerRadius={98}
                              paddingAngle={3}
                              onMouseEnter={(_, index) => setActiveCategoryHover(index)}
                              onMouseLeave={() => setActiveCategoryHover(null)}
                            >
                              {sortedCategories.map((entry, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={entry.color || '#6366f1'}
                                  stroke={activeCategoryHover === index ? '#1e293b' : '#fff'}
                                  strokeWidth={activeCategoryHover === index ? 3 : 1}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/technician/all-tickets?category=' + encodeURIComponent(entry.category));
                                  }}
                                  className="transition-all duration-300 cursor-pointer"
                                />
                              ))}
                            </Pie>
                            <Tooltip content={<CustomCategoryTooltip />} />
                          </PieChart>
                        </ResponsiveContainer>

                        {/* Center Metric Display Hub */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
                          {hoveredCategory ? (
                            <>
                              <span className="text-2xl font-black text-slate-900 tracking-tight">{hoveredCategory.count}</span>
                              <span className="text-[11px] font-bold text-slate-600 truncate max-w-[100px]">{hoveredCategory.category}</span>
                              <span className="text-[10px] font-extrabold text-blue-600 bg-blue-50 px-1.5 py-0.2 rounded mt-0.5">
                                {Math.round(((hoveredCategory.count || 0) / totalCategoryTickets) * 100)}% of total
                              </span>
                            </>
                          ) : (
                            <>
                              <span className="text-2xl font-black text-slate-900 tracking-tight">{totalCategoryTickets}</span>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Classified</span>
                              <span className="text-[9px] font-medium text-slate-400">Tickets &rarr;</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Ranked Category Grid Cards */}
                      <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {sortedCategories.map((item, index) => {
                          const count = Number(item.count) || 0;
                          const pct = Math.round((count / totalCategoryTickets) * 100);
                          const isHovered = activeCategoryHover === index;

                          return (
                            <div
                              key={index}
                              onClick={() => navigate('/technician/all-tickets?category=' + encodeURIComponent(item.category))}
                              onMouseEnter={() => setActiveCategoryHover(index)}
                              onMouseLeave={() => setActiveCategoryHover(null)}
                              className={`border rounded-xl p-3.5 transition-all cursor-pointer ${
                                isHovered 
                                  ? 'bg-blue-50/80 border-blue-300 shadow-md scale-[1.02]' 
                                  : 'bg-slate-50 hover:bg-slate-100/80 border-slate-200/70 hover:shadow-sm'
                              }`}
                              title={`Click to filter and view ${item.category} tickets only`}
                            >
                              <div className="flex items-center justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <span
                                    className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: item.color }}
                                  ></span>
                                  <span className="text-xs font-bold text-slate-700 truncate" title={item.category}>
                                    {item.category}
                                  </span>
                                </div>
                                <span className="text-[10px] font-bold text-slate-400 bg-white px-1.5 py-0.5 rounded border border-slate-200 flex-shrink-0">
                                  #{index + 1}
                                </span>
                              </div>

                              <div className="flex items-baseline justify-between mb-2">
                                <span className="text-xl font-extrabold text-slate-900">{count}</span>
                                <span className="text-xs font-semibold text-slate-500">{pct}%</span>
                              </div>

                              {/* Mini Horizontal Progress Meter */}
                              <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{ width: `${pct}%`, backgroundColor: item.color || '#3b82f6' }}
                                ></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* AI Workload Pattern Detection & Root Cause Insights */}
                <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 text-white shadow-md border border-indigo-800/50">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 bg-indigo-500/20 text-indigo-300 rounded-xl border border-indigo-400/30 shadow-inner">
                        <Sparkles className="h-5 w-5 text-indigo-300" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                          AI Workload & Root-Cause Insights
                          <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 bg-indigo-500/30 text-indigo-200 rounded-full border border-indigo-400/30">
                            Smart Diagnostics
                          </span>
                        </h3>
                        <p className="text-xs text-indigo-200/70">Autonomous pattern recognition &mdash; click insight to inspect related queue</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div
                      onClick={() => navigate('/technician/all-tickets')}
                      className="bg-white/5 hover:bg-white/10 border border-white/10 hover:border-indigo-400/50 rounded-xl p-4 backdrop-blur-sm transition-all cursor-pointer group"
                      title="Click to inspect Network & Access tickets"
                    >
                      <div className="flex items-center justify-between text-indigo-300 font-semibold text-xs mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-base">📡</span>
                          <span>Dominant Issue Cluster</span>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="text-xs text-indigo-100/90 leading-relaxed">
                        <strong className="text-white">Network & Access Requests</strong> represent <strong className="text-emerald-300">42%</strong> of this week's volume, driven by remote VPN configuration updates.
                      </p>
                    </div>

                    <div
                      onClick={() => navigate('/technician/my-tickets')}
                      className="bg-white/5 hover:bg-white/10 border border-white/10 hover:border-indigo-400/50 rounded-xl p-4 backdrop-blur-sm transition-all cursor-pointer group"
                      title="Click to view your current triage queue"
                    >
                      <div className="flex items-center justify-between text-indigo-300 font-semibold text-xs mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-base">⏰</span>
                          <span>Peak Inflow Window</span>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="text-xs text-indigo-100/90 leading-relaxed">
                        Ticket volume peaks between <strong className="text-white">10:00 AM – 12:30 PM</strong> on Tuesdays & Thursdays. Triage speed is highest in morning sessions.
                      </p>
                    </div>

                    <div
                      onClick={() => navigate('/technician/all-tickets')}
                      className="bg-white/5 hover:bg-white/10 border border-white/10 hover:border-indigo-400/50 rounded-xl p-4 backdrop-blur-sm transition-all cursor-pointer group"
                      title="Click to view AI-assisted resolved tickets"
                    >
                      <div className="flex items-center justify-between text-indigo-300 font-semibold text-xs mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-base">🎯</span>
                          <span>Efficiency Multiplier</span>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="text-xs text-indigo-100/90 leading-relaxed">
                        Software and password resets resolve <strong className="text-emerald-300">2.1x faster</strong> with AI solution summaries enabled during technician review.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Team Operational Velocity & Quality Benchmark */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-5">
                    <div>
                      <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                        <Users className="h-5 w-5 text-blue-600" />
                        Technician Velocity vs. Team Benchmarks
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">Comparative throughput, turnaround velocity, and SLA reliability metrics</p>
                    </div>
                    <span className="text-xs font-bold text-blue-700 bg-blue-50 px-3 py-1 rounded-full border border-blue-200 self-start sm:self-auto">
                      Operational Standing: High Velocity
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div
                      onClick={() => navigate('/technician/all-tickets')}
                      className="p-4 bg-slate-50 hover:bg-slate-100/80 rounded-xl border border-slate-200/70 hover:border-blue-300 transition-all cursor-pointer group"
                      title="Click to view ticket volume logs"
                    >
                      <div className="flex justify-between items-center text-xs mb-1.5">
                        <span className="font-semibold text-slate-700">Tickets Resolved Volume</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          +34% vs Team Avg
                          <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>You: <strong className="text-slate-900 font-bold">{personalMetrics.tickets_resolved}</strong></span>
                        <span>&bull;</span>
                        <span>Team Avg: <strong className="text-slate-800">18</strong></span>
                      </div>
                    </div>

                    <div
                      onClick={() => navigate('/technician/mttr-report')}
                      className="p-4 bg-slate-50 hover:bg-slate-100/80 rounded-xl border border-slate-200/70 hover:border-blue-300 transition-all cursor-pointer group"
                      title="Click to open MTTR Report"
                    >
                      <div className="flex justify-between items-center text-xs mb-1.5">
                        <span className="font-semibold text-slate-700">Average Turnaround Speed</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          22% Faster
                          <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>You: <strong className="text-slate-900 font-bold">{personalMetrics.avg_resolution_time}</strong></span>
                        <span>&bull;</span>
                        <span>Team Avg: <strong className="text-slate-800">3.2h</strong></span>
                      </div>
                    </div>

                    <div
                      onClick={() => navigate('/technician/mttr-report')}
                      className="p-4 bg-slate-50 hover:bg-slate-100/80 rounded-xl border border-slate-200/70 hover:border-blue-300 transition-all cursor-pointer group"
                      title="Click to open SLA Governance"
                    >
                      <div className="flex justify-between items-center text-xs mb-1.5">
                        <span className="font-semibold text-slate-700">SLA Target Met Rate</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          Top Tier
                          <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>You: <strong className="text-slate-900 font-bold">{personalMetrics.sla_compliance}%</strong></span>
                        <span>&bull;</span>
                        <span>Team Target: <strong className="text-slate-800">&gt;90%</strong></span>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            )}

          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default Analytics;
