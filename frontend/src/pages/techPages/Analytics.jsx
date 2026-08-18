import React, { useState, useEffect } from 'react';
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
  Line,
  LineChart,
  PieChart,
  Pie,
  Cell,
  Legend,
  ReferenceLine,
} from "recharts";
import { TrendingUp, Clock, CheckCircle, Star, Award, Target, Users, Zap, Loader2, RefreshCw, AlertCircle, Hourglass, PlayCircle, FileText } from "lucide-react";
import useAuth from '../../hooks/useAuth';

const Analytics = () => {
  const { user } = useAuth();
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load analytics data for current technician
  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError('');
      
      if (!user?.username) {
        setError('User not authenticated');
        return;
      }

      // Fetch analytics data from backend
      const response = await fetch(`http://localhost:8001/analytics/${user.username}`);
      if (!response.ok) {
        throw new Error('Failed to fetch analytics data');
      }
      
      const data = await response.json();
      setAnalyticsData(data);
      
    } catch (error) {
      console.error('Failed to load analytics:', error);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.username) {
      loadAnalytics();
    }
  }, [user]);

  // Use real data or fallback to empty data
  const personalMetrics = analyticsData?.personal_metrics || {
    tickets_resolved: 0,
    tickets_open: 0,
    tickets_pending: 0,
    tickets_in_progress: 0,
    avg_resolution_time: "0 hours",
    customer_satisfaction: 0.0,
    sla_compliance: 0,
    this_week_resolved: 0,
    this_month_resolved: 0,
    total_tickets: 0
  };

  const weeklyData = analyticsData?.weekly_data || [];
  const categoryData = analyticsData?.category_data || [];
  const priorityData = analyticsData?.priority_data || [];
  const statusData = analyticsData?.status_data || [];

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Header Section */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-800">📊 Analytics Dashboard</h1>
                <p className="text-gray-600">Your performance metrics and insights</p>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={loadAnalytics}
                  disabled={loading}
                  className="flex items-center space-x-1 border border-gray-300 px-3 py-1 rounded-full text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3 w-3" />
                  )}
                  <span>Refresh</span>
                </button>
                <span className="border border-gray-300 px-3 py-1 rounded-full text-sm font-medium">
                  This Month
                </span>
                {personalMetrics.tickets_resolved > 20 && (
                  <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                    Top Performer 🏆
                  </span>
                )}
              </div>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  <span className="text-gray-600">Loading analytics data...</span>
                </div>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <div className="text-red-600 font-medium">Error loading analytics</div>
                </div>
                <p className="text-red-600 text-sm mt-1">{error}</p>
                <button
                  onClick={loadAnalytics}
                  className="mt-2 text-red-600 hover:text-red-700 text-sm font-medium"
                >
                  Try again
                </button>
              </div>
            )}

            {/* Analytics Content */}
            {!loading && !error && (
              <div className="space-y-6">
                {/* Key Performance Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-6">
                  {/* Total Tickets Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Total Tickets</h3>
                      <FileText className="h-4 w-4 text-gray-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.total_tickets}</div>
                    <p className="text-xs text-gray-500 mt-1">All assigned tickets</p>
                  </div>

                  {/* Open Tickets Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Open Tickets</h3>
                      <AlertCircle className="h-4 w-4 text-red-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.tickets_open}</div>
                    <p className="text-xs text-gray-500 mt-1">Active (not resolved/closed)</p>
                  </div>

                  {/* Pending Tickets Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Pending</h3>
                      <Hourglass className="h-4 w-4 text-yellow-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.tickets_pending}</div>
                    <p className="text-xs text-gray-500 mt-1">Awaiting action</p>
                  </div>

                  {/* In Progress Tickets Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">In Progress</h3>
                      <PlayCircle className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.tickets_in_progress}</div>
                    <p className="text-xs text-gray-500 mt-1">Actively working</p>
                  </div>

                  {/* Tickets Resolved Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Tickets Resolved</h3>
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.tickets_resolved}</div>
                    <p className="text-xs text-gray-500 mt-1">
                      <TrendingUp className="inline h-3 w-3 mr-1" />
                      This month: {personalMetrics.this_month_resolved}
                    </p>
                  </div>

                  {/* Avg Resolution Time Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Avg Resolution Time</h3>
                      <Clock className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.avg_resolution_time}</div>
                    <p className="text-xs text-gray-500 mt-1">Based on resolved tickets</p>
                  </div>

                  {/* Customer Satisfaction Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Customer Satisfaction</h3>
                      <Star className="h-4 w-4 text-yellow-500" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.customer_satisfaction}/5.0</div>
                    <p className="text-xs text-gray-500 mt-1">
                      {personalMetrics.customer_satisfaction >= 4.5 ? 'Above' : 'At'} team average
                    </p>
                  </div>

                  {/* SLA Compliance Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">SLA Compliance</h3>
                      <Target className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.sla_compliance}%</div>
                    <p className="text-xs text-gray-500 mt-1">
                      {personalMetrics.sla_compliance >= 95 ? 'Excellent' : 'Good'}
                    </p>
                  </div>

                  {/* This Week Resolved Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:col-span-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">This Week</h3>
                      <Zap className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.this_week_resolved}</div>
                    <p className="text-xs text-gray-500 mt-1">Resolved in last 7 days</p>
                  </div>
                </div>

                {/* Charts Section - Weekly Performance */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  {/* Chart Header */}
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">Weekly Performance</h3>
                      <p className="text-sm text-gray-500 mt-0.5">Tickets created vs resolved — last 7 days</p>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-3 rounded-sm" style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}></span>
                        <span className="text-gray-600 font-medium">Resolved</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-3 rounded-sm" style={{ background: 'linear-gradient(135deg,#38bdf8,#0ea5e9)' }}></span>
                        <span className="text-gray-600 font-medium">Created</span>
                      </span>
                    </div>
                  </div>

                  {weeklyData.length > 0 ? (
                    <>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart
                          data={weeklyData}
                          barCategoryGap="30%"
                          barGap={4}
                          margin={{ top: 10, right: 10, left: -10, bottom: 30 }}
                        >
                          <defs>
                            <linearGradient id="resolvedGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#6366f1" stopOpacity={1} />
                              <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.8} />
                            </linearGradient>
                            <linearGradient id="createdGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#38bdf8" stopOpacity={1} />
                              <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.7} />
                            </linearGradient>
                            <linearGradient id="resolvedGradientToday" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#4f46e5" stopOpacity={1} />
                              <stop offset="100%" stopColor="#7c3aed" stopOpacity={1} />
                            </linearGradient>
                            <linearGradient id="createdGradientToday" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#0284c7" stopOpacity={1} />
                              <stop offset="100%" stopColor="#0369a1" stopOpacity={1} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="4 4" stroke="#f1f5f9" vertical={false} />
                          <XAxis
                            dataKey="day"
                            axisLine={false}
                            tickLine={false}
                            height={55}
                            tick={(props) => {
                              const { x, y, payload, index } = props;
                              const entry = weeklyData[index] || {};
                              const isToday = entry.is_today;
                              const dayName = entry.day || payload.value;
                              const fullDate = entry.full_date || '';
                              return (
                                <g transform={`translate(${x},${y + 6})`}>
                                  {/* Today highlight pill */}
                                  {isToday && (
                                    <rect
                                      x={-28} y={-4}
                                      width={56} height={46}
                                      rx={8}
                                      fill="#6366f1"
                                      fillOpacity={0.08}
                                      stroke="#6366f1"
                                      strokeWidth={1.5}
                                      strokeOpacity={0.35}
                                    />
                                  )}
                                  {/* Day name */}
                                  <text
                                    x={0} y={10}
                                    textAnchor="middle"
                                    fill={isToday ? '#4f46e5' : '#64748b'}
                                    fontSize={12}
                                    fontWeight={isToday ? 700 : 500}
                                  >
                                    {dayName}
                                  </text>
                                  {/* Date number */}
                                  <text
                                    x={0} y={25}
                                    textAnchor="middle"
                                    fill={isToday ? '#6366f1' : '#94a3b8'}
                                    fontSize={11}
                                    fontWeight={isToday ? 600 : 400}
                                  >
                                    {fullDate}
                                  </text>
                                  {/* "Today" badge */}
                                  {isToday && (
                                    <text
                                      x={0} y={40}
                                      textAnchor="middle"
                                      fill="#6366f1"
                                      fontSize={9}
                                      fontWeight={700}
                                      letterSpacing={0.5}
                                    >
                                      TODAY
                                    </text>
                                  )}
                                </g>
                              );
                            }}
                          />
                          <YAxis
                            tick={{ fontSize: 12, fill: '#94a3b8' }}
                            axisLine={false}
                            tickLine={false}
                            allowDecimals={false}
                          />
                          <Tooltip
                            contentStyle={{
                              background: '#1e293b',
                              border: 'none',
                              borderRadius: '10px',
                              color: '#f8fafc',
                              boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                              padding: '10px 14px'
                            }}
                            labelFormatter={(label, payload) => {
                              if (payload && payload.length > 0) {
                                const entry = payload[0].payload;
                                return `${entry.day}, ${entry.full_date}${entry.is_today ? ' (Today)' : ''}`;
                              }
                              return label;
                            }}
                            labelStyle={{ color: '#94a3b8', fontWeight: 600, marginBottom: '4px', fontSize: '12px' }}
                            itemStyle={{ color: '#f8fafc', fontSize: '13px' }}
                            cursor={{ fill: 'rgba(148,163,184,0.08)', radius: 4 }}
                          />
                          <Bar
                            dataKey="resolved"
                            name="Resolved"
                            radius={[6, 6, 0, 0]}
                            maxBarSize={40}
                          >
                            {weeklyData.map((entry, index) => (
                              <Cell
                                key={`resolved-${index}`}
                                fill={entry.is_today ? 'url(#resolvedGradientToday)' : 'url(#resolvedGradient)'}
                              />
                            ))}
                          </Bar>
                          <Bar
                            dataKey="created"
                            name="Created"
                            radius={[6, 6, 0, 0]}
                            maxBarSize={40}
                          >
                            {weeklyData.map((entry, index) => (
                              <Cell
                                key={`created-${index}`}
                                fill={entry.is_today ? 'url(#createdGradientToday)' : 'url(#createdGradient)'}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>

                      {/* Weekly Summary Row */}
                      <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-4">
                        <div className="text-center">
                          <p className="text-xs text-gray-500 mb-1">Total Created</p>
                          <p className="text-xl font-bold text-sky-500">
                            {weeklyData.reduce((sum, d) => sum + (d.created || 0), 0)}
                          </p>
                        </div>
                        <div className="text-center border-x border-gray-100">
                          <p className="text-xs text-gray-500 mb-1">Total Resolved</p>
                          <p className="text-xl font-bold text-indigo-500">
                            {weeklyData.reduce((sum, d) => sum + (d.resolved || 0), 0)}
                          </p>
                        </div>
                        <div className="text-center">
                          <p className="text-xs text-gray-500 mb-1">Resolution Rate</p>
                          <p className="text-xl font-bold text-emerald-500">
                            {(() => {
                              const created = weeklyData.reduce((s, d) => s + (d.created || 0), 0);
                              const resolved = weeklyData.reduce((s, d) => s + (d.resolved || 0), 0);
                              return created > 0 ? `${Math.round((resolved / created) * 100)}%` : 'N/A';
                            })()}
                          </p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                      <TrendingUp className="h-10 w-10 mb-3 opacity-30" />
                      <p className="text-sm font-medium">No activity in the last 7 days</p>
                      <p className="text-xs mt-1 opacity-70">Resolve tickets to see your weekly trend</p>
                    </div>
                  )}
                </div>

                {/* Category Breakdown */}
                {categoryData.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold mb-4">Tickets by Category</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {categoryData.map((item, index) => (
                        <div key={index} className="text-center">
                          <div className="text-2xl font-bold" style={{ color: item.color }}>
                            {item.count}
                          </div>
                          <div className="text-sm text-gray-600">{item.category}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Priority Breakdown */}
                {priorityData.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold mb-4">Tickets by Priority</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="w-full h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={priorityData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={100}
                              dataKey="count"
                              nameKey="priority"
                              label={({ priority, percent }) => `${priority} ${(percent * 100).toFixed(0)}%`}
                            >
                              {priorityData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => [value, 'tickets']} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="space-y-3">
                        {priorityData.map((item, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                            <span className="font-medium">{item.priority}</span>
                            <span className="text-gray-600">{item.count} tickets</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Status Distribution */}
                {statusData.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold mb-4">Ticket Status Distribution</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="w-full h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={statusData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={100}
                              dataKey="count"
                              nameKey="status"
                              label={({ status, percent }) => `${status} ${(percent * 100).toFixed(0)}%`}
                            >
                              {statusData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => [value, 'tickets']} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="space-y-3">
                        {statusData.map((item, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                            <span className="font-medium">{item.status}</span>
                            <span className="text-gray-600">{item.count} tickets</span>
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
