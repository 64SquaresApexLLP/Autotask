import React, { useState, useEffect } from 'react';
import { FileText, Plus, Clock, CheckCircle, ChevronUp, Loader2, Eye, Sparkles, User, Phone, Mail, Calendar } from 'lucide-react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import AiPipelineModal from '../components/AiPipelineModal.jsx';
import ExpandedTicketDetails from '../components/ExpandedTicketDetails.jsx';
import { ticketService } from '../services/ticketService.js';
import { ApiError } from '../services/api.js';
import useAuth from '../hooks/useAuth';
import { calculateTicketSla } from '../components/MttrCard';

const UserDashboard = () => {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingTicket, setCreatingTicket] = useState(false);
  const [aiPipelineOpen, setAiPipelineOpen] = useState(false);
  const [aiPipelineSubmitted, setAiPipelineSubmitted] = useState(null);
  const [aiPipelineResult, setAiPipelineResult] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [expandedTicketId, setExpandedTicketId] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    requester_name: user?.full_name || user?.username || '',
    phone_number: user?.phone_number || user?.phone || '',
    user_email: user?.email || user?.username || ''
  });

  useEffect(() => {
    console.log(tickets)
  }, [tickets]);

  // Load user's tickets on component mount
  useEffect(() => {
    loadUserTickets();
  }, []);

  // Keep the signed-in user's contact info in sync with the create-ticket form.
  // These fields (name, phone, email) are read-only on the form and are
  // automatically attached to every ticket the user creates.

  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      requester_name: user?.full_name || user?.username || '',
      phone_number: user?.phone_number || user?.phone || '',
      user_email: user?.email || user?.username || ''
    }));
  }, [user]);

  const loadUserTickets = async () => {
    try {
      setLoading(true);
      setError('');

      const userId = user?.username?.trim().toLowerCase();
      const userEmail = user?.email?.trim().toLowerCase();

      // Load all tickets
      const allTickets = await ticketService.getAllTickets({ limit: 150 });

      // Filter tickets for current user with case-insensitivity
      const userName = (user?.name || user?.full_name)?.trim().toLowerCase();
      const userRole = user?.role?.toLowerCase();

      let userTickets = allTickets;
      if (userRole === 'user' && (userId || userEmail || userName)) {
        const matching = allTickets.filter(ticket => {
          const tEmail = ticket.user_email?.trim().toLowerCase();
          const tUserId = ticket.user_id?.trim().toLowerCase();
          const tReqName = ticket.requester_name?.trim().toLowerCase();
          return (userEmail && tEmail === userEmail) ||
            (userId && tUserId === userId) ||
            (userId && tReqName === userId) ||
            (userName && tReqName === userName) ||
            (userName && tEmail === userName);
        });
        userTickets = matching.length > 0 ? matching : allTickets;
      }

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
      setAiPipelineResult(null);
      setAiPipelineSubmitted({ title: formData.title, description: formData.description });
      setAiPipelineOpen(true);

      const ticketData = {
        ...formData,
        user_email: formData.user_email || user?.email || user?.username,
        requester_name: formData.requester_name || user?.full_name || user?.username,
        phone_number: formData.phone_number || user?.phone_number || user?.phone || ''
      };

      // Single real call to the AI workflow - the pipeline modal shows a
      // loading state until this resolves, then renders the actual
      // extraction/classification/resolution/assignment output it returns.
      const created = await ticketService.createTicket(ticketData);
      setAiPipelineResult(created);

      // Reset form now; the AI pipeline modal stays up until the user closes it
      setFormData({
        title: '',
        description: '',
        priority: 'medium',
        due_date: '',
        requester_name: user?.full_name || user?.username || '',
        phone_number: user?.phone_number || user?.phone || '',
        user_email: user?.email || user?.username || ''
      });
      setShowCreateForm(false);

      await loadUserTickets();

    } catch (error) {
      console.error('Failed to create ticket:', error);
      setError(error.message || 'Failed to create ticket. Please try again.');
      setAiPipelineOpen(false);
    } finally {
      setCreatingTicket(false);
    }
  };

  const closeAiPipeline = () => {
    setAiPipelineOpen(false);
    setAiPipelineResult(null);
    setAiPipelineSubmitted(null);
    setSuccessMessage('Ticket created successfully! Your request has been submitted and processed by our AI system.');
    setTimeout(() => setSuccessMessage(''), 5000);
    // Re-fetch right as the modal closes so the new ticket is guaranteed to
    // be visible immediately, even if the earlier background reload raced
    // with the ticket becoming visible in the database.
    loadUserTickets();
  };

  const toggleTicket = (ticketId) => {
    setExpandedTicketId(prev => prev === ticketId ? null : ticketId);
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

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1">
        <Header onRefresh={loadUserTickets} isRefreshing={loading} />
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

              {/* <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">Open Tickets</h3>
                    <p className="text-2xl font-bold text-yellow-600 mt-2">
                      {tickets.filter(t => !['completed', 'resolved'].includes(t.status?.toLowerCase())).length}
                    </p>
                  </div>
                  <Clock className="w-8 h-8 text-yellow-600" />
                </div>
              </div> */}

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
                        value={formData.requester_name || user?.full_name || user?.username || ''}
                        onChange={handleInputChange}
                        readOnly
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder={user?.full_name || user?.username || "Your name"}
                        title="Your name is taken from your profile and cannot be changed"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        name="phone_number"
                        value={formData.phone_number || user?.phone_number || user?.phone || ''}
                        onChange={handleInputChange}
                        readOnly
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder="Your phone number"
                        title="Your phone number is taken from your profile and cannot be changed"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Due Date <span className="text-gray-400 font-normal">(optional)</span>
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
                        value={formData.user_email || user?.email || user?.username || ''}
                        onChange={handleInputChange}
                        readOnly
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent"
                        placeholder={user?.email || user?.username || "your.email@example.com"}
                        title="Your email is taken from your profile and cannot be changed"
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
                <h2 className="text-lg md:text-xl font-semibold text-gray-800">Recent Ticket</h2>
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
                  { tickets.slice(0, 1).map((ticket) => {
                    const sla = calculateTicketSla(ticket);
                    const slaBadgeClass = sla.color === 'red'
                      ? 'bg-red-100 text-red-700 border-red-200'
                      : sla.color === 'amber'
                        ? 'bg-amber-100 text-amber-700 border-amber-200'
                        : sla.color === 'blue'
                          ? 'bg-blue-100 text-blue-700 border-blue-200'
                          : 'bg-emerald-100 text-emerald-700 border-emerald-200';

                    return (
                      <div key={ticket.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center flex-wrap gap-2 mb-2">
                              <h3 className="text-lg font-semibold text-gray-800">{ticket.title}</h3>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                                {ticket.priority || 'Medium'}
                              </span>
                              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-md border ${slaBadgeClass}`}>
                                {sla.text}
                              </span>
                            </div>
                            <p className="text-gray-600 mb-3">{ticket.description}</p>

                            {(ticket.ticket_category || ticket.issue_type) && (
                              <div className="flex items-center flex-wrap gap-2 mb-3">
                                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-[#E9F1FA] text-[#00ABE4]">
                                  <Sparkles className="w-3 h-3" />
                                  {ticket.ticket_category || ticket.issue_type}
                                </span>
                                {ticket.issue_type && ticket.issue_type !== ticket.ticket_category && (
                                  <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                    {ticket.issue_type}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-3 shrink-0">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                              {ticket.priority || 'Medium'}
                            </span>
                            <button
                              type="button"
                              onClick={(event) => { event.stopPropagation(); toggleTicket(ticket.id); }}
                              className="p-2 rounded-lg text-[#00ABE4] hover:bg-[#E9F1FA] transition-colors"
                              title={expandedTicketId === ticket.id ? 'Collapse ticket details' : 'View all ticket details'}
                              aria-label={expandedTicketId === ticket.id ? 'Collapse ticket details' : 'View all ticket details'}
                            >
                              {expandedTicketId === ticket.id ? <ChevronUp className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                            </button>
                          </div>
                        </div>

                        {expandedTicketId === ticket.id && (
                          <ExpandedTicketDetails ticket={ticket} />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Real AI Pipeline Visualization */}
      {aiPipelineOpen && (
        <AiPipelineModal
          submitted={aiPipelineSubmitted}
          result={aiPipelineResult}
          onClose={closeAiPipeline}
        />
      )}
    </div>
  );
};

export default UserDashboard;