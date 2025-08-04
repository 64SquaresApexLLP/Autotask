import React, { useState, useEffect } from 'react';
import { FileText, Plus, Clock, AlertCircle, CheckCircle, User, Calendar, Phone, Mail, Loader2 } from 'lucide-react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import { ticketService } from '../services/ticketService.js';
import { ApiError } from '../services/api.js';
import useAuth from '../hooks/useAuth';

const UserDashboard = () => {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingTicket, setCreatingTicket] = useState(false);
  const [creationProgress, setCreationProgress] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    requester_name: '',
    phone_number: '',
    user_email: ''
  });

  // Load user's tickets on component mount
  useEffect(() => {
    loadUserTickets();
  }, []);

  const loadUserTickets = async () => {
    try {
      setLoading(true);
      setError('');

      // For demo purposes, let's load all tickets and filter on frontend
      // In production, you'd want to filter by user email on backend
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

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title || !formData.description) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setCreatingTicket(true);
      setError('');
      setCreationProgress(null);

      const ticketData = {
        ...formData,
        user_email: user?.email || user?.username,
        requester_name: formData.requester_name || user?.full_name || user?.username
      };

      // Use the new polling method with progress updates
      try {
        await ticketService.createTicketWithPolling(ticketData, (progress) => {
          setCreationProgress(progress);
        });
      } catch (pollingError) {
        // Fallback to regular creation if polling fails
        console.warn('Polling method failed, falling back to regular creation:', pollingError);
        setCreationProgress({
          stage: 'fallback',
          message: 'Processing with standard method...',
          progress: 50
        });
        await ticketService.createTicket(ticketData);
      }

      // Reset form and reload tickets
      setFormData({
        title: '',
        description: '',
        priority: 'medium',
        due_date: '',
        requester_name: '',
        phone_number: '',
        user_email: ''
      });
      setShowCreateForm(false);
      setCreationProgress(null);
      setSuccessMessage('Ticket created successfully! Your request has been submitted and processed by our AI system.');

      // Wait a moment then reload tickets
      setTimeout(async () => {
        await loadUserTickets();
        // Clear success message after showing tickets
        setTimeout(() => setSuccessMessage(''), 5000);
      }, 1000);

    } catch (error) {
      console.error('Failed to create ticket:', error);
      setError(error.message || 'Failed to create ticket. Please try again.');
      setCreationProgress(null);
    } finally {
      setCreatingTicket(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high':
      case 'critical':
        return 'text-red-600 bg-red-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'resolved':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'in_progress':
      case 'assigned':
        return <Clock className="w-5 h-5 text-blue-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1">
        <Header />
        <main className="p-6 md:p-8">
          <div className="max-w-6xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-800 mb-3">User Dashboard</h1>
              <p className="text-gray-600 text-base md:text-lg">Welcome back, {user?.full_name || user?.username}! Submit and track your requests here.</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
                {error}
              </div>
            )}

            {successMessage && (
              <div className="mb-6 p-4 bg-green-50 text-green-600 rounded-lg border border-green-200 flex items-center space-x-2">
                <CheckCircle className="w-5 h-5" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">Total Tickets</h3>
                    <p className="text-2xl font-bold text-[#00ABE4] mt-2">{tickets.length}</p>
                  </div>
                  <FileText className="w-8 h-8 text-[#00ABE4]" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">Open Tickets</h3>
                    <p className="text-2xl font-bold text-yellow-600 mt-2">
                      {tickets.filter(t => !['completed', 'resolved'].includes(t.status?.toLowerCase())).length}
                    </p>
                  </div>
                  <Clock className="w-8 h-8 text-yellow-600" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">Resolved</h3>
                    <p className="text-2xl font-bold text-green-600 mt-2">
                      {tickets.filter(t => ['completed', 'resolved'].includes(t.status?.toLowerCase())).length}
                    </p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
              </div>
            </div>

            {/* Create New Ticket Section */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8 mb-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg md:text-xl font-semibold text-gray-800">Create New Ticket</h2>
                <button
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="flex items-center space-x-2 bg-[#00ABE4] text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                >
                  <Plus className="w-5 h-5" />
                  <span>New Ticket</span>
                </button>
              </div>

              {showCreateForm && (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Title *
                      </label>
                      <input
                        type="text"
                        name="title"
                        value={formData.title}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder="Brief description of the issue"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Priority
                      </label>
                      <select
                        name="priority"
                        value={formData.priority}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Your Name
                      </label>
                      <input
                        type="text"
                        name="requester_name"
                        value={formData.requester_name}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder={user?.full_name || user?.username || "Your name"}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        name="phone_number"
                        value={formData.phone_number}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder="Your phone number"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Due Date
                      </label>
                      <input
                        type="date"
                        name="due_date"
                        value={formData.due_date}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Email
                      </label>
                      <input
                        type="email"
                        name="user_email"
                        value={formData.user_email}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder={user?.email || user?.username || "your.email@example.com"}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description *
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleInputChange}
                      rows={4}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                      placeholder="Please provide detailed information about your request..."
                      required
                    />
                  </div>

                  <div className="flex space-x-4">
                    <button
                      type="submit"
                      disabled={creatingTicket}
                      className="flex items-center space-x-2 bg-[#00ABE4] text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {creatingTicket ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Plus className="w-5 h-5" />
                      )}
                      <span>{creatingTicket ? 'Creating...' : 'Create Ticket'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowCreateForm(false)}
                      disabled={creatingTicket}
                      className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* My Tickets Section */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg md:text-xl font-semibold text-gray-800">My Tickets</h2>
                <button
                  onClick={loadUserTickets}
                  disabled={loading}
                  className="flex items-center space-x-2 text-[#00ABE4] hover:text-blue-600 transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Clock className="w-5 h-5" />
                  )}
                  <span>Refresh</span>
                </button>
              </div>

              {loading && tickets.length === 0 ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading your tickets...</p>
                </div>
              ) : tickets.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets found</p>
                  <p className="text-gray-500">Create your first ticket to get started!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {tickets.map((ticket) => (
                    <div key={ticket.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            {getStatusIcon(ticket.status)}
                            <h3 className="text-lg font-semibold text-gray-800">{ticket.title}</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                              {ticket.priority || 'Medium'}
                            </span>
                          </div>
                          <p className="text-gray-600 mb-3">{ticket.description}</p>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-500">
                            <div className="flex items-center space-x-2">
                              <User className="w-4 h-4" />
                              <span>Requester: {ticket.requester_name || 'Not specified'}</span>
                            </div>
                            {ticket.phone_number && (
                              <div className="flex items-center space-x-2">
                                <Phone className="w-4 h-4" />
                                <span>{ticket.phone_number}</span>
                              </div>
                            )}
                            {ticket.user_email && (
                              <div className="flex items-center space-x-2">
                                <Mail className="w-4 h-4" />
                                <span>{ticket.user_email}</span>
                              </div>
                            )}
                            {ticket.due_date && (
                              <div className="flex items-center space-x-2">
                                <Calendar className="w-4 h-4" />
                                <span>Due: {new Date(ticket.due_date).toLocaleDateString()}</span>
                              </div>
                            )}
                            <div className="flex items-center space-x-2">
                              <Clock className="w-4 h-4" />
                              <span>Created: {new Date(ticket.created_at || Date.now()).toLocaleDateString()}</span>
                            </div>
                            {ticket.assigned_technician && (
                              <div className="flex items-center space-x-2">
                                <User className="w-4 h-4" />
                                <span>Assigned to: {ticket.assigned_technician}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="ml-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            ticket.status?.toLowerCase() === 'completed' || ticket.status?.toLowerCase() === 'resolved'
                              ? 'text-green-600 bg-green-50'
                              : ticket.status?.toLowerCase() === 'in_progress' || ticket.status?.toLowerCase() === 'assigned'
                              ? 'text-blue-600 bg-blue-50'
                              : 'text-yellow-600 bg-yellow-50'
                          }`}>
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

      {/* Progress Modal */}
      {creatingTicket && creationProgress && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mb-4">
                <Loader2 className="w-12 h-12 animate-spin text-[#00ABE4] mx-auto" />
              </div>

              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Creating Your Ticket
              </h3>

              <p className="text-gray-600 mb-4">
                {creationProgress.message}
              </p>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div
                  className="bg-[#00ABE4] h-2 rounded-full transition-all duration-500"
                  style={{ width: `${creationProgress.progress}%` }}
                ></div>
              </div>

              <div className="flex justify-between text-sm text-gray-500">
                <span>{creationProgress.progress}% Complete</span>
                {creationProgress.elapsed && (
                  <span>{creationProgress.elapsed}s elapsed</span>
                )}
              </div>

              {creationProgress.stage === 'processing' && (
                <div className="mt-4 text-xs text-gray-500">
                  <p>⚡ Our AI is analyzing your request and generating an automated resolution.</p>
                  <p className="mt-1">This process typically takes 60-90 seconds.</p>
                  {creationProgress.isLongRunning && (
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-700">
                      <p>⏱️ This is taking longer than usual. Please don't close this window.</p>
                      <p>Your ticket will be created successfully.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserDashboard;