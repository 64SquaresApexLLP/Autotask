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
} from "recharts";
import { TrendingUp, Clock, CheckCircle, Star, Award, Target, Users, Zap, Loader2, RefreshCw } from "lucide-react";
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

      // Try to fetch analytics data from backend
      try {
        const response = await fetch(`http://localhost:8000/analytics/${user.username}`);
        if (!response.ok) {
          throw new Error('Failed to fetch analytics data');
        }

        const data = await response.json();
        setAnalyticsData(data);
      } catch (apiError) {
        console.warn('Analytics API not available, using fallback data:', apiError);

        // Fallback: Use empty data structure
        const fallbackData = {
          personal_metrics: {
            tickets_resolved: 0,
            avg_resolution_time: "N/A",
            customer_satisfaction: 0.0,
            sla_compliance: 0,
            this_week_resolved: 0,
            this_month_resolved: 0
          },
          weekly_data: [],
          category_data: []
        };
        setAnalyticsData(fallbackData);
      }
      
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
    avg_resolution_time: "0 hours",
    customer_satisfaction: 0.0,
    sla_compliance: 0,
    this_week_resolved: 0,
    this_month_resolved: 0
  };

  const weeklyData = analyticsData?.weekly_data || [];
  const categoryData = analyticsData?.category_data || [];

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
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Tickets Resolved Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Tickets Resolved</h3>
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.tickets_resolved}</div>
                    <p className="text-xs text-gray-500 mt-1">
                      <TrendingUp className="inline h-3 w-3 mr-1" />
                      This month
                    </p>
                  </div>

                  {/* Avg Resolution Time Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">Avg Resolution Time</h3>
                      <Clock className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.avg_resolution_time}</div>
                    <p className="text-xs text-gray-500 mt-1">Based on resolved tickets</p>
                  </div>

                  {/* Customer Satisfaction Card */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
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
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium">SLA Compliance</h3>
                      <Target className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="text-2xl font-bold">{personalMetrics.sla_compliance}%</div>
                    <p className="text-xs text-gray-500 mt-1">
                      {personalMetrics.sla_compliance >= 95 ? 'Excellent' : 'Good'}
                    </p>
                  </div>
                </div>

                {/* Charts Section */}
                {weeklyData.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold mb-4">Weekly Performance</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={weeklyData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="resolved" fill="#3b82f6" name="Resolved" />
                        <Bar dataKey="created" fill="#e5e7eb" name="Created" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

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
