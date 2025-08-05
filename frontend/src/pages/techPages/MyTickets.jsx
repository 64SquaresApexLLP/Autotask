import React, { useState, useEffect } from "react";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import ChatButton from "../../components/ChatButton";
import { FiSearch, FiUser , FiChevronDown, FiFilter, FiEye } from "react-icons/fi";
import { IoReload, IoTimeOutline } from "react-icons/io5";
import useAuth from "../../hooks/useAuth";
import { ticketService } from "../../services/ticketService";
import { Loader2 } from "lucide-react";
import { useNavigate } from 'react-router-dom';



const statusColors = {
  open: "bg-blue-100 text-blue-800",
  new: "bg-blue-100 text-blue-800",
  "in-progress": "bg-yellow-100 text-yellow-800",
  "in progress": "bg-yellow-100 text-yellow-800",
  assigned: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
  completed: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-800",
};

const priorityColors = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const MyTickets = () => {
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [newWorkNote, setNewWorkNote] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [timeSpent, setTimeSpent] = useState("");


  const navigate = useNavigate();

  // Real data state
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Load tickets assigned to current technician
  const loadMyTickets = async () => {
    try {
      setLoading(true);
      setError("");

      // Get all tickets and filter for current technician
      const allTickets = await ticketService.getAllTickets({ limit: 100 });
      const myTickets = allTickets.filter(ticket => {
        const assignedTech = ticket.assigned_technician;
        const technicianId = ticket.technician_id;
        const currentUserId = user?.username; 

        return assignedTech === currentUserId || technicianId === currentUserId;
      });

      setTickets(myTickets);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      setError('Failed to load your tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.username) {
      loadMyTickets();
    }
  }, [user]);

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch =
      ticket.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.requester_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.user_email?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || ticket.status?.toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority = priorityFilter === "all" || ticket.priority?.toLowerCase() === priorityFilter.toLowerCase();

    return matchesSearch && matchesStatus && matchesPriority;
  });

  const handleUpdateTicket = () => {
    if (!selectedTicket) return;
    alert(`Ticket ${selectedTicket.id} updated successfully!`);
    setSelectedTicket(null);
    setNewWorkNote("");
    setNewStatus("");
    setTimeSpent("");
  };

  const handleSendEmail = () => {
    if (!selectedTicket) return;
    const customerName = selectedTicket.requester_name || 'Customer';
    const customerEmail = selectedTicket.user_email || 'No email available';
    alert(`Email sent to ${customerName} at ${customerEmail}`);
  };

  const getSLAStatus = (deadline) => {
    const now = new Date();
    const slaDate = new Date(deadline);
    const hoursRemaining = (slaDate.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (hoursRemaining < 0) {
      return <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">⚠️ Overdue</span>;
    } else if (hoursRemaining < 2) {
      return <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded-full text-xs font-medium">⏰ Due Soon</span>;
    } else {
      return <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs font-medium">✅ On Track</span>;
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Header Section */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-800">🎟️ My Tickets</h1>
                <p className="text-gray-600">Tickets assigned to you, sorted and searchable</p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="border border-gray-300 px-3 py-1 rounded-full text-sm font-medium">
                  {filteredTickets.length} tickets
                </span>
                <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium">
                  {tickets.filter(t => t.priority?.toLowerCase() === "critical").length} critical
                </span>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6">
                {error}
                <button
                  onClick={loadMyTickets}
                  className="ml-4 text-red-800 underline hover:no-underline"
                >
                  Try Again
                </button>
              </div>
            )}

            {/* Search and Filters */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                  <FiSearch className="absolute left-3 top-3 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by ticket, title, or customer..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg py-2 px-4 pl-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button 
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center justify-center gap-2 border border-gray-300 rounded-lg py-2 px-4 hover:bg-gray-50"
                >
                  <FiFilter className="text-gray-500" />
                  <span>Filters</span>
                  <FiChevronDown className={`transition-transform ${showFilters ? "rotate-180" : ""}`} />
                </button>
              </div>

              {/* Expanded Filters */}
              {showFilters && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setStatusFilter("all")}
                        className={`px-3 py-1 rounded-full text-sm ${statusFilter === "all" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        All
                      </button>
                      <button
                        onClick={() => setStatusFilter("open")}
                        className={`px-3 py-1 rounded-full text-sm ${statusFilter === "open" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        Open
                      </button>
                      <button
                        onClick={() => setStatusFilter("in-progress")}
                        className={`px-3 py-1 rounded-full text-sm ${statusFilter === "in-progress" ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        In Progress
                      </button>
                      <button
                        onClick={() => setStatusFilter("resolved")}
                        className={`px-3 py-1 rounded-full text-sm ${statusFilter === "resolved" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        Resolved
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setPriorityFilter("all")}
                        className={`px-3 py-1 rounded-full text-sm ${priorityFilter === "all" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        All
                      </button>
                      <button
                        onClick={() => setPriorityFilter("low")}
                        className={`px-3 py-1 rounded-full text-sm ${priorityFilter === "low" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        Low
                      </button>
                      <button
                        onClick={() => setPriorityFilter("medium")}
                        className={`px-3 py-1 rounded-full text-sm ${priorityFilter === "medium" ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        Medium
                      </button>
                      <button
                        onClick={() => setPriorityFilter("high")}
                        className={`px-3 py-1 rounded-full text-sm ${priorityFilter === "high" ? "bg-orange-100 text-orange-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        High
                      </button>
                      <button
                        onClick={() => setPriorityFilter("critical")}
                        className={`px-3 py-1 rounded-full text-sm ${priorityFilter === "critical" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-800"}`}
                      >
                        Critical
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Tickets Table */}
            <div className="bg-white shadow-md rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticket #</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SLA Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time Spent</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {loading ? (
                      <tr>
                        <td colSpan="7" className="px-6 py-8 text-center">
                          <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                          <p className="text-gray-600">Loading your tickets...</p>
                        </td>
                      </tr>
                    ) : filteredTickets.map((ticket) => (
                      <tr key={ticket.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-blue-900">{ticket.id}</td>
                        <td className="px-6 py-4 whitespace-nowrap font-medium">{ticket.title}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <FiUser className="h-4 w-4 text-gray-400 mr-1" />
                            {ticket.requester_name || ticket.user_email || 'Unknown'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[ticket.status?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                            {ticket.status || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColors[ticket.priority?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                            {ticket.priority?.toUpperCase() || 'UNKNOWN'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                            ✅ On Track
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <IoTimeOutline className="h-4 w-4 text-gray-400 mr-1" />
                            <span className="text-gray-500">-</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => navigate(`/technician/my-tickets/view/${ticket.id.replace('.', '-')}`)}
        
                            className="flex items-center text-sm text-blue-600 hover:text-blue-800"
                          >
                            
                            <FiEye className="h-4 w-4 mr-1" />
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredTickets.length === 0 && (
                  <div className="p-6 text-center text-gray-500">No tickets found matching your criteria.</div>
                )}
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
                    🎫 {selectedTicket.id} - {selectedTicket.title}
                  </h2>
                  <p className="text-gray-600">{selectedTicket.ticket_category || 'General'} • {selectedTicket.ticket_type || 'Support'}</p>
                </div>
                <button 
                  onClick={() => setSelectedTicket(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column - Ticket Details */}
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${statusColors[selectedTicket.status?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                        {selectedTicket.status || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${priorityColors[selectedTicket.priority?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                        {selectedTicket.priority?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Customer</label>
                      <p className="text-sm">{selectedTicket.requester_name || 'Unknown'}</p>
                      <p className="text-xs text-gray-500">{selectedTicket.user_email || 'No email'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                      <p className="text-sm">{selectedTicket.due_date || 'Not set'}</p>
                      <div className="mt-1">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                          ✅ On Track
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <p className="text-sm text-gray-600 p-3 bg-gray-50 rounded">
                      {selectedTicket.description || 'No description provided'}
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Ticket Details</label>
                    <div className="space-y-3 max-h-60 overflow-y-auto">
                      <div className="border-l-2 border-blue-200 pl-4 pb-2">
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>Created: {selectedTicket.created_at ? new Date(selectedTicket.created_at).toLocaleDateString() : 'Unknown'}</span>
                        </div>
                        <p className="text-sm mt-1">Ticket created and assigned to technician</p>
                      </div>

                      {selectedTicket.resolution && (
                        <div className="border-l-2 border-green-200 pl-4 pb-2">
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            <span>Resolution</span>
                          </div>
                          <p className="text-sm mt-1">{selectedTicket.resolution}</p>
                        </div>
                      )}

                      {!selectedTicket.resolution && (
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
                      className="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                      <option value="">Select new status</option>
                      <option value="open">Open</option>
                      <option value="in-progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Time Spent (this session)</label>
                    <input
                      type="text"
                      placeholder="e.g., 30 minutes, 1.5 hours"
                      value={timeSpent}
                      onChange={(e) => setTimeSpent(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Add Work Note</label>
                    <textarea
                      placeholder="Describe the work performed, findings, or next steps..."
                      rows={4}
                      value={newWorkNote}
                      onChange={(e) => setNewWorkNote(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={handleUpdateTicket}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-medium flex items-center justify-center"
                    >
                      Save Update
                    </button>
                    <button
                      onClick={handleSendEmail}
                      className="flex-1 border border-gray-300 hover:bg-gray-50 py-2 px-4 rounded-lg font-medium flex items-center justify-center"
                    >
                      Email Customer
                    </button>
                  </div>

                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">📧 Email Templates</h4>
                    <div className="space-y-2">
                      <button className="w-full text-left text-xs border border-blue-200 bg-white hover:bg-blue-100 p-2 rounded">
                        "Working on your issue..."
                      </button>
                      <button className="w-full text-left text-xs border border-blue-200 bg-white hover:bg-blue-100 p-2 rounded">
                        "Need additional information..."
                      </button>
                      <button className="w-full text-left text-xs border border-blue-200 bg-white hover:bg-blue-100 p-2 rounded">
                        "Issue resolved, please test..."
                      </button>
                    </div>
                  </div>

                  <div className="p-4 bg-green-50 rounded-lg">
                    <h4 className="font-medium text-green-900 mb-2">✅ Quick Actions</h4>
                    <div className="space-y-2">
                      <button className="w-full text-left text-xs border border-green-200 bg-white hover:bg-green-100 p-2 rounded">
                        Mark as Resolved
                      </button>
                      <button className="w-full text-left text-xs border border-green-200 bg-white hover:bg-green-100 p-2 rounded">
                        Escalate to Senior Tech
                      </button>
                      <button className="w-full text-left text-xs border border-green-200 bg-white hover:bg-green-100 p-2 rounded">
                        Schedule Follow-up
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyTickets;