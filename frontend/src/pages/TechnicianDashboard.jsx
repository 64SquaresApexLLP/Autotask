import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatButton from '../components/ChatButton';
import { Wrench, Clock, Loader2, CheckCircle, ArrowRight } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import { ticketService } from '../services/ticketService.js';
import { technicianService } from '../services/technicianService.js';
import { calculateTicketSla } from '../components/MttrCard';


const TechnicianDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState({
    myTickets: [],
    allTickets: [],
    statistics: null,
    technicians: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load dashboard data on component mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError('');

      const currentUserId = (user?.username || '').trim().toLowerCase();
      const currentUserEmail = (user?.email || '').trim().toLowerCase();

      // Load all tickets, statistics, and technicians
      const [allTickets, statistics, technicians] = await Promise.all([
        ticketService.getAllTickets(),
        ticketService.getTicketStatistics().catch(() => null),
        technicianService.getAllTechnicians().catch(() => [])
      ]);

      // Filter tickets assigned to current technician using real IDs
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

      setDashboardData({
        myTickets,
        allTickets,
        statistics,
        technicians
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Calculate statistics from ticket data
  const getStatistics = () => {
    const { myTickets, allTickets } = dashboardData;

    // Mutually exclusive buckets so that: myActive + myUrgent + myCompleted = myTotal
    const DONE_STATUSES = ['completed', 'resolved', 'closed'];
    const isCompleted = (t) => DONE_STATUSES.includes((t.status || '').toLowerCase());
    const isUrgentPriority = (t) => ['high', 'critical'].includes((t.priority || '').toLowerCase());

    return {
      myTotal: myTickets.length,
      // All open tickets (myActive + myUrgent) — used for the banner & workload gauge
      myOpen: myTickets.filter((t) => !isCompleted(t)).length,
      // Open AND NOT high/critical priority (does not double-count with Urgent)
      myActive: myTickets.filter((t) => !isCompleted(t) && !isUrgentPriority(t)).length,
      // Open AND high/critical priority
      myUrgent: myTickets.filter((t) => !isCompleted(t) && isUrgentPriority(t)).length,
      // Completed = resolved / completed / closed
      myCompleted: myTickets.filter(isCompleted).length,
      totalUnassigned: allTickets.filter(t => !t.assigned_technician).length,
      totalCritical: allTickets.filter(t => t.priority?.toLowerCase() === 'critical').length
    };
  };

  const stats = getStatistics();

  const [updatingTicketId, setUpdatingTicketId] = useState(null);

  const handleQuickStatusUpdate = async (e, ticketId, newStatus) => {
    e.stopPropagation();
    try {
      setUpdatingTicketId(ticketId);
      await ticketService.updateTicketStatus(ticketId, newStatus);
      setDashboardData(prev => ({
        ...prev,
        myTickets: prev.myTickets.map(t => t.id === ticketId ? { ...t, status: newStatus } : t),
        allTickets: prev.allTickets.map(t => t.id === ticketId ? { ...t, status: newStatus } : t)
      }));
    } catch (err) {
      console.error('Quick update error:', err);
    } finally {
      setUpdatingTicketId(null);
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen ">
        <Header onRefresh={loadDashboardData} isRefreshing={loading} />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto ">
          <div className="max-w-7xl mx-auto space-y-6">
            

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Welcome Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#00ABE4] flex items-center justify-center text-2xl shadow-xs border border-blue-100 flex-shrink-0">
                  🔧
                </div>
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800">Welcome back, {user?.full_name || user?.username}!</h1>
                  <p className="text-gray-600 text-sm mt-0.5">Here's your current workload and active dispatch queue</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#00ABE4] border border-blue-200">
                  <CheckCircle className="w-3.5 h-3.5 text-[#00ABE4]" />
                  <span>{stats.myOpen} Active Tickets Assigned</span>
                </span>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 lg:gap-6">
              {/* Total Assigned Tickets */}
              <div
                onClick={() => navigate('/technician/my-tickets')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 hover:border-indigo-300 hover:shadow-md p-4 lg:p-6 transition-all cursor-pointer group"
                title="Click to view all your assigned tickets"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">📊</div>
                  <ArrowRight className="w-4 h-4 text-indigo-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1 group-hover:text-indigo-600 transition-colors">Total Tickets</h3>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myTotal}
                </div>
                <p className="text-sm text-gray-600">All tickets assigned to you &rarr;</p>
              </div>

              {/* My Active Tickets */}
              <div
                onClick={() => navigate('/technician/my-tickets')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 hover:border-blue-300 hover:shadow-md p-4 lg:p-6 transition-all cursor-pointer group"
                title="Click to view your active assigned tickets"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl"></div>
                  <ArrowRight className="w-4 h-4 text-blue-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1 group-hover:text-blue-600 transition-colors">My Active Tickets</h3>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myActive}
                </div>
                <p className="text-sm text-gray-600">Open, normal priority &rarr;</p>
              </div>

              {/* Urgent Tickets */}
              <div
                onClick={() => navigate('/technician/my-tickets')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 hover:border-red-300 hover:shadow-md p-4 lg:p-6 transition-all cursor-pointer group"
                title="Click to view critical & high priority tickets"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">🚨</div>
                  <div className="flex items-center gap-1.5">
                    {stats.myUrgent > 0 && (
                      <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">
                        {stats.myUrgent}
                      </span>
                    )}
                    <ArrowRight className="w-4 h-4 text-red-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1 group-hover:text-red-600 transition-colors">Urgent Tickets</h3>
                <div className="text-3xl font-bold text-red-600 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myUrgent}
                </div>
                <p className="text-sm text-red-600">
                  {stats.myUrgent > 0 ? 'Requires immediate attention →' : 'No urgent tickets →'}
                </p>
              </div>

              {/* Completed Today */}
              <div
                onClick={() => navigate('/technician/my-tickets')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 hover:border-green-300 hover:shadow-md p-4 lg:p-6 transition-all cursor-pointer group"
                title="Click to view all resolved tickets"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl"></div>
                  <ArrowRight className="w-4 h-4 text-green-400 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1 group-hover:text-green-600 transition-colors">Completed</h3>
                <div className="text-3xl font-bold text-green-600 mb-2">
                  {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : stats.myCompleted}
                </div>
                <p className="text-sm text-green-600">View resolution queue &rarr;</p>
              </div>

              
            </div>



            {/* Recent Assignments */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
              <div className="flex items-center space-x-2 mb-6">
                <Clock className="w-5 h-5 text-blue-500" />
                <h2 className="text-xl font-semibold text-gray-800">My Recent Tickets</h2>
              </div>
              <p className="text-gray-600 mb-6">Latest tickets assigned to you</p>

              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4] mx-auto mb-4" />
                  <p className="text-gray-600">Loading your tickets...</p>
                </div>
              ) : dashboardData.myTickets.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                  <p className="text-gray-600 text-lg mb-2">No tickets assigned</p>
                  <p className="text-gray-500">You're all caught up! Great work!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {dashboardData.myTickets.slice(0, 3).map((ticket) => {
                    const priorityColor = ticket.priority?.toLowerCase() === 'critical' ? 'red' :
                      ticket.priority?.toLowerCase() === 'high' ? 'orange' :
                        ticket.priority?.toLowerCase() === 'medium' ? 'yellow' : 'green';

                    const borderClass = priorityColor === 'red' ? 'border-red-200 bg-red-50' :
                      priorityColor === 'orange' ? 'border-orange-200 bg-orange-50' :
                        priorityColor === 'yellow' ? 'border-yellow-200 bg-yellow-50' : 'border-green-200 bg-green-50';
                    const dotClass = priorityColor === 'red' ? 'bg-red-500' :
                      priorityColor === 'orange' ? 'bg-orange-500' :
                        priorityColor === 'yellow' ? 'bg-yellow-500' : 'bg-green-500';
                    const textClass = priorityColor === 'red' ? 'text-red-600' :
                      priorityColor === 'orange' ? 'text-orange-600' :
                        priorityColor === 'yellow' ? 'text-yellow-600' : 'text-green-600';

                    const sla = calculateTicketSla(ticket);
                    const slaBadgeClass = sla.color === 'red'
                      ? 'bg-red-100 text-red-700 border-red-200'
                      : sla.color === 'amber'
                        ? 'bg-amber-100 text-amber-700 border-amber-200'
                        : sla.color === 'blue'
                          ? 'bg-blue-100 text-blue-700 border-blue-200'
                          : 'bg-emerald-100 text-emerald-700 border-emerald-200';

                    return (
                      <div key={ticket.id} className={`flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border rounded-lg ${borderClass}`}>
                        <div className="flex items-start space-x-3 mb-3 sm:mb-0">
                          <div className={`w-3 h-3 rounded-full mt-1 ${dotClass}`}></div>
                          <div>
                            <div className="font-semibold text-gray-800 flex flex-wrap items-center gap-2">
                              <span>{ticket.title}</span>
                              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${slaBadgeClass}`}>
                                {sla.text}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600 mt-1">
                              #{ticket.id} • {ticket.requester_name || ticket.user_email || 'Unknown'} •
                              {new Date(ticket.created_at || Date.now()).toLocaleDateString()}
                            </div>
                            <div className="text-xs text-gray-500 mt-1 flex flex-wrap items-center gap-2">
                              <span>Priority: {ticket.priority || 'Medium'} • Status: {ticket.status || 'Open'}</span>
                              {ticket.time_spent && (
                                <span className="font-semibold text-[#00ABE4] bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                                  Logged: {ticket.time_spent}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col sm:items-end space-y-2 mt-3 sm:mt-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-bold uppercase tracking-wider ${textClass}`}>
                              {ticket.priority || 'Medium'} Priority
                            </span>
                          </div>

                          {/* Quick Action Button Strip */}
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {['open', 'assigned'].includes((ticket.status || '').toLowerCase()) && (
                              <button
                                onClick={(e) => handleQuickStatusUpdate(e, ticket.id, 'In Progress')}
                                disabled={updatingTicketId === ticket.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm transition-all disabled:opacity-50"
                                title="Move to In Progress"
                              >
                                {updatingTicketId === ticket.id ? <Loader2 className="w-3 h-3 animate-spin" /> : '▶ Start Work'}
                              </button>
                            )}

                            {'in progress' === ticket.status?.toLowerCase() && ticket.time_spent && (
                              <button
                                onClick={(e) => handleQuickStatusUpdate(e, ticket.id, 'Resolved')}
                                disabled={updatingTicketId === ticket.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm transition-all disabled:opacity-50"
                                title="Mark as Resolved"
                              >
                                {updatingTicketId === ticket.id ? <Loader2 className="w-3 h-3 animate-spin" /> : '✓ Resolve'}
                              </button>
                            )}

                            
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {dashboardData.myTickets.length > 3 && (
                    <div className="text-center pt-4">
                      <button
                        onClick={() => window.location.href = '/technician/my-tickets'}
                        className="text-[#00ABE4] hover:text-blue-600 font-medium"
                      >
                        View all {dashboardData.myTickets.length} tickets →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>


          
          </div>
        </main>
      </div>
      <ChatButton />

      
    </div>
  );
};

export default TechnicianDashboard;