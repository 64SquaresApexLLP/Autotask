import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import { Search, Filter, Download, UserCheck, RotateCcw, AlertTriangle, Calendar, User, Loader2, Clock, CheckCircle, AlertCircle, Tag, X } from 'lucide-react';
import { ticketService } from '../../services/ticketService.js';
import { technicianService } from '../../services/technicianService.js';
import { ApiError } from '../../services/api.js';
import useAuth from '../../hooks/useAuth';

const AllTickets = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || 'all');
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get('category') || 'all');
  const [assignedFilter, setAssignedFilter] = useState(searchParams.get('assigned') || 'all');

  // Synchronize state when URL query parameters change
  useEffect(() => {
    const cat = searchParams.get('category');
    if (cat) {
      setCategoryFilter(cat);
    }
    const prio = searchParams.get('priority');
    if (prio) {
      setPriorityFilter(prio);
    }
    const stat = searchParams.get('status');
    if (stat) {
      setStatusFilter(stat);
    }
  }, [searchParams]);

  // Load tickets and technicians on component mount
  useEffect(() => {
    loadTickets();
    loadTechnicians();
  }, []);

  const loadTickets = async () => {
    try {
      setLoading(true);
      setError('');
      const allTickets = await ticketService.getAllTickets();
      setTickets(allTickets || []);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      setError('Failed to load tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadTechnicians = async () => {
    try {
      const techList = await technicianService.getAllTechnicians();
      setTechnicians(techList || []);
    } catch (error) {
      console.error('Failed to load technicians:', error);
      setTechnicians([]);
    }
  };

  const assignTicket = async (ticketId, technicianId) => {
    try {
      setError('');
      await ticketService.assignTicket(ticketId, technicianId);
      await loadTickets(); // Reload tickets to show updated assignment
    } catch (error) {
      console.error('Failed to assign ticket:', error);
      setError('Failed to assign ticket. Please try again.');
    }
  };

  const updateTicketStatus = async (ticketId, newStatus) => {
    try {
      setError('');
      await ticketService.updateTicketStatus(ticketId, newStatus);
      await loadTickets(); // Reload tickets to show updated status
    } catch (error) {
      console.error('Failed to update ticket status:', error);
      setError('Failed to update ticket status. Please try again.');
    }
  };

  // Extract dynamic list of unique categories from real ticket dataset
  const availableCategories = Array.from(
    new Set(
      tickets
        .map(t => t.category || t.ticket_category || t.issue_type)
        .filter(Boolean)
    )
  ).sort();

  // Filter tickets based on search, category, and filter criteria
  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.requester_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.id?.toString().includes(searchTerm);

    const matchesStatus = statusFilter === 'all' || ticket.status?.toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority = priorityFilter === 'all' || ticket.priority?.toLowerCase() === priorityFilter.toLowerCase();
    const matchesAssigned = assignedFilter === 'all' || ticket.assigned_technician === assignedFilter;

    // Dynamic Category match
    const ticketCat = (ticket.category || ticket.ticket_category || ticket.issue_type || '').toLowerCase();
    const filterCat = categoryFilter.toLowerCase();
    const matchesCategory = categoryFilter === 'all' || 
      ticketCat === filterCat || 
      ticketCat.includes(filterCat) || 
      filterCat.includes(ticketCat);

    return matchesSearch && matchesStatus && matchesPriority && matchesAssigned && matchesCategory;
  });

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'resolved':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'in_progress':
      case 'progress':
      case 'assigned':
        return <Clock className="w-5 h-5 text-blue-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
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

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'resolved':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
      case 'progress':
      case 'assigned':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'open':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header onRefresh={loadTickets} isRefreshing={loading} />
        <main className=" p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">All Tickets</h1>
              <p className="text-gray-600">Manage all system-wide tickets</p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Total Tickets</p>
                <p className="text-2xl font-bold">{loading ? <Loader2 className="w-6 h-6 animate-spin" /> : tickets.length}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Unassigned</p>
                <p className="text-2xl font-bold text-orange-600">
                  {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : tickets.filter(t => !t.assigned_technician || t.assigned_technician === 'Unassigned').length}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Critical / High</p>
                <p className="text-2xl font-bold text-red-600">
                  {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : tickets.filter(t => ['critical', 'high'].includes(t.priority?.toLowerCase())).length}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Open / Progress</p>
                <p className="text-2xl font-bold text-blue-600">
                  {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : tickets.filter(t => ['open', 'progress', 'in_progress'].includes(t.status?.toLowerCase())).length}
                </p>
              </div>
            </div>

            {/* Active Category Filter Alert Banner */}
            {categoryFilter !== 'all' && (
              <div className="flex items-center justify-between bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-xl shadow-sm animate-fadeIn">
                <div className="flex items-center gap-2.5">
                  <span className="text-xl"></span>
                  <div>
                    <span className="font-semibold text-sm">Active Category Filter: </span>
                    <span className="font-bold text-blue-900 bg-blue-100/80 px-2 py-0.5 rounded border border-blue-300 ml-1">
                      {categoryFilter}
                    </span>
                    <span className="text-xs text-blue-600 ml-2">
                      ({filteredTickets.length} ticket{filteredTickets.length === 1 ? '' : 's'} matching)
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setCategoryFilter('all');
                    setSearchParams({});
                  }}
                  className="flex items-center gap-1 text-xs bg-white hover:bg-blue-100 text-blue-700 font-bold px-3 py-1.5 rounded-lg border border-blue-300 transition shadow-sm cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Show All Categories</span>
                </button>
              </div>
            )}

            {/* Filter Card */}
            <div className="bg-white rounded-lg shadow p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Filter className="h-5 w-5 text-gray-500" />
                  <h2 className="text-lg font-semibold text-gray-800">Filter Tickets</h2>
                </div>
                {(categoryFilter !== 'all' || priorityFilter !== 'all' || statusFilter !== 'all' || assignedFilter !== 'all' || searchTerm) && (
                  <button
                    onClick={() => {
                      setCategoryFilter('all');
                      setPriorityFilter('all');
                      setStatusFilter('all');
                      setAssignedFilter('all');
                      setSearchTerm('');
                      setSearchParams({});
                    }}
                    className="text-xs text-blue-600 hover:underline font-medium cursor-pointer"
                  >
                    Reset all filters
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                <input
                  type="text"
                  placeholder="Search title, ID, requester..."
                  className="px-3 py-2 border rounded-lg w-full text-sm"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
                <select
                  value={categoryFilter}
                  onChange={e => {
                    setCategoryFilter(e.target.value);
                    if (e.target.value === 'all') {
                      searchParams.delete('category');
                      setSearchParams(searchParams);
                    } else {
                      setSearchParams({ ...Object.fromEntries(searchParams.entries()), category: e.target.value });
                    }
                  }}
                  className="px-3 py-2 border rounded-lg w-full text-sm font-medium bg-white"
                >
                  <option value="all">📁 All Categories</option>
                  {availableCategories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 border rounded-lg w-full text-sm bg-white">
                  <option value="all">All Status</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="assigned">Assigned</option>
                  <option value="resolved">Resolved</option>
                  <option value="completed">Completed</option>
                </select>
                <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="px-3 py-2 border rounded-lg w-full text-sm bg-white">
                  <option value="all">All Priority</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select value={assignedFilter} onChange={e => setAssignedFilter(e.target.value)} className="px-3 py-2 border rounded-lg w-full text-sm bg-white">
                  <option value="all">All Technicians</option>
                  <option value="">Unassigned</option>
                  {technicians.map(t => (
                    <option key={t.id || t.username} value={t.username || t.name}>{t.name || t.username}</option>
                  ))}
                </select>
                <button
                  onClick={loadTickets}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ABE4] hover:bg-blue-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center justify-center space-x-2 text-sm cursor-pointer"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="w-full bg-white rounded-lg shadow">
              {loading && tickets.length === 0 ? (
                <div className="p-8 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading tickets...</p>
                </div>
              ) : filteredTickets.length === 0 ? (
                <div className="p-8 text-center">
                  <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets found</p>
                  <p className="text-gray-500 text-sm">
                    {categoryFilter !== 'all' 
                      ? `No tickets currently match category "${categoryFilter}".`
                      : 'Try adjusting your filters or create a new ticket.'}
                  </p>
                  {categoryFilter !== 'all' && (
                    <button
                      onClick={() => {
                        setCategoryFilter('all');
                        setSearchParams({});
                      }}
                      className="mt-3 inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 font-semibold px-3 py-1.5 rounded-lg border border-blue-200 hover:bg-blue-100 transition"
                    >
                      Show All Categories
                    </button>
                  )}
                </div>
              ) : (
                <table className="w-full table-fixed text-sm text-left">
                  <thead className="bg-gray-100 border-b">
                    <tr>
                      <th className="p-3">#</th>
                      <th className="p-3">Title</th>
                      <th className="p-3">Category</th>
                      <th className="p-3">Requester</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Priority</th>
                      <th className="p-3">Technician</th>
                      <th className="p-3">Created</th>
                      <th className="p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTickets.map((ticket, idx) => (
                      <tr key={ticket.id} className="border-b hover:bg-gray-50">
                        <td className="p-3 font-mono text-xs font-bold text-slate-700">#{ticket.id}</td>
                        <td className="p-3">
                          <div>
                            <div className="font-medium text-slate-900">{ticket.title}</div>
                            <div className="text-xs text-gray-500 truncate max-w-xs">{ticket.description}</div>
                          </div>
                        </td>
                        <td className="p-3">
                          <span
                            onClick={() => {
                              const cat = ticket.category || ticket.ticket_category || ticket.issue_type;
                              if (cat) {
                                setCategoryFilter(cat);
                                setSearchParams({ category: cat });
                              }
                            }}
                            className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 transition cursor-pointer"
                            title="Filter by this category"
                          >
                             {ticket.category || ticket.ticket_category || ticket.issue_type || 'General'}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-1">
                            <User className="w-4 h-4 text-gray-400" />
                            <span>{ticket.requester_name || ticket.user_email || 'Unknown'}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                            {ticket.status || 'Open'}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                            {ticket.priority || 'Medium'}
                          </span>
                        </td>
                        <td className="p-3">
                          {!ticket.assigned_technician ? (
                            <span className="text-orange-600 font-medium flex items-center">
                              <AlertTriangle className="w-4 h-4 mr-1" />
                              Unassigned
                            </span>
                          ) : (
                            <span className="flex items-center">
                              <UserCheck className="w-4 h-4 mr-1 text-green-600" />
                              {ticket.assigned_technician}
                            </span>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4 text-gray-400" />
                            <span>{new Date(ticket.created_at || Date.now()).toLocaleDateString()}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center space-x-2">
                            {!ticket.assigned_technician && (
                              <select
                                onChange={(e) => e.target.value && assignTicket(ticket.id, e.target.value)}
                                className="text-xs px-2 py-1 border rounded"
                                defaultValue=""
                              >
                                <option value="">Assign to...</option>
                                {technicians.map(tech => (
                                  <option key={tech.id || tech.username} value={tech.username || tech.name}>
                                    {tech.name || tech.username}
                                  </option>
                                ))}
                              </select>
                            )}
                            <select
                              value={ticket.status || 'open'}
                              onChange={(e) => updateTicketStatus(ticket.id, e.target.value)}
                              className="text-xs px-2 py-1 border rounded"
                            >
                              <option value="open">Open</option>
                              <option value="in_progress">In Progress</option>
                              <option value="assigned">Assigned</option>
                              <option value="resolved">Resolved</option>
                              <option value="completed">Completed</option>
                            </select>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>



          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default AllTickets;
