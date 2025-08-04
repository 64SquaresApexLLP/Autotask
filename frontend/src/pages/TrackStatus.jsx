import React, { useState, useEffect } from 'react';
import { Search, Clock, AlertCircle, CheckCircle, User, Calendar, Phone, Mail, Loader2, FileText } from 'lucide-react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import { ticketService } from '../services/ticketService.js';
import { ApiError } from '../services/api.js';
import useAuth from '../hooks/useAuth';

const TrackStatus = () => {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Load user's tickets on component mount
  useEffect(() => {
    loadUserTickets();
  }, []);

  const loadUserTickets = async () => {
    try {
      setLoading(true);
      setError('');

      // Load all tickets and filter on frontend
      const allTickets = await ticketService.getAllTickets({ limit: 100 });

      // Filter tickets for current user using real user ID from USER_DUMMY_DATA
      const userId = user?.username; // This will be U001 or U002
      const userEmail = user?.email;
      const userTickets = allTickets.filter(ticket => {
        return ticket.user_email === userEmail ||
               ticket.user_id === userId ||
               ticket.requester_name === userId;
      });

      setTickets(userTickets || []);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      setError('Failed to load your tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Filter tickets based on search and status
  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.id?.toString().includes(searchTerm);
    
    const matchesStatus = statusFilter === 'all' || ticket.status?.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
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
            
            {/* Header */}
            <div>
              <h1 className="text-3xl font-bold text-gray-900">📋 Track Ticket Status</h1>
              <p className="text-gray-600 mt-2">Monitor the progress of your submitted tickets</p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Search and Filter */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      type="text"
                      placeholder="Search tickets by title, description, or ID..."
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                </div>
                <div className="md:w-48">
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                  >
                    <option value="all">All Status</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="assigned">Assigned</option>
                    <option value="resolved">Resolved</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                <button
                  onClick={loadUserTickets}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ABE4] text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Tickets List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-6">Your Tickets</h2>
              
              {loading && tickets.length === 0 ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading your tickets...</p>
                </div>
              ) : filteredTickets.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets found</p>
                  <p className="text-gray-500">
                    {searchTerm || statusFilter !== 'all' 
                      ? 'Try adjusting your search or filter criteria.' 
                      : 'You haven\'t submitted any tickets yet.'}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredTickets.map((ticket) => (
                    <div key={ticket.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            {getStatusIcon(ticket.status)}
                            <h3 className="text-lg font-semibold text-gray-800">#{ticket.id} - {ticket.title}</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                              {ticket.priority || 'Medium'}
                            </span>
                          </div>
                          <p className="text-gray-600 mb-3">{ticket.description}</p>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-500">
                            <div className="flex items-center space-x-2">
                              <User className="w-4 h-4" />
                              <span>Requester: {ticket.requester_name || 'Not specified'}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Calendar className="w-4 h-4" />
                              <span>Created: {new Date(ticket.created_at || Date.now()).toLocaleDateString()}</span>
                            </div>
                            {ticket.due_date && (
                              <div className="flex items-center space-x-2">
                                <Clock className="w-4 h-4" />
                                <span>Due: {new Date(ticket.due_date).toLocaleDateString()}</span>
                              </div>
                            )}
                            {ticket.assigned_technician && (
                              <div className="flex items-center space-x-2">
                                <User className="w-4 h-4" />
                                <span>Assigned to: {ticket.assigned_technician}</span>
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="ml-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                            {ticket.status || 'Open'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default TrackStatus;
