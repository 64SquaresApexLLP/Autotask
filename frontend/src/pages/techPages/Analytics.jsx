import React, { useState, useEffect, useCallback } from 'react';
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
  Sparkles
} from "lucide-react";
import useAuth from '../../hooks/useAuth';
import { API_BASE_URL } from '../../config/api';

const Analytics = () => {
  const { user } = useAuth();
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
                    <Activity className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-2xl md:text-3xl font-bold text-slate-800 tracking-tight">
                        Analytics Dashboard
                      </h1>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        Live Realtime
                      </span>
                    </div>
                    <p className="text-slate-500 text-sm mt-0.5">
                      Real-time performance metrics, ticket resolutions, and workflow insights
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

                {personalMetrics.tickets_resolved > 20 && (
                  <span className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-3 py-1.5 rounded-xl text-xs font-semibold shadow-sm flex items-center gap-1">
                    <Award className="h-3.5 w-3.5" />
                    Top Performer 🏆
                  </span>
                )}
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
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-blue-200 transition">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tickets Resolved</span>
                      <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
                        <CheckCircle className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                      {personalMetrics.tickets_resolved}
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="flex items-center gap-1 font-medium text-emerald-600">
                        <TrendingUp className="h-3.5 w-3.5" />
                        {resolutionRate}% resolved
                      </span>
                      <span>Total: {personalMetrics.total_tickets}</span>
                    </div>
                  </div>

                  {/* Avg Resolution Time Card */}
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-blue-200 transition">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avg Resolution Time</span>
                      <div className="p-2 bg-blue-100 text-blue-700 rounded-xl">
                        <Clock className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                      {personalMetrics.avg_resolution_time}
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-blue-600 font-medium">⚡ Optimal performance</span>
                      <span>{personalMetrics.open_tickets} active</span>
                    </div>
                  </div>

                  {/* Customer Satisfaction Card */}
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-blue-200 transition">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-amber-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer Satisfaction</span>
                      <div className="p-2 bg-amber-100 text-amber-700 rounded-xl">
                        <Star className="h-5 w-5 fill-amber-500 text-amber-500" />
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{personalMetrics.customer_satisfaction}</span>
                      <span className="text-sm font-medium text-slate-400">/ 5.0</span>
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-amber-600 font-medium">★★★★★ Excellent rating</span>
                      <span>Team Avg: 4.5</span>
                    </div>
                  </div>

                  {/* SLA Compliance Card */}
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 relative overflow-hidden group hover:border-blue-200 transition">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-purple-50 rounded-full -mr-8 -mt-8 pointer-events-none transition group-hover:scale-110"></div>
                    <div className="flex items-center justify-between mb-3 relative">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">SLA Compliance</span>
                      <div className="p-2 bg-purple-100 text-purple-700 rounded-xl">
                        <Target className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{personalMetrics.sla_compliance}%</span>
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="text-purple-600 font-medium">🎯 Target met</span>
                      <span>Target: &gt;90%</span>
                    </div>
                  </div>
                </div>

                {/* Charts Grid: Weekly Performance & Priority Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                  {/* Weekly Performance Bar Chart (2 columns on lg) */}
                  <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6">
                    <div className="flex items-center justify-between mb-6">
                      <div>
                        <h3 className="text-base font-bold text-slate-800">Weekly Performance Activity</h3>
                        <p className="text-xs text-slate-500 mt-0.5">Tickets resolved vs newly created by day of week</p>
                      </div>
                      <div className="flex items-center gap-4 text-xs font-medium">
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-3 rounded bg-blue-600"></span>
                          <span className="text-slate-600">Resolved</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-3 rounded bg-slate-200"></span>
                          <span className="text-slate-600">Created</span>
                        </div>
                      </div>
                    </div>

                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                          <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', borderRadius: '12px', border: 'none', color: '#fff' }}
                            itemStyle={{ color: '#fff', fontSize: '12px' }}
                            cursor={{ fill: '#f8fafc' }}
                          />
                          <Bar dataKey="resolved" fill="#3b82f6" name="Resolved" radius={[6, 6, 0, 0]} maxBarSize={36} />
                          <Bar dataKey="created" fill="#e2e8f0" name="Created" radius={[6, 6, 0, 0]} maxBarSize={36} />
                        </BarChart>
                      </ResponsiveContainer>
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
                        <span className="text-xs text-slate-400 font-medium">Real-time</span>
                      </div>
                      <p className="text-xs text-slate-500 mb-6">Distribution across urgency tiers</p>

                      <div className="space-y-4">
                        {priorityData.map((item) => {
                          const total = personalMetrics.total_tickets || 1;
                          const pct = Math.round((item.count / total) * 100);
                          return (
                            <div key={item.priority} className="space-y-1.5">
                              <div className="flex items-center justify-between text-xs font-semibold">
                                <div className="flex items-center gap-2">
                                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                                  <span className="text-slate-700">{item.priority}</span>
                                </div>
                                <div className="text-slate-500 font-mono">
                                  {item.count} <span className="text-slate-400 font-normal">({pct}%)</span>
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

                    <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                      <span>Total Tracked Tickets</span>
                      <span className="font-bold text-slate-800">{personalMetrics.total_tickets}</span>
                    </div>
                  </div>

                </div>

                {/* Category Breakdown & Donut Chart */}
                {categoryData.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
                      <div>
                        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                          <Layers className="h-4 w-4 text-blue-500" />
                          Tickets by Issue Category
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">Real-time classification breakdown across all incoming tickets</p>
                      </div>
                      <span className="text-xs font-semibold px-3 py-1 bg-slate-100 text-slate-700 rounded-full self-start sm:self-auto">
                        {categoryData.length} Categories
                      </span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                      {/* Donut Chart */}
                      <div className="lg:col-span-5 h-64 flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={categoryData}
                              dataKey="count"
                              nameKey="category"
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={95}
                              paddingAngle={3}
                            >
                              {categoryData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color || '#6366f1'} />
                              ))}
                            </Pie>
                            <Tooltip
                              contentStyle={{ backgroundColor: '#1e293b', borderRadius: '12px', border: 'none', color: '#fff' }}
                              itemStyle={{ color: '#fff', fontSize: '12px' }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>

                      {/* Category Grid Pills */}
                      <div className="lg:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {categoryData.map((item, index) => (
                          <div
                            key={index}
                            className="bg-slate-50 hover:bg-slate-100/80 border border-slate-200/60 rounded-xl p-3.5 transition group"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span
                                className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                                style={{ backgroundColor: item.color }}
                              ></span>
                              <span className="text-xs font-semibold text-slate-600 truncate" title={item.category}>
                                {item.category}
                              </span>
                            </div>
                            <div className="text-xl font-extrabold text-slate-900 ml-4.5">
                              {item.count}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

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
