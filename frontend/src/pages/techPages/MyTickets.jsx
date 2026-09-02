import React, { useState, useEffect } from "react";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import ChatButton from "../../components/ChatButton";
import { FiSearch, FiUser , FiChevronDown, FiFilter, FiEye, FiX } from "react-icons/fi";
import { IoTimeOutline } from "react-icons/io5";
import useAuth from "../../hooks/useAuth";
import { ticketService } from "../../services/ticketService";
import { Loader2 } from "lucide-react";
import { useNavigate, useSearchParams } from 'react-router-dom';
import { calculateTicketSla } from '../../components/MttrCard';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "all");
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get("priority") || "all");
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get("category") || "all");
  const [showFilters, setShowFilters] = useState(Boolean(searchParams.get("category") || searchParams.get("priority")));
  
  const navigate = useNavigate();

  // Synchronize state when URL query parameters change
  useEffect(() => {
    const cat = searchParams.get("category");
    if (cat) {
      setCategoryFilter(cat);
      setShowFilters(true);
    }
    const prio = searchParams.get("priority");
    if (prio) {
      setPriorityFilter(prio);
    }
  }, [searchParams]);

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
      const currentUserId = (user?.username || '').trim().toLowerCase();
      const currentUserEmail = (user?.email || '').trim().toLowerCase();
      const currentFullName = (user?.full_name || '').trim().toLowerCase();

      const myTickets = allTickets.filter(ticket => {
        const assignedTech = (ticket.assigned_technician || '').trim().toLowerCase();
        const technicianId = (ticket.technician_id || '').trim().toLowerCase();
        const technicianEmail = (ticket.technician_email || '').trim().toLowerCase();

        return (
          (currentUserId && (assignedTech === currentUserId || technicianId === currentUserId)) ||
          (currentUserEmail && (technicianEmail === currentUserEmail || assignedTech === currentUserEmail)) ||
          (currentFullName && (assignedTech === currentFullName || assignedTech.includes(currentFullName)))
        );
      });

      setTickets(myTickets);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      setError('Failed to load your tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const [, setTick] = useState(0);

  useEffect(() => {
    if (user?.username) {
      loadMyTickets();
    }
    const timer = setInterval(() => setTick(t => t + 1), 10000);
    return () => clearInterval(timer);
  }, [user]);

  // Dynamic unique categories
  const availableCategories = Array.from(
    new Set(tickets.map(t => t.category || t.ticket_category || t.issue_type).filter(Boolean))
  ).sort();

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch =
      ticket.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.requester_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ticket.user_email?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || ticket.status?.toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority = priorityFilter === "all" || ticket.priority?.toLowerCase() === priorityFilter.toLowerCase();
    
    // Dynamic Category match
    const ticketCat = (ticket.category || ticket.ticket_category || ticket.issue_type || '').toLowerCase();
    const filterCat = categoryFilter.toLowerCase();
    const matchesCategory = categoryFilter === "all" ||
      ticketCat === filterCat ||
      ticketCat.includes(filterCat) ||
      filterCat.includes(ticketCat);

    return matchesSearch && matchesStatus && matchesPriority && matchesCategory;
  });

  
  

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header onRefresh={loadMyTickets} isRefreshing={loading} />
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
                {/* <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium">
                  {tickets.filter(t => t.priority?.toLowerCase() === "critical").length} critical
                </span> */}
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
            <div className="bg-white w-full rounded-lg shadow-sm border border-gray-200 p-4">
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

              {/* Active Category Filter Alert Banner */}
              {categoryFilter !== "all" && (
                <div className="mt-3 flex items-center justify-between bg-blue-50 border border-blue-200 text-blue-800 px-3.5 py-2 rounded-lg text-xs font-semibold">
                  <div className="flex items-center gap-2">
                    <span>🏷️</span>
                    <span>Filtering by Category: <strong className="text-blue-900 font-bold">&ldquo;{categoryFilter}&rdquo;</strong></span>
                  </div>
                  <button
                    onClick={() => {
                      setCategoryFilter("all");
                      searchParams.delete("category");
                      setSearchParams(searchParams);
                    }}
                    className="flex items-center gap-1 bg-white hover:bg-blue-100 text-blue-700 px-2 py-0.5 rounded border border-blue-300 transition cursor-pointer"
                  >
                    <FiX className="w-3 h-3" />
                    <span>Clear</span>
                  </button>
                </div>
              )}

              {/* Expanded Filters */}
              {showFilters && (
                <div className="mt-4  grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                    <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                      <button
                        onClick={() => {
                          setCategoryFilter("all");
                          searchParams.delete("category");
                          setSearchParams(searchParams);
                        }}
                        className={`px-2.5 py-1 rounded-full text-xs font-medium ${categoryFilter === "all" ? "bg-blue-100 text-blue-800 border border-blue-300" : "bg-gray-100 text-gray-800"}`}
                      >
                        All
                      </button>
                      {availableCategories.map(cat => (
                        <button
                          key={cat}
                          onClick={() => {
                            setCategoryFilter(cat);
                            setSearchParams({ ...Object.fromEntries(searchParams.entries()), category: cat });
                          }}
                          className={`px-2.5 py-1 rounded-full text-xs font-medium truncate max-w-[140px] ${categoryFilter.toLowerCase() === cat.toLowerCase() ? "bg-blue-600 text-white shadow-sm" : "bg-gray-100 hover:bg-gray-200 text-gray-800"}`}
                          title={cat}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>

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
            <div className="w-full bg-white shadow-md rounded-lg">
              <div className="w-full">
                <table className="w-full table-fixed divide-y divide-gray-200">
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
                    ) : filteredTickets.map((ticket) => {
                      const sla = calculateTicketSla(ticket);

                      // Calculate Time Spent Display
                      let timeSpentDisplay = ticket.time_spent || ticket.TIME_SPENT;
                      if (!timeSpentDisplay) {
                        const text = `${ticket.resolution || ''} ${ticket.description || ''}`;
                        const match = text.match(/\((\d+(?:\.\d+)?\s*(?:mins?|minutes?|hrs?|hours?))\)/i);
                        if (match) {
                          timeSpentDisplay = match[1];
                        } else {
                          const isResolved = ['completed', 'resolved', 'closed'].includes((ticket.status || '').toLowerCase());
                          if (isResolved) {
                            timeSpentDisplay = sla?.durationHours ? `${sla.durationHours}h` : '1.2h';
                          } else {
                            const createdAt = ticket.created_at ? new Date(ticket.created_at) : null;
                            if (createdAt && !isNaN(createdAt.getTime())) {
                              const elapsedMins = Math.max(1, Math.round((Date.now() - createdAt.getTime()) / 60000));
                              if (elapsedMins < 60) {
                                timeSpentDisplay = `${elapsedMins}m`;
                              } else {
                                const elapsedH = (elapsedMins / 60).toFixed(1);
                                timeSpentDisplay = elapsedH < 24 ? `${elapsedH}h` : `${(elapsedMins / 1440).toFixed(1)}d`;
                              }
                            } else {
                              timeSpentDisplay = '30m';
                            }
                          }
                        }
                      }

                      return (
                        <tr key={ticket.id} className="hover:bg-gray-50">
                          <td className="px-2 sm:px-6 py-4 font-mono text-sm text-blue-900">{ticket.id}</td>
                          <td className="px-2 sm:px-6 py-4 font-medium">{ticket.title}</td>
                          <td className="px-2 sm:px-6 py-4">
                            <div className="flex items-center">
                              <FiUser className="h-4 w-4 text-gray-400 mr-1" />
                              {ticket.requester_name || ticket.user_email || 'Unknown'}
                            </div>
                          </td>
                          <td className="px-2 sm:px-6 py-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[ticket.status?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                              {ticket.status || 'Unknown'}
                            </span>
                          </td>
                          <td className="px-2 sm:px-6 py-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColors[ticket.priority?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
                              {ticket.priority?.toUpperCase() || 'UNKNOWN'}
                            </span>
                          </td>
                          <td className="px-2 sm:px-6 py-4">
                            {sla?.status === 'resolved' ? (
                              <span className="bg-blue-100 text-blue-800 px-2.5 py-1 rounded-full text-xs font-medium">
                                ✅ SLA Met
                              </span>
                            ) : sla?.status === 'breached' ? (
                              <span className="bg-red-100 text-red-800 px-2.5 py-1 rounded-full text-xs font-medium">
                                ⚠️ Breached
                              </span>
                            ) : sla?.status === 'approaching' ? (
                              <span className="bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full text-xs font-medium">
                                ⏳ Near SLA
                              </span>
                            ) : (
                              <span className="bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full text-xs font-medium">
                                🟢 On Track
                              </span>
                            )}
                          </td>
                          <td className="px-2 sm:px-6 py-4">
                            <div className="flex items-center font-medium text-gray-700">
                              <IoTimeOutline className="h-4 w-4 text-[#00ABE4] mr-1.5" />
                              <span>{timeSpentDisplay}</span>
                            </div>
                          </td>
                          <td className="px-2 sm:px-6 py-4">
                            <button
                              onClick={() => navigate(`/technician/my-tickets/view/${ticket.id.replace('.', '-')}`)}
                              className="flex items-center text-sm font-semibold text-blue-600 hover:text-blue-800"
                            >
                              <FiEye className="h-4 w-4 mr-1" />
                              View
                            </button>
                          </td>
                        </tr>
                      );
                    })}
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