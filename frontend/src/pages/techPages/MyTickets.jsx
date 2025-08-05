import React, { useState, useEffect } from "react";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import ChatButton from "../../components/ChatButton";
import { FiSearch, FiUser , FiChevronDown, FiFilter, FiEye } from "react-icons/fi";
import { IoTimeOutline } from "react-icons/io5";
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
  const [showFilters, setShowFilters] = useState(false);
  
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

  
  

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className=" p-6 md:p-8 flex-1 overflow-y-auto">
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
      
    </div>
  );
};

export default MyTickets;