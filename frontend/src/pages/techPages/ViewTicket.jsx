import React from 'react'
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';
import Header from '../../components/Header';
import ChatButton from '../../components/ChatButton';
import { ticketService } from '../../services/ticketService';
import { Loader2 } from 'lucide-react';

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

  const fetchTicket = async () => {
    try {
      setLoading(true);
      setLoadError('');
      const data = await ticketService.getTicketById(tId);
      setTicket(data);
    } catch (error) {
      console.error('Failed to load ticket:', error);
      setLoadError('Failed to load this ticket. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicket();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tId]);

  const handleUpdateTicket = async () => {
    if (!newStatus && !newWorkNote) {
      setSaveMessage({ type: 'error', text: 'Select a new status or add a work note before saving.' });
      return;
    }

    setSaving(true);
    setSaveMessage(null);
    try {
      if (newStatus) {
        await ticketService.updateTicketStatus(tId, newStatus);
      }
      if (newWorkNote) {
        const note = timeSpent ? `(${timeSpent}) ${newWorkNote}` : newWorkNote;
        await ticketService.addWorkNote(tId, note);
      }

      setSaveMessage({ type: 'success', text: 'Ticket updated successfully.' });
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

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                      🤖 AI Suggested Resolution
                    </label>
                    {ticket.resolution ? (
                      <p className="text-sm text-gray-700 p-3 bg-purple-50 border border-purple-100 rounded whitespace-pre-line">
                        {ticket.resolution}
                      </p>
                    ) : (
                      <p className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
                        No AI resolution generated for this ticket yet.
                      </p>
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
                      className="w-full border border-gray-300 rounded-lg p-2"
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
                      className="w-full border border-gray-300 rounded-lg p-2"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Add Work Note</label>
                    <textarea
                      rows={4}
                      value={newWorkNote}
                      onChange={(e) => setNewWorkNote(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg p-2"
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
                      disabled={saving}
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                      Save Update
                    </button>
                    <button
                      onClick={handleSendEmail}
                      disabled={emailing}
                      className="flex-1 border border-gray-300 py-2 px-4 rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
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
