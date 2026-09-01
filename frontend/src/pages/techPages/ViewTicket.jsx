import React from 'react'
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';
import Header from '../../components/Header';
import ChatButton from '../../components/ChatButton';
import { ticketService } from '../../services/ticketService';
import useAuth from '../../hooks/useAuth';
import { 
  Loader2, 
  Sparkles, 
  Tag, 
  Layers, 
  Link2, 
  CheckCircle2, 
  Pencil, 
  PlayCircle, 
  CheckCircle, 
  XCircle, 
  Lock, 
  ShieldAlert,
  Clock
} from 'lucide-react';

const statusColors = {
  open: 'bg-yellow-100 text-yellow-800',
  new: 'bg-yellow-100 text-yellow-800',
  'in-progress': 'bg-blue-100 text-blue-800',
  'in progress': 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-800',
};

const priorityColors = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-100 text-red-800',
};

function ViewTicket() {
  const { ticketId } = useParams();
  const tId = ticketId.replace('-', '.');
  const navigate = useNavigate();
  const { user } = useAuth();

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [newStatus, setNewStatus] = useState('');
  const [timeSpent, setTimeSpent] = useState('');
  const [newWorkNote, setNewWorkNote] = useState('');

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null); // { type: 'success'|'error', text }

  const [emailing, setEmailing] = useState(false);
  const [emailMessage, setEmailMessage] = useState(null);

  const [similarTickets, setSimilarTickets] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  const [editingResolution, setEditingResolution] = useState(false);
  const [editedResolutionText, setEditedResolutionText] = useState('');
  const [resolutionMessage, setResolutionMessage] = useState(null);
  const [resolutionActionLoading, setResolutionActionLoading] = useState(false);

  const [quickAction, setQuickAction] = useState(null); // which lifecycle action is in flight
  const [quickActionMessage, setQuickActionMessage] = useState(null);

  const currentUserId = (user?.username || '').trim().toLowerCase();
  const currentUserEmail = (user?.email || '').trim().toLowerCase();
  const currentFullName = (user?.full_name || user?.name || '').trim().toLowerCase();

  const assignedTech = (ticket?.assigned_technician || '').trim().toLowerCase();
  const techId = (ticket?.technician_id || '').trim().toLowerCase();
  const techEmail = (ticket?.technician_email || '').trim().toLowerCase();

  const isAssignedToMe = Boolean(
    !user || user.role === 'admin' ||
    (currentUserId && (assignedTech === currentUserId || techId === currentUserId)) ||
    (currentUserEmail && (techEmail === currentUserEmail || assignedTech === currentUserEmail)) ||
    (currentFullName && (assignedTech === currentFullName || assignedTech.includes(currentFullName)))
  );

  const fetchTicket = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const data = await ticketService.getTicketById(tId);
      setTicket(data);
      return data;
    } catch (error) {
      console.error('Failed to load ticket:', error);
      setLoadError('Failed to load this ticket. Please try again.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicket();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tId]);

  // Load similar tickets once we know the current ticket's classification
  useEffect(() => {
    if (!ticket) return;

    let cancelled = false;
    const loadSimilar = async () => {
      try {
        setLoadingSimilar(true);
        const results = await ticketService.getSimilarTickets(ticket, 5);
        if (!cancelled) setSimilarTickets(results);
      } catch (error) {
        console.error('Failed to load similar tickets:', error);
        if (!cancelled) setSimilarTickets([]);
      } finally {
        if (!cancelled) setLoadingSimilar(false);
      }
    };

    loadSimilar();
    return () => { cancelled = true; };
  }, [ticket?.id, ticket?.issue_type, ticket?.ticket_category]);

  const handleUpdateTicket = async () => {
    if (!newStatus && !newWorkNote && !timeSpent) {
      setSaveMessage({ type: 'error', text: 'Select a new status, enter time spent, or add a work note before saving.' });
      return;
    }

    const targetId = ticket?.id || tId;
    setSaving(true);
    setSaveMessage(null);
    try {
      await ticketService.updateTicket(targetId, {
        status: newStatus || undefined,
        work_note: newWorkNote || undefined,
        time_spent: timeSpent || undefined
      });

      setSaveMessage({ type: 'success', text: 'Ticket updated and time spent saved successfully in Snowflake.' });
      setNewStatus('');
      setTimeSpent('');
      setNewWorkNote('');
      await fetchTicket();
    } catch (error) {
      console.error('Failed to update ticket:', error);
      setSaveMessage({ type: 'error', text: error.message || 'Failed to update ticket.' });
    } finally {
      setSaving(false);
    }
  };

  const handleSendEmail = async () => {
    const message = newWorkNote || `Update on your ticket ${ticket?.id}: status is now ${ticket?.status}.`;

    setEmailing(true);
    setEmailMessage(null);
    try {
      await ticketService.emailCustomer(tId, message);
      setEmailMessage({ type: 'success', text: 'Email sent to customer.' });
    } catch (error) {
      console.error('Failed to email customer:', error);
      setEmailMessage({ type: 'error', text: error.message || 'Failed to send email to customer.' });
    } finally {
      setEmailing(false);
    }
  };

  const handleAcceptResolution = async () => {
    setResolutionActionLoading(true);
    setResolutionMessage(null);
    try {
      await ticketService.addWorkNote(tId, 'Technician accepted the AI suggested resolution.');
      if (ticket?.status?.toLowerCase() === 'open' || ticket?.status?.toLowerCase() === 'new') {
        await ticketService.updateTicketStatus(tId, 'In Progress');
      }
      setResolutionMessage({ type: 'success', text: 'Resolution accepted.' });
      await fetchTicket();
    } catch (error) {
      console.error('Failed to accept resolution:', error);
      setResolutionMessage({ type: 'error', text: error.message || 'Failed to accept resolution.' });
    } finally {
      setResolutionActionLoading(false);
    }
  };

  const startEditingResolution = () => {
    setEditedResolutionText(ticket?.resolution || '');
    setEditingResolution(true);
    setResolutionMessage(null);
  };

  const handleSaveEditedResolution = async () => {
    if (!editedResolutionText.trim()) return;

    setResolutionActionLoading(true);
    setResolutionMessage(null);
    try {
      await ticketService.addWorkNote(tId, `Edited Resolution: ${editedResolutionText.trim()}`);
      setResolutionMessage({ type: 'success', text: 'Edited resolution saved.' });
      setEditingResolution(false);
      await fetchTicket();
    } catch (error) {
      console.error('Failed to save edited resolution:', error);
      setResolutionMessage({ type: 'error', text: error.message || 'Failed to save edited resolution.' });
    } finally {
      setResolutionActionLoading(false);
    }
  };

  const handleQuickStatus = async (status) => {
    setQuickAction(status);
    setQuickActionMessage(null);
    try {
      await ticketService.updateTicketStatus(tId, status);
      setQuickActionMessage({ type: 'success', text: `Ticket marked as ${status}.` });
      await fetchTicket();
    } catch (error) {
      console.error(`Failed to mark ticket as ${status}:`, error);
      setQuickActionMessage({ type: 'error', text: error.message || `Failed to mark ticket as ${status}.` });
    } finally {
      setQuickAction(null);
    }
  };

  const goToTicket = (ticketNumber) => {
    navigate(`/technician/my-tickets/view/${ticketNumber.replace('.', '-')}`);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
          <Header />
          <main className="p-6 md:p-8 flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4]" />
          </main>
        </div>
        <ChatButton />
      </div>
    );
  }

  if (loadError || !ticket) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
          <Header />
          <main className="p-6 md:p-8 flex-1">
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
              {loadError || 'Ticket not found.'}
              <button onClick={fetchTicket} className="ml-4 text-red-800 underline hover:no-underline">
                Try Again
              </button>
            </div>
          </main>
        </div>
        <ChatButton />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto space-y-6">

          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl mx-auto p-6">
            <div className="space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">
                    🎫 {ticket.id} - {ticket.title}
                  </h2>
                  <p className="text-gray-600">
                    {ticket.ticket_category || 'General'} • {ticket.ticket_type || 'Support'}
                  </p>
                </div>
              </div>

              {!isAssignedToMe && (
                <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-lg flex items-center gap-3 text-sm font-medium">
                  <Lock className="w-5 h-5 text-amber-600 flex-shrink-0" />
                  <div>
                    <strong className="font-semibold text-amber-950">Read-Only Access:</strong> You are not the assigned technician for this ticket ({ticket.assigned_technician || 'Unassigned'}). Modifying status, notes, and resolving is disabled.
                  </div>
                </div>
              )}

              {/* Lifecycle Quick Actions */}
              <div className="flex flex-wrap items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg p-3">
                <span className="text-xs font-medium text-gray-500 mr-1">Lifecycle:</span>
                <button
                  onClick={() => handleQuickStatus('In Progress')}
                  disabled={!isAssignedToMe || quickAction !== null}
                  className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {quickAction === 'In Progress' ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                  Mark In Progress
                </button>
                <button
                  onClick={() => handleQuickStatus('Resolved')}
                  disabled={!isAssignedToMe || quickAction !== null}
                  className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {quickAction === 'Resolved' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  Resolve
                </button>
                <button
                  onClick={() => handleQuickStatus('Closed')}
                  disabled={!isAssignedToMe || quickAction !== null}
                  className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {quickAction === 'Closed' ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                  Close
                </button>
                {quickActionMessage && (
                  <span className={`text-sm ${quickActionMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                    {quickActionMessage.text}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${statusColors[ticket.status?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                        {ticket.status || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${priorityColors[ticket.priority?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                        {ticket.priority?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                      <p className="text-sm">{ticket.requester_name || 'Unknown'}</p>
                      <p className="text-xs text-gray-500">{ticket.user_email || 'No email'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                      <p className="text-sm">{ticket.due_date || 'Not set'}</p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <p className="text-sm text-gray-600 p-3 bg-gray-50 rounded">
                      {ticket.description || 'No description provided'}
                    </p>
                  </div>

                  {/* AI Analysis */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                      <Sparkles className="w-4 h-4 text-[#00ABE4]" /> AI Analysis
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-gray-500 text-xs mb-1">
                          <Tag className="w-3 h-3" /> Category
                        </div>
                        <p className="text-sm font-medium text-gray-800">{ticket.ticket_category || 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-gray-500 text-xs mb-1">
                          <Layers className="w-3 h-3" /> Issue Type
                        </div>
                        <p className="text-sm font-medium text-gray-800">{ticket.issue_type || 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-gray-500 text-xs mb-1">Sub Issue Type</div>
                        <p className="text-sm font-medium text-gray-800">{ticket.sub_issue_type || 'N/A'}</p>
                      </div>
                    </div>
                  </div>

                  {/* AI Suggested Resolution */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                      🤖 AI Suggested Resolution
                    </label>
                    {editingResolution ? (
                      <div className="space-y-2">
                        <textarea
                          rows={5}
                          value={editedResolutionText}
                          onChange={(e) => setEditedResolutionText(e.target.value)}
                          className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={handleSaveEditedResolution}
                            disabled={resolutionActionLoading}
                            className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-[#00ABE4] text-white disabled:opacity-50"
                          >
                            {resolutionActionLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                            Save Edited Resolution
                          </button>
                          <button
                            onClick={() => setEditingResolution(false)}
                            disabled={resolutionActionLoading}
                            className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        {ticket.resolution ? (
                          <p className="text-sm text-gray-700 p-3 bg-purple-50 border border-purple-100 rounded whitespace-pre-line">
                            {ticket.resolution}
                          </p>
                        ) : (
                          <p className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
                            No AI resolution generated for this ticket yet.
                          </p>
                        )}
                        {ticket.resolution && (
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={handleAcceptResolution}
                              disabled={resolutionActionLoading}
                              className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50"
                            >
                              {resolutionActionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                              Accept Resolution
                            </button>
                            <button
                              onClick={startEditingResolution}
                              disabled={resolutionActionLoading}
                              className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                            >
                              <Pencil className="w-4 h-4" />
                              Edit Resolution
                            </button>
                          </div>
                        )}
                        {resolutionMessage && (
                          <p className={`text-sm mt-1 ${resolutionMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                            {resolutionMessage.text}
                          </p>
                        )}
                      </>
                    )}
                  </div>

                  {/* Similar Tickets */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                      <Link2 className="w-4 h-4 text-[#00ABE4]" /> Similar Tickets
                    </label>
                    {loadingSimilar ? (
                      <div className="flex items-center gap-2 text-sm text-gray-500 p-3">
                        <Loader2 className="w-4 h-4 animate-spin" /> Finding similar tickets...
                      </div>
                    ) : similarTickets.length === 0 ? (
                      <p className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
                        No similar tickets found.
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-56 overflow-y-auto">
                        {similarTickets.map((sim) => (
                          <button
                            key={sim.id}
                            onClick={() => goToTicket(sim.id)}
                            className="w-full text-left border border-gray-200 rounded-lg p-3 hover:shadow-sm hover:border-[#00ABE4] transition-shadow"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-gray-800">{sim.id} - {sim.title}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[sim.status?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                                {sim.status || 'Unknown'}
                              </span>
                            </div>
                            {sim.resolution && (
                              <p className="text-xs text-gray-500 line-clamp-2">{sim.resolution}</p>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Ticket Details</label>
                    <div className="space-y-3 max-h-60 overflow-y-auto">
                      <div className="border-l-2 border-blue-200 pl-4 pb-2">
                        <div className="text-xs text-gray-500">
                          Created: {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : 'Unknown'}
                        </div>
                        <p className="text-sm mt-1">Ticket created and assigned to technician</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column - Update Form */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Update Status</label>
                    <select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                      disabled={!isAssignedToMe}
                      className="w-full border border-gray-300 rounded-lg p-2 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    >
                      <option value="">Select new status</option>
                      <option value="Open">Open</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Resolved">Resolved</option>
                      <option value="Closed">Closed</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Time Spent</label>
                    <input
                      type="text"
                      placeholder="e.g. 30 mins"
                      value={timeSpent}
                      onChange={(e) => setTimeSpent(e.target.value)}
                      disabled={!isAssignedToMe}
                      className="w-full border border-gray-300 rounded-lg p-2 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Add Work Note</label>
                    <textarea
                      rows={4}
                      value={newWorkNote}
                      onChange={(e) => setNewWorkNote(e.target.value)}
                      disabled={!isAssignedToMe}
                      placeholder={!isAssignedToMe ? "Only assigned technician can add work notes." : "Add internal or customer update notes..."}
                      className="w-full border border-gray-300 rounded-lg p-2 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                  </div>

                  {saveMessage && (
                    <p className={`text-sm ${saveMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                      {saveMessage.text}
                    </p>
                  )}
                  {emailMessage && (
                    <p className={`text-sm ${emailMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                      {emailMessage.text}
                    </p>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={handleUpdateTicket}
                      disabled={!isAssignedToMe || saving}
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                      Save Update
                    </button>
                    <button
                      onClick={handleSendEmail}
                      disabled={!isAssignedToMe || emailing}
                      className="flex-1 border border-gray-300 py-2 px-4 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {emailing && <Loader2 className="w-4 h-4 animate-spin" />}
                      Email Customer
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </main>
      </div>
      <ChatButton />
    </div>
  )
}

export default ViewTicket
