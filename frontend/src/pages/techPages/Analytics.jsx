import React from 'react';
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
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { TrendingUp, Clock, CheckCircle, Star, Award, Target, Users, Zap } from "lucide-react";

// Mock analytics data
const personalMetrics = {
  ticketsResolved: 28,
  avgResolutionTime: "4.2 hours",
  customerSatisfaction: 4.7,
  slaCompliance: 94,
  thisWeekResolved: 8,
  thisMonthResolved: 28,
  totalTimeSpent: "156 hours",
  escalationRate: 5,
};

const weeklyData = [
  { day: "Mon", resolved: 4, created: 3 },
  { day: "Tue", resolved: 6, created: 5 },
  { day: "Wed", resolved: 3, created: 4 },
  { day: "Thu", resolved: 5, created: 2 },
  { day: "Fri", resolved: 7, created: 6 },
  { day: "Sat", resolved: 2, created: 1 },
  { day: "Sun", resolved: 1, created: 2 },
];

const categoryData = [
  { category: "Hardware", count: 12, color: "#3b82f6" },
  { category: "Software", count: 8, color: "#10b981" },
  { category: "Network", count: 6, color: "#f59e0b" },
  { category: "Account", count: 2, color: "#ef4444" },
];

const priorityTrends = [
  { month: "Oct", low: 8, medium: 12, high: 4, critical: 1 },
  { month: "Nov", low: 10, medium: 15, high: 6, critical: 2 },
  { month: "Dec", low: 12, medium: 18, high: 5, critical: 1 },
  { month: "Jan", low: 6, medium: 14, high: 7, critical: 1 },
];

const teamComparison = [
  { name: "You", resolved: 28, satisfaction: 4.7, sla: 94 },
  { name: "Aditya", resolved: 32, satisfaction: 4.5, sla: 91 },
  { name: "Mahima", resolved: 25, satisfaction: 4.8, sla: 96 },
  { name: "Archit", resolved: 30, satisfaction: 4.6, sla: 89 },
];

const skillEffectiveness = [
  { skill: "Hardware", tickets: 12, avgTime: "3.2h", satisfaction: 4.8 },
  { skill: "Network", tickets: 6, avgTime: "5.1h", satisfaction: 4.5 },
  { skill: "Software", tickets: 8, avgTime: "4.8h", satisfaction: 4.7 },
  { skill: "Account", tickets: 2, avgTime: "1.5h", satisfaction: 4.9 },
];

const Analytics = () => {
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
                <span className="border border-gray-300 px-3 py-1 rounded-full text-sm font-medium">
                  This Month
                </span>
                <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                  Top Performer 🏆
                </span>
              </div>
            </div>

            {/* Key Performance Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Tickets Resolved Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium">Tickets Resolved</h3>
                  <CheckCircle className="h-4 w-4 text-green-600" />
                </div>
                <div className="text-2xl font-bold">{personalMetrics.ticketsResolved}</div>
                <p className="text-xs text-gray-500 mt-1">
                  <TrendingUp className="inline h-3 w-3 mr-1" />
                  +12% from last month
                </p>
              </div>

              {/* Avg Resolution Time Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium">Avg Resolution Time</h3>
                  <Clock className="h-4 w-4 text-blue-600" />
                </div>
                <div className="text-2xl font-bold">{personalMetrics.avgResolutionTime}</div>
                <p className="text-xs text-gray-500 mt-1">
                  <Target className="inline h-3 w-3 mr-1" />
                  15% faster than team avg
                </p>
              </div>

              {/* Customer Satisfaction Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium">Customer Satisfaction</h3>
                  <Star className="h-4 w-4 text-yellow-600" />
                </div>
                <div className="text-2xl font-bold">{personalMetrics.customerSatisfaction}/5.0</div>
                <p className="text-xs text-gray-500 mt-1">
                  <Award className="inline h-3 w-3 mr-1" />
                  Above team average
                </p>
              </div>

              {/* SLA Compliance Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium">SLA Compliance</h3>
                  <Zap className="h-4 w-4 text-purple-600" />
                </div>
                <div className="text-2xl font-bold">{personalMetrics.slaCompliance}%</div>
                <p className="text-xs text-gray-500 mt-1">
                  <TrendingUp className="inline h-3 w-3 mr-1" />
                  +3% improvement
                </p>
              </div>
            </div>

            {/* Performance Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Weekly Performance Chart */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold">Weekly Performance</h2>
                  <p className="text-sm text-gray-600">Tickets resolved vs created this week</p>
                </div>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={weeklyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="resolved" fill="#10b981" name="Resolved" />
                      <Bar dataKey="created" fill="#3b82f6" name="Assigned" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Tickets by Category Chart */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold">Tickets by Category</h2>
                  <p className="text-sm text-gray-600">Distribution of your resolved tickets</p>
                </div>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ category, count }) => `${category}: ${count}`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                      >
                        {categoryData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Priority Trends Chart */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="mb-4">
                <h2 className="text-lg font-semibold">Priority Trends Over Time</h2>
                <p className="text-sm text-gray-600">Monthly breakdown of tickets by priority level</p>
              </div>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={priorityTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="low" stroke="#10b981" strokeWidth={2} name="Low" />
                    <Line type="monotone" dataKey="medium" stroke="#f59e0b" strokeWidth={2} name="Medium" />
                    <Line type="monotone" dataKey="high" stroke="#ef4444" strokeWidth={2} name="High" />
                    <Line type="monotone" dataKey="critical" stroke="#7c3aed" strokeWidth={2} name="Critical" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Team Comparison */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="mb-4">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Team Performance Comparison</h2>
                </div>
                <p className="text-sm text-gray-600">How you stack up against your teammates</p>
              </div>
              <div className="space-y-4">
                {teamComparison.map((member, index) => (
                  <div
                    key={index}
                    className={`p-4 border rounded-lg ${member.name === "You" ? "bg-blue-50 border-blue-200" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{member.name}</span>
                        {member.name === "You" && (
                          <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs">
                            You
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">{member.resolved} tickets resolved</div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Satisfaction</p>
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-green-500 h-2 rounded-full"
                              style={{ width: `${(member.satisfaction / 5) * 100}%` }}
                            ></div>
                          </div>
                          <span className="font-medium">{member.satisfaction}</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">SLA Compliance</p>
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ width: `${member.sla}%` }}
                            ></div>
                          </div>
                          <span className="font-medium">{member.sla}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">Rank</p>
                        <span className="font-medium">#{index + 1}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Skill-based Performance */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="mb-4">
                <h2 className="text-lg font-semibold">Skill-based Performance</h2>
                <p className="text-sm text-gray-600">Your effectiveness across different skill areas</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {skillEffectiveness.map((skill, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">{skill.skill}</h4>
                      <span className="border border-gray-300 px-2 py-1 rounded-full text-xs">
                        {skill.tickets} tickets
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Avg Resolution Time:</span>
                        <span className="font-medium">{skill.avgTime}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Customer Satisfaction:</span>
                        <div className="flex items-center gap-1">
                          <Star className="h-3 w-3 text-yellow-500" />
                          <span className="font-medium">{skill.satisfaction}</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{ width: `${(skill.satisfaction / 5) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Personal Goals */}
            <div className="border border-green-200 bg-green-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-4">
                <Target className="h-5 w-5 text-green-800" />
                <h2 className="text-lg font-semibold text-green-800">Monthly Goals & Achievements</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm font-medium text-green-900">Resolution Target</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${(personalMetrics.thisMonthResolved / 30) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-green-800">
                      {personalMetrics.thisMonthResolved}/30
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-green-900">SLA Target</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${personalMetrics.slaCompliance}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-green-800">
                      {personalMetrics.slaCompliance}%
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-green-900">Satisfaction Target</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${(personalMetrics.customerSatisfaction / 5) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-green-800">
                      {personalMetrics.customerSatisfaction}/5.0
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default Analytics;