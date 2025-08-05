import React from 'react'
import { useState ,useEffect } from 'react';
import { useParams } from 'react-router-dom';
import Sidebar from '../../components/Sidebar';
import Header from '../../components/Header';
import ChatButton from '../../components/ChatButton';

const mockFetchTicketById = async (id) => {
    // Replace with your real API or context logic
    return {
      id,
      title: 'Network Issue in Office',
      ticket_category: 'Networking',
      ticket_type: 'Issue',
      status: 'open',
      priority: 'high',
      requester_name: 'John Doe',
      user_email: 'john@example.com',
      due_date: '2025-08-10',
      created_at: '2025-08-01T10:00:00Z',
      description: 'Internet not working in the main office.',
      resolution: '',
    };
  };
  
  const statusColors = {
    open: 'bg-yellow-100 text-yellow-800',
    'in-progress': 'bg-blue-100 text-blue-800',
    resolved: 'bg-green-100 text-green-800',
  };
  
  const priorityColors = {
    low: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800',
  };
  

function ViewTicket() {

    const { ticketId } = useParams();

    const tId = ticketId.replace('-', '.');

   


  const [ticket, setTicket] = useState(null);
  const [newStatus, setNewStatus] = useState('');
  const [timeSpent, setTimeSpent] = useState('');
  const [newWorkNote, setNewWorkNote] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      const data = await mockFetchTicketById(tId);
      setTicket(data);
    };

    fetchData();
  }, [tId]);

  const handleUpdateTicket = () => {
    // handle ticket update logic
    console.log('Saving:', { newStatus, timeSpent, newWorkNote });
  };

  const handleSendEmail = () => {
    // handle email logic
    console.log('Sending email...');
  };

  if (!ticket) return <div className="p-6">Loading...</div>;
    


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
                  <label className="block text-sm font-medium text-gray-700 mb-2">Ticket Details</label>
                  <div className="space-y-3 max-h-60 overflow-y-auto">
                    <div className="border-l-2 border-blue-200 pl-4 pb-2">
                      <div className="text-xs text-gray-500">
                        Created: {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : 'Unknown'}
                      </div>
                      <p className="text-sm mt-1">Ticket created and assigned to technician</p>
                    </div>

                    {ticket.resolution ? (
                      <div className="border-l-2 border-green-200 pl-4 pb-2">
                        <div className="text-xs text-gray-500">Resolution</div>
                        <p className="text-sm mt-1">{ticket.resolution}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">No resolution notes yet</p>
                    )}
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
                    <option value="open">Open</option>
                    <option value="in-progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Time Spent</label>
                  <input
                    type="text"
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

                <div className="flex gap-2">
                  <button onClick={handleUpdateTicket} className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg">
                    Save Update
                  </button>
                  <button onClick={handleSendEmail} className="flex-1 border border-gray-300 py-2 px-4 rounded-lg">
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