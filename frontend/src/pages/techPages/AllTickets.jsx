import React, { useState, useEffect } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import { Search, Filter, Download, UserCheck, RotateCcw, AlertTriangle, Calendar, User, Loader2, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { ticketService } from '../../services/ticketService.js';
import { technicianService } from '../../services/technicianService.js';
import { ApiError } from '../../services/api.js';
import useAuth from '../../hooks/useAuth';

const AllTickets = () => {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [assignedFilter, setAssignedFilter] = useState('all');

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
      // Use fallback technicians with real IDs if API fails
      setTechnicians([
        { id: 'T001', name: 'Technician T001', username: 'T001' },
        { id: 'T103', name: 'Technician T103', username: 'T103' },
        { id: 'T104', name: 'Technician T104', username: 'T104' },
        { id: 'T106', name: 'Technician T106', username: 'T106' }
      ]);
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

  // Filter tickets based on search and filter criteria
  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.requester_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.id?.toString().includes(searchTerm);

    const matchesStatus = statusFilter === 'all' || ticket.status?.toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority = priorityFilter === 'all' || ticket.priority?.toLowerCase() === priorityFilter.toLowerCase();
    const matchesAssigned = assignedFilter === 'all' || ticket.assigned_technician === assignedFilter;

    return matchesSearch && matchesStatus && matchesPriority && matchesAssigned;
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
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">📋 All Tickets</h1>
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

            {/* Filter Card */}
            <div className="bg-white rounded-lg shadow p-4 space-y-4">
              <div className="flex items-center gap-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <h2 className="text-lg font-semibold text-gray-800">Filter Tickets</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                <input
                  type="text"
                  placeholder="Search..."
                  className="px-3 py-2 border rounded w-full"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Status</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="assigned">Assigned</option>
                  <option value="resolved">Resolved</option>
                  <option value="completed">Completed</option>
                </select>
                <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Priority</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select value={assignedFilter} onChange={e => setAssignedFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Technicians</option>
                  <option value="">Unassigned</option>
                  {technicians.map(t => (
                    <option key={t.id || t.username} value={t.username || t.name}>{t.name || t.username}</option>
                  ))}
                </select>
                <button
                  onClick={loadTickets}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ABE4] text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-auto bg-white rounded-lg shadow">
              {loading && tickets.length === 0 ? (
                <div className="p-8 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading tickets...</p>
                </div>
              ) : filteredTickets.length === 0 ? (
                <div className="p-8 text-center">
                  <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets found</p>
                  <p className="text-gray-500">Try adjusting your filters or create a new ticket.</p>
                </div>
              ) : (
                <table className="min-w-full text-sm text-left">
                  <thead className="bg-gray-100 border-b">
                    <tr>
                      <th className="p-3">#</th>
                      <th className="p-3">Title</th>
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
                        <td className="p-3 font-mono text-xs">#{ticket.id}</td>
                        <td className="p-3">
                          <div>
                            <div className="font-medium">{ticket.title}</div>
                            <div className="text-xs text-gray-500 truncate max-w-xs">{ticket.description}</div>
                          </div>
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
