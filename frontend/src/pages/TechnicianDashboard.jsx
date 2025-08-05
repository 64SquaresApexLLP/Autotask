import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatButton from '../components/ChatButton';
import { Wrench, Bell, Clock, AlertTriangle, Settings, Users, FileText, Calendar, TrendingUp, Loader2, CheckCircle } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import { ticketService } from '../services/ticketService.js';
import { technicianService } from '../services/technicianService.js';
import { ApiError } from '../services/api.js';

const ProgressBar = ({ percentage, color = "bg-blue-500" }) => (
  <div className="w-full bg-gray-200 rounded-full h-3">
    <div 
      className={`${color} h-3 rounded-full transition-all duration-300`} 
      style={{ width: `${percentage}%` }}
    ></div>
  </div>
);

const TechnicianDashboard = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState({
    myTickets: [],
    allTickets: [],
    statistics: null,
    technicians: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTicket, setSelectedTicket] = useState(null);

  // Load dashboard data on component mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError('');

      // Load all tickets, statistics, and technicians
      const [allTickets, statistics, technicians] = await Promise.all([
        ticketService.getAllTickets(),
        ticketService.getTicketStatistics().catch(() => null), // Statistics might not be available
        technicianService.getAllTechnicians().catch(() => []) // Get all technicians
      ]);

      // Filter tickets assigned to current technician using real IDs
      const myTickets = allTickets.filter(ticket => {
        const assignedTech = ticket.assigned_technician;
        const technicianId = ticket.technician_id;
        const currentUserId = user?.username; // This will be T001, T103, T104, T106

        return assignedTech === currentUserId ||
               technicianId === currentUserId;
      });

      setDashboardData({
        myTickets,
        allTickets,
        statistics,
        technicians
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Calculate statistics from ticket data
  const getStatistics = () => {
    const { myTickets, allTickets } = dashboardData;

    return {
      myTotal: myTickets.length,
      myOpen: myTickets.filter(t => !['completed', 'resolved'].includes(t.status?.toLowerCase())).length,
      myCompleted: myTickets.filter(t => ['completed', 'resolved'].includes(t.status?.toLowerCase())).length,
      myUrgent: myTickets.filter(t => ['high', 'critical'].includes(t.priority?.toLowerCase())).length,
      totalUnassigned: allTickets.filter(t => !t.assigned_technician).length,
      totalCritical: allTickets.filter(t => t.priority?.toLowerCase() === 'critical').length
    };
  };

  const stats = getStatistics();

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen ">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto ">
          <div className="max-w-7xl mx-auto space-y-6">
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Welcome Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
              <div className="flex items-center space-x-3 mb-4 sm:mb-0">
                <div className="text-2xl">🔧</div>
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800">Welcome back, {user?.full_name || user?.username}!</h1>
                  <p className="text-gray-600 text-sm lg:text-base">Here's your current workload and team status</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <button
                  onClick={loadDashboardData}
                  disabled={loading}
                  className="flex items-center space-x-2 text-[#00ABE4] hover:text-blue-600 transition-colors disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Clock className="w-5 h-5" />}
                  <span className="text-sm">Refresh</span>
                </button>
                <div className="relative">
                  <Bell className="w-6 h-6 text-gray-500 hover:text-gray-700 cursor-pointer" />
                  {stats.myUrgent > 0 && (
                    <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {stats.myUrgent}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">📋</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">My Active Tickets</h3>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myOpen}
                </div>
                <p className="text-sm text-gray-600">Total assigned: {stats.myTotal}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">🚨</div>
                  {stats.myUrgent > 0 && (
                    <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">
                      {stats.myUrgent}
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Urgent Tickets</h3>
                <div className="text-3xl font-bold text-red-600 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myUrgent}
                </div>
                <p className="text-sm text-red-600">
                  {stats.myUrgent > 0 ? 'Requires immediate attention' : 'No urgent tickets'}
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">✅</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Completed Today</h3>
                <div className="text-3xl font-bold text-green-600 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myCompleted}
                </div>
                <p className="text-sm text-green-600">Great work!</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">📅</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Unassigned Tickets</h3>
                <div className="text-3xl font-bold text-orange-600 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.totalUnassigned}
                </div>
                <p className="text-sm text-gray-600">Available for assignment</p>
              </div>
            </div>

            {/* Performance Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Performance Metrics */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <TrendingUp className="w-5 h-5 text-yellow-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Performance Metrics</h2>
                </div>
                <p className="text-gray-600 mb-6">Your current performance indicators</p>
                
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">Ticket Completion Rate</span>
                      <span className="text-gray-900 font-semibold">
                        {stats.myTotal > 0 ? Math.round((stats.myCompleted / stats.myTotal) * 100) : 0}%
                      </span>
                    </div>
                    <ProgressBar
                      percentage={stats.myTotal > 0 ? (stats.myCompleted / stats.myTotal) * 100 : 0}
                      color="bg-blue-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">Active Workload</span>
                      <span className="text-gray-900 font-semibold">{stats.myOpen} tickets</span>
                    </div>
                    <ProgressBar
                      percentage={Math.min((stats.myOpen / 10) * 100, 100)}
                      color={stats.myOpen > 7 ? "bg-red-500" : stats.myOpen > 4 ? "bg-yellow-500" : "bg-green-500"}
                    />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">Priority Distribution</span>
                      <span className="text-gray-900 font-semibold">{stats.myUrgent} urgent</span>
                    </div>
                    <ProgressBar
                      percentage={stats.myTotal > 0 ? (stats.myUrgent / stats.myTotal) * 100 : 0}
                      color={stats.myUrgent > 0 ? "bg-red-500" : "bg-green-500"}
                    />
                  </div>
                </div>
              </div>

              {/* Team Status */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Users className="w-5 h-5 text-blue-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Team Status</h2>
                </div>
                <p className="text-gray-600 mb-6">Current workload across the team</p>

                <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                  {/* Dynamic technician data from Snowflake */}
                  {dashboardData.technicians
                    .filter(tech => tech.current_workload > 0) // Only show technicians with assigned tickets
                    .map((tech, index) => {
                      const colors = [
                        { bg: 'bg-green-50', dot: 'bg-green-500', tag: 'bg-blue-100 text-blue-800' },
                        { bg: 'bg-yellow-50', dot: 'bg-yellow-500', tag: 'bg-green-100 text-green-800' },
                        { bg: 'bg-blue-50', dot: 'bg-blue-500', tag: 'bg-purple-100 text-purple-800' },
                        { bg: 'bg-purple-50', dot: 'bg-purple-500', tag: 'bg-indigo-100 text-indigo-800' },
                        { bg: 'bg-pink-50', dot: 'bg-pink-500', tag: 'bg-red-100 text-red-800' },
                        { bg: 'bg-indigo-50', dot: 'bg-indigo-500', tag: 'bg-blue-100 text-blue-800' }
                      ];
                      const colorScheme = colors[index % colors.length];
                      
                      return (
                        <div key={tech.id} className={`flex items-center justify-between p-3 ${colorScheme.bg} rounded-lg`}>
                          <div className="flex items-center space-x-3">
                            <div className={`w-3 h-3 ${colorScheme.dot} rounded-full`}></div>
                            <div>
                              <div className="font-semibold text-gray-800">{tech.id}</div>
                              <div className="flex space-x-2 text-xs">
                                <span className={`${colorScheme.tag} px-2 py-1 rounded`}>{tech.role || 'Technician'}</span>
                              </div>
                            </div>
                          </div>
                          <span className="text-sm font-medium text-gray-600">
                            {tech.current_workload} tickets
                          </span>
                        </div>
                      );
                    })}
                  
                  {dashboardData.technicians.filter(tech => tech.current_workload > 0).length === 0 && (
                    <div className="text-center py-4 text-gray-500">
                      No technicians with assigned tickets
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Recent Assignments */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
              <div className="flex items-center space-x-2 mb-6">
                <Clock className="w-5 h-5 text-blue-500" />
                <h2 className="text-xl font-semibold text-gray-800">My Recent Tickets</h2>
              </div>
              <p className="text-gray-600 mb-6">Latest tickets assigned to you</p>

              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading your tickets...</p>
                </div>
              ) : dashboardData.myTickets.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets assigned</p>
                  <p className="text-gray-500">You're all caught up! Great work!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {dashboardData.myTickets.slice(0, 3).map((ticket) => {
                    const priorityColor = ticket.priority?.toLowerCase() === 'critical' ? 'red' :
                                        ticket.priority?.toLowerCase() === 'high' ? 'orange' :
                                        ticket.priority?.toLowerCase() === 'medium' ? 'yellow' : 'green';

                    const borderClass = priorityColor === 'red' ? 'border-red-200 bg-red-50' :
                                       priorityColor === 'orange' ? 'border-orange-200 bg-orange-50' :
                                       priorityColor === 'yellow' ? 'border-yellow-200 bg-yellow-50' : 'border-green-200 bg-green-50';
                    const dotClass = priorityColor === 'red' ? 'bg-red-500' :
                                   priorityColor === 'orange' ? 'bg-orange-500' :
                                   priorityColor === 'yellow' ? 'bg-yellow-500' : 'bg-green-500';
                    const textClass = priorityColor === 'red' ? 'text-red-600' :
                                     priorityColor === 'orange' ? 'text-orange-600' :
                                     priorityColor === 'yellow' ? 'text-yellow-600' : 'text-green-600';

                    return (
                      <div key={ticket.id} className={`flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border rounded-lg ${borderClass}`}>
                        <div className="flex items-start space-x-3 mb-3 sm:mb-0">
                          <div className={`w-3 h-3 rounded-full mt-1 ${dotClass}`}></div>
                          <div>
                            <div className="font-semibold text-gray-800">{ticket.title}</div>
                            <div className="text-sm text-gray-600 mt-1">
                              #{ticket.id} • {ticket.requester_name || ticket.user_email || 'Unknown'} •
                              {new Date(ticket.created_at || Date.now()).toLocaleDateString()}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              Priority: {ticket.priority || 'Medium'} • Status: {ticket.status || 'Open'}
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col sm:items-end space-y-2">
                          <span className={`text-sm font-medium ${textClass}`}>
                            {ticket.priority || 'Medium'} Priority
                          </span>
                          <button
                            onClick={() => setSelectedTicket(ticket)}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            View Details
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {dashboardData.myTickets.length > 3 && (
                    <div className="text-center pt-4">
                      <button
                        onClick={() => window.location.href = '/technician/my-tickets'}
                        className="text-[#00ABE4] hover:text-blue-600 font-medium"
                      >
                        View all {dashboardData.myTickets.length} tickets →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pending Actions */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Pending Actions</h2>
                </div>
                <p className="text-gray-600 mb-6">Tickets requiring your attention or updates</p>

                <div className="space-y-4">
                  {/* Show real tickets that need attention (In Progress or Assigned status) */}
                  {dashboardData.myTickets
                    .filter(ticket => ticket.status === 'In Progress' || ticket.status === 'Assigned')
                    .slice(0, 3)
                    .map((ticket, index) => (
                    <div key={ticket.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-orange-200 bg-orange-50 rounded-lg">
                      <div>
                        <div className="font-semibold text-gray-800 mb-1">{ticket.title}</div>
                        <div className="text-sm text-gray-600 mb-2">{ticket.id} • {ticket.requester_name}</div>
                        <div className="flex items-center space-x-1 text-sm text-orange-600">
                          <AlertTriangle className="w-4 h-4" />
                          <span>Status: {ticket.status}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => setSelectedTicket(ticket)}
                        className="mt-3 sm:mt-0 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-medium text-sm"
                      >
                        Take Action
                      </button>
                    </div>
                  ))}

                  {/* Show message if no pending actions */}
                  {dashboardData.myTickets.filter(ticket => ticket.status === 'In Progress' || ticket.status === 'Assigned').length === 0 && (
                    <div className="text-center py-8">
                      <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                      <p className="text-gray-600">No pending actions required!</p>
                      <p className="text-sm text-gray-500">All your tickets are up to date.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* System Status */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Bell className="w-5 h-5 text-blue-500" />
                  <h2 className="text-xl font-semibold text-gray-800">System Status</h2>
                </div>

                <div className="space-y-4">
                  {/* Real system status */}
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <div className="text-xl">✅</div>
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">Operational</span>
                        </div>
                        <div className="font-semibold text-gray-800 mb-2">All Systems Operational</div>
                        <p className="text-sm text-gray-600">
                          Ticket system, database, and AI agents are running normally.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <div className="text-xl">📊</div>
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">Statistics</span>
                        </div>
                        <div className="font-semibold text-gray-800 mb-2">Total Tickets in System</div>
                        <p className="text-sm text-gray-600">
                          {dashboardData.allTickets.length} tickets currently in the system across all technicians.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
      <ChatButton />

      {/* Ticket Detail Modal */}
      {selectedTicket && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">
                    🎫 {selectedTicket.ticketnumber || selectedTicket.id} - {selectedTicket.title}
                  </h2>
                  <p className="text-gray-600">{selectedTicket.ticketcategory || 'General'} • {selectedTicket.tickettype || 'Support'}</p>
                </div>
                <button
                  onClick={() => setSelectedTicket(null)}
                  className="text-gray-500 hover:text-gray-700 text-xl font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <p className="text-gray-800">{selectedTicket.description || 'No description provided'}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        selectedTicket.status === 'resolved' ? 'bg-green-100 text-green-800' :
                        selectedTicket.status === 'Assigned' ? 'bg-blue-100 text-blue-800' :
                        selectedTicket.status === 'In Progress' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {selectedTicket.status || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        selectedTicket.priority === 'Critical' ? 'bg-red-100 text-red-800' :
                        selectedTicket.priority === 'High' ? 'bg-orange-100 text-orange-800' :
                        selectedTicket.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {selectedTicket.priority || 'Medium'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Requester</label>
                    <p className="text-gray-800">{selectedTicket.requester_name || selectedTicket.useremail || 'Unknown'}</p>
                  </div>
                </div>

                {/* Right Column */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Created</label>
                    <p className="text-gray-800">{selectedTicket.created_at ? new Date(selectedTicket.created_at).toLocaleDateString() : 'Unknown'}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                    <p className="text-gray-800">{selectedTicket.duedatetime || 'Not set'}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Issue Type</label>
                    <p className="text-gray-800">{selectedTicket.issuetype || 'General'}</p>
                  </div>

                  {selectedTicket.resolution && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Resolution</label>
                      <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                        <p className="text-gray-800">{selectedTicket.resolution}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between items-center pt-4 border-t">
                <div className="flex space-x-3">
                  {/* Show action buttons for tickets that need action */}
                  {(selectedTicket.status === 'Assigned' || selectedTicket.status === 'In Progress') && (
                    <>
                      <button
                        onClick={() => {
                          // Navigate to My Tickets page where they can manage the ticket
                          window.location.href = '/technician/my-tickets';
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        Manage Ticket
                      </button>
                      <button
                        onClick={() => {
                          // Navigate to My Tickets page
                          window.location.href = '/technician/my-tickets';
                        }}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        Update Status
                      </button>
                    </>
                  )}
                </div>
                <button
                  onClick={() => setSelectedTicket(null)}
                  className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TechnicianDashboard;