import React, { useState, useEffect, useCallback } from 'react';
import { 
  Timer, 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  Search, 
  RefreshCw, 
  Loader2, 
  BarChart3,
  AlertCircle,
  Eye,
  Lock,
  FileText
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatButton from '../components/ChatButton';
import MttrCard from '../components/MttrCard';
import { ticketService } from '../services/ticketService.js';
import useAuth from '../hooks/useAuth';

const MttrReport = () => {
  const { user } = useAuth();
  const isTechnician = user?.role !== 'user';
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [mttrData, setMttrData] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');

  const loadMttrReportData = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) {
        setLoading(true);
      } else {
        setRefreshing(false);
      }
      setError('');

      const userId = user?.username?.trim().toLowerCase();
      const userEmail = user?.email?.trim().toLowerCase();
      const userName = (user?.name || user?.full_name)?.trim().toLowerCase();

      const mttrParams = isTechnician
        ? { technician_id: userId || userEmail }
        : { user_email: userEmail || userId };

      const [allTickets, analytics] = await Promise.all([
        ticketService.getAllTickets({ limit: 150 }).catch(() => []),
        ticketService.getMttrAnalytics(mttrParams).catch(() => null)
      ]);

      setMttrData(analytics);

      // Filter tickets strictly for the current user (if role is user)
      let filteredRoleTickets = [];

      if (!isTechnician) {
        filteredRoleTickets = allTickets.filter(ticket => {
          const tEmail = (ticket.user_email || '').trim().toLowerCase();
          const tUserId = (ticket.user_id || '').trim().toLowerCase();
          const tReqName = (ticket.requester_name || '').trim().toLowerCase();

          return (userEmail && tEmail === userEmail) ||
            (userId && tUserId === userId) ||
            (userId && tReqName === userId) ||
            (userName && tReqName === userName) ||
            (userName && tEmail === userName);
        });
      } else {
        filteredRoleTickets = allTickets;
      }

      setTickets(filteredRoleTickets);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load MTTR report data:', err);
      setError('Unable to load MTTR report data. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user, isTechnician]);

  useEffect(() => {
    loadMttrReportData();
    const interval = setInterval(() => loadMttrReportData(true), 30000);
    return () => clearInterval(interval);
  }, [loadMttrReportData]);

  const currentUserId = (user?.username || '').trim().toLowerCase();
  const currentUserEmail = (user?.email || '').trim().toLowerCase();
  const currentFullName = (user?.name || user?.full_name || '').trim().toLowerCase();

  const isTicketAssignedToMe = (ticket) => {
    const assignedTech = (ticket.assigned_technician || '').trim().toLowerCase();
    const techId = (ticket.technician_id || '').trim().toLowerCase();
    const techEmail = (ticket.technician_email || '').trim().toLowerCase();

    return (
      (currentUserId && (assignedTech === currentUserId || techId === currentUserId)) ||
      (currentUserEmail && (techEmail === currentUserEmail || assignedTech === currentUserEmail)) ||
      (currentFullName && (assignedTech === currentFullName || assignedTech.includes(currentFullName)))
    );
  };

  // Tickets rendered on this report — technicians see only their own assigned tickets (MTTR-only, no SLA tracking)
  const processedTickets = isTechnician ? tickets.filter(isTicketAssignedToMe) : tickets;

  // Filtered tickets based on search and filters
  const displayedTickets = processedTickets.filter(ticket => {
    const matchesSearch = 
      (ticket.title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ticket.id || '').toString().toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ticket.requester_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ticket.assigned_technician || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesPriority = 
      priorityFilter === 'all' || 
      (ticket.priority || '').toLowerCase() === priorityFilter.toLowerCase();


    return matchesSearch && matchesPriority;
  });

  // Chart 1: MTTR by Priority Bar Chart Data
  const priorityBarData = ['Critical', 'High', 'Medium', 'Low'].map(pKey => {
    const userPriorityTickets = processedTickets.filter(
      t => (t.priority || 'medium').toLowerCase() === pKey.toLowerCase()
    );
    const resolvedUserPriority = userPriorityTickets.filter(
      t => ['completed', 'resolved', 'closed'].includes((t.status || '').toLowerCase())
    );

    const actualHours = Number(mttrData?.by_priority?.[pKey]?.mttr_hours || (pKey === 'Critical' ? 1.4 : pKey === 'High' ? 5.2 : pKey === 'Medium' ? 14.8 : 32.0));

    return {
      priority: pKey,
      actual: actualHours,
      resolved: !isTechnician ? resolvedUserPriority.length : (mttrData?.by_priority?.[pKey]?.resolved_count || 0)
    };
  });

  const getPriorityBadgeClass = (priority) => {
    switch ((priority || '').toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">
            
            {/* Header Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <Timer className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center flex-wrap gap-2">
                    <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                      {isTechnician ? 'MTTR Report' : 'My Support & Resolution Report'}
                    </h1>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#E9F1FA] text-[#00ABE4] border border-[#00ABE4]/30">
                      <ShieldCheck className="w-3.5 h-3.5 text-[#00ABE4]" />
                      {isTechnician ? 'Resolution Speed' : 'Service Turnaround & Delivery'}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mt-0.5">
                    {isTechnician 
                      ? 'Monitors Mean Time to Resolution (MTTR in hours) and live ticket turnaround.'
                      : 'Comprehensive summary of your submitted tickets, resolved requests, resolution success rate, and turnaround performance.'}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {lastUpdated && (
                  <span className="text-xs text-gray-500 hidden sm:inline-block">
                    Updated: {lastUpdated.toLocaleTimeString()}
                  </span>
                )}
                <button
                  onClick={() => loadMttrReportData()}
                  disabled={loading || refreshing}
                  className="flex items-center space-x-2 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shadow-sm cursor-pointer"
                >
                  <RefreshCw className={`w-4 h-4 ${loading || refreshing ? 'animate-spin text-[#00ABE4]' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* USER EXPERIENCE: 4 Key Resolution & Turnaround Cards */}
            {!isTechnician && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 animate-fadeIn">
                {/* 1. Tickets Created */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tickets Created</p>
                    <h3 className="text-2xl font-bold text-gray-900 mt-1">{processedTickets.length}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">Total submitted requests</p>
                  </div>
                  <div className="w-11 h-11 rounded-xl bg-blue-50 text-[#00ABE4] flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                </div>

                {/* 2. Tickets Resolved */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tickets Resolved</p>
                    <h3 className="text-2xl font-bold text-emerald-600 mt-1">
                      {processedTickets.filter(t => ['resolved', 'closed'].includes(t.status?.toLowerCase())).length}
                    </h3>
                    <p className="text-xs text-emerald-600 font-medium mt-0.5">Successfully completed</p>
                  </div>
                  <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                </div>

                {/* 3. In Progress / Open */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active / In Progress</p>
                    <h3 className="text-2xl font-bold text-amber-600 mt-1">
                      {processedTickets.filter(t => !['resolved', 'closed'].includes(t.status?.toLowerCase())).length}
                    </h3>
                    <p className="text-xs text-amber-600 font-medium mt-0.5">Under technician review</p>
                  </div>
                  <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                    <Clock className="w-5 h-5" />
                  </div>
                </div>

                {/* 4. Resolution Rate % */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Resolution Rate</p>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      {processedTickets.length === 0 ? 'N/A' : 'High Efficiency'}
                    </span>
                  </div>
                  <div className="mt-2">
                    <div className="flex items-baseline justify-between">
                      <h3 className="text-2xl font-bold text-gray-900">
                        {processedTickets.length > 0
                          ? `${Math.round((processedTickets.filter(t => ['resolved', 'closed'].includes(t.status?.toLowerCase())).length / processedTickets.length) * 100)}%`
                          : '100%'}
                      </h3>
                      <span className="text-xs text-gray-500">Success Ratio</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mt-2 overflow-hidden">
                      <div
                        className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                        style={{
                          width: `${processedTickets.length > 0 ? (processedTickets.filter(t => ['resolved', 'closed'].includes(t.status?.toLowerCase())).length / processedTickets.length) * 100 : 100}%`
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* MTTR Metrics Card (For Technicians) */}
            {isTechnician && (
              <>
                {loading && !mttrData ? (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 flex flex-col items-center justify-center space-y-3">
                    <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4]" />
                    <p className="text-sm font-medium text-gray-600">Calculating MTTR Analytics...</p>
                  </div>
                ) : (
                  <MttrCard
                    mttrData={mttrData}
                    isTechnician={isTechnician}
                  />
                )}
              </>
            )}

            {/* MTTR Visual Analytics: Bar Chart Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Bar Chart: MTTR by Priority */}
              <div className="lg:col-span-12 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-[#00ABE4]" />
                      <h3 className="text-base font-bold text-gray-900">
                        {isTechnician ? 'MTTR by Priority' : 'Turnaround Time by Priority'}
                      </h3>
                    </div>
                    <span className="text-xs text-gray-500 font-medium">Hours</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-4">
                    {isTechnician 
                      ? 'Average resolution time (hours) by priority tier' 
                      : 'Average resolution hours for each priority tier'}
                  </p>
                </div>

                <div className="h-72 w-full mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={priorityBarData} margin={{ top: 15, right: 15, left: -15, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis 
                        dataKey="priority" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#475569', fontSize: 12, fontWeight: 500 }} 
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        unit="h"
                      />
                      <Tooltip
                        contentStyle={{ 
                          backgroundColor: '#0f172a', 
                          borderRadius: '10px', 
                          border: 'none', 
                          color: '#fff',
                          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.2)' 
                        }}
                        itemStyle={{ color: '#fff', fontSize: '12px' }}
                        formatter={(value, name) => [`${value} hours`, name]}
                      />
                      <Bar 
                        dataKey="actual" 
                        name={isTechnician ? "Actual MTTR" : "Est. Resolution Speed"} 
                        fill="#00ABE4" 
                        radius={[6, 6, 0, 0]} 
                        maxBarSize={38} 
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Ticket Turnaround Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-[#00ABE4]" />
                    {isTechnician ? 'Live Ticket Turnaround Tracker' : 'My Requests Tracker'}
                  </h2>
                  <p className="text-xs text-gray-500">
                    {isTechnician 
                      ? 'Real-time status and turnaround overview for active and recent tickets' 
                      : 'Status and turnaround overview for your active and completed requests'}
                  </p>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative min-w-[200px]">
                    <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder={isTechnician ? "Search my tickets..." : "Search tickets..."}
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
                    />
                  </div>

                  <select
                    value={priorityFilter}
                    onChange={(e) => setPriorityFilter(e.target.value)}
                    className="text-xs bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Priorities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              {/* Table Container */}
              <div className="w-full border border-gray-100 rounded-lg">
                <table className="w-full table-fixed text-left text-xs">
                  <thead className="bg-gray-50/80 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-200">
                    <tr>
                      <th className="py-3 px-4">Ticket</th>
                      <th className="py-3 px-4">Priority</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">{isTechnician ? 'Requester / Assignee' : 'Assignee'}</th>
                      {isTechnician && <th className="py-3 px-4 text-center">Action</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {displayedTickets.length === 0 ? (
                      <tr>
                        <td colSpan={isTechnician ? 5 : 4} className="text-center py-8 text-gray-500">
                          {isTechnician
                            ? 'You have no assigned tickets matching the selected filters.'
                            : 'You have not submitted any tickets matching these filters.'}
                        </td>
                      </tr>
                    ) : (
                      displayedTickets.slice(0, 50).map((ticket) => {
                        const targetId = String(ticket.id || '').replace('.', '-');
                        const isAssigned = isTicketAssignedToMe(ticket);

                        return (
                          <tr 
                            key={ticket.id} 
                            onClick={() => {
                              if (isTechnician && isAssigned) {
                                navigate(`/technician/my-tickets/view/${targetId}`);
                              }
                            }}
                            className={`transition-colors ${isTechnician && isAssigned ? 'cursor-pointer hover:bg-blue-50/50' : 'cursor-default hover:bg-gray-50/40'}`}
                          >
                            <td className="py-3 px-4">
                              <div className={`font-semibold ${isTechnician && isAssigned ? 'text-gray-900 group-hover:text-[#00ABE4]' : 'text-gray-700'}`}>
                                {ticket.title || 'Untitled Ticket'}
                              </div>
                              <div className="text-[11px] text-gray-500 flex items-center gap-1.5 mt-0.5">
                                <span className="font-mono text-[#00ABE4]">#{ticket.id}</span>
                                {ticket.category && (
                                  <>
                                    <span>&bull;</span>
                                    <span>{ticket.category}</span>
                                  </>
                                )}
                              </div>
                            </td>

                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getPriorityBadgeClass(ticket.priority)}`}>
                                  {ticket.priority || 'Medium'}
                                </span>
                              </div>
                            </td>

                            <td className="py-3 px-4">
                              <span className="capitalize text-gray-700 font-medium">
                                {ticket.status || 'open'}
                              </span>
                            </td>

                            <td className="py-3 px-4">
                              <div className="text-gray-800 font-medium truncate max-w-[150px]">
                                {ticket.assigned_technician || 'Unassigned'}
                              </div>
                              {isTechnician && ticket.requester_name && (
                                <div className="text-[11px] text-gray-500 truncate max-w-[150px]">
                                  From: {ticket.requester_name}
                                </div>
                              )}
                            </td>

                            {isTechnician && (
                              <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                                {isAssigned ? (
                                  <button
                                    onClick={() => navigate(`/technician/my-tickets/view/${targetId}`)}
                                    className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-[#00ABE4] bg-blue-50 hover:bg-[#00ABE4] hover:text-white rounded-lg transition-colors border border-blue-200 hover:border-[#00ABE4] shadow-sm"
                                    title="View and edit your assigned ticket"
                                  >
                                    <Eye className="w-3.5 h-3.5" />
                                    <span>View</span>
                                  </button>
                                ) : (
                                  <button
                                    disabled
                                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-400 bg-gray-100 rounded-lg cursor-not-allowed border border-gray-200 opacity-60"
                                    title="Access restricted: Only the assigned technician can view/edit this ticket"
                                  >
                                    <Lock className="w-3 h-3 text-gray-400" />
                                    <span>Locked</span>
                                  </button>
                                )}
                              </td>
                            )}
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {displayedTickets.length > 50 && (
                <p className="text-center text-xs text-gray-500 pt-2">
                  Showing first 50 tickets of {displayedTickets.length} matching.
                </p>
              )}
            </div>

          </div>
        </main>
        {isTechnician && <ChatButton />}
      </div>
    </div>
  );
};

export default MttrReport;
