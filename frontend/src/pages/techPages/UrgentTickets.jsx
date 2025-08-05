import React, { useState, useEffect } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import { AlertTriangle, User, Phone, Mail, Zap, Loader2, RefreshCw } from 'lucide-react';
import useAuth from '../../hooks/useAuth';
import { ticketService } from '../../services/ticketService';
import { technicianService } from '../../services/technicianService';

const UrgentTickets = () => {
  const { user } = useAuth();
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  // Real data state
  const [urgentTickets, setUrgentTickets] = useState([]);
  const [availableTechnicians, setAvailableTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load urgent tickets (Critical and High priority)
  const loadUrgentTickets = async () => {
    try {
      setLoading(true);
      setError('');

      // Get all tickets and filter for urgent ones
      const allTickets = await ticketService.getAllTickets({ limit: 100 });
      const urgent = allTickets.filter(ticket => {
        // Handle both uppercase and lowercase priority fields
        const priority = (ticket.PRIORITY || ticket.priority)?.toLowerCase();
        return priority === 'critical' || priority === 'high';
      });

      setUrgentTickets(urgent);
    } catch (error) {
      console.error('Failed to load urgent tickets:', error);
      setError('Failed to load urgent tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Load available technicians
  const loadTechnicians = async () => {
    try {
      const technicians = await technicianService.getAllTechnicians();

      // Use the workload data directly from the API (no need to calculate manually)
      const techsWithLoad = technicians.map(tech => {
        // Parse workload as integer to handle decimal values from Snowflake
        const workload = parseInt(tech.current_workload) || 0;

        return {
          id: tech.id,  // Use 'id' field from API response
          name: tech.name,
          email: tech.email,
          role: tech.role,
          skills: tech.specializations ? tech.specializations.split(',').map(s => s.trim()) : ['General Support'],
          status: workload < 5 ? 'available' : 'busy',  // Use parsed workload
          currentLoad: workload  // Use parsed workload as integer
        };
      });

      setAvailableTechnicians(techsWithLoad);
    } catch (error) {
      console.error('Failed to load technicians:', error);
      // Fallback to basic data if API fails
      setAvailableTechnicians([
        { id: "T001", name: "John Doe", skills: ["General Support"], status: "available", currentLoad: 0 },
        { id: "T103", name: "Vidhi Dave", skills: ["IT Support"], status: "available", currentLoad: 0 },
        { id: "T104", name: "Rohan Kulkarni", skills: ["Network Admin"], status: "available", currentLoad: 0 },
        { id: "T106", name: "Madhavi Ghalme", skills: ["Cybersecurity"], status: "available", currentLoad: 0 },
      ]);
    }
  };

  useEffect(() => {
    loadUrgentTickets();
    loadTechnicians();
  }, []);

  const handleTakeTicket = async (ticket) => {
    try {
      // Use the correct field name for ticket number
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;

      // Assign ticket to current user
      await ticketService.assignTicket(ticketNumber, user.username);

      setToastMessage({
        title: "Ticket Assigned! 🚨",
        description: `Urgent ticket ${ticketNumber} has been assigned to you. Customer notified.`,
      });

      // Reload tickets to reflect changes
      loadUrgentTickets();
      loadTechnicians();
    } catch (error) {
      console.error('Failed to assign ticket:', error);
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;
      setToastMessage({
        title: "Assignment Failed ❌",
        description: `Failed to assign ticket ${ticketNumber}. Please try again.`,
      });
    }
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleEscalate = async (ticket) => {
    try {
      // Use the correct field name for ticket number
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;

      // Update ticket status to escalated
      await ticketService.updateTicketStatus(ticketNumber, 'Escalated');

      setToastMessage({
        title: "Ticket Escalated! ⬆️",
        description: `Ticket ${ticketNumber} has been escalated to senior technician. Management notified.`,
      });

      // Reload tickets to reflect changes
      loadUrgentTickets();
    } catch (error) {
      console.error('Failed to escalate ticket:', error);
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;
      setToastMessage({
        title: "Escalation Failed ❌",
        description: `Failed to escalate ticket ${ticketNumber}. Please try again.`,
      });
    }
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleAssignTicket = async (technicianId, ticket) => {
    try {
      // Use the correct field name for ticket number
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;

      await ticketService.assignTicket(ticketNumber, technicianId);

      setToastMessage({
        title: "Ticket Assigned! 🎯",
        description: `Ticket ${ticketNumber} has been assigned to ${technicianId}. Customer notified.`,
      });

      // Reload data to reflect changes
      loadUrgentTickets();
      loadTechnicians();
    } catch (error) {
      console.error('Failed to assign ticket:', error);
      const ticketNumber = ticket.TICKETNUMBER || ticket.ticketnumber || ticket.id;
      setToastMessage({
        title: "Assignment Failed ❌",
        description: `Failed to assign ticket ${ticketNumber} to ${technicianId}. Please try again.`,
      });
    }
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleEmergencyContact = (phone) => {
    setToastMessage({
      title: "Emergency Contact Initiated! 📞",
      description: `Calling ${phone} for immediate assistance.`,
    });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case "critical":
        return "bg-red-500 text-white";
      case "high":
        return "bg-orange-500 text-white";
      default:
        return "bg-gray-500 text-white";
    }
  };

  

  // Helper function to calculate ticket age
  const getTicketAge = (createdAt) => {
    if (!createdAt) return 'Unknown';
    const now = new Date();
    const created = new Date(createdAt);
    const diffHours = Math.floor((now - created) / (1000 * 60 * 60));

    if (diffHours < 1) return 'Less than 1 hour';
    if (diffHours === 1) return '1 hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className=" p-6 md:p-8 flex-1 overflow-y-auto ">
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Toast Notification */}
            {toastMessage && (
              <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg animate-fade-in">
                <div className="font-bold">{toastMessage.title}</div>
                <div>{toastMessage.description}</div>
              </div>
            )}

            {/* Header Section */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-red-600">🚨 Urgent Tickets</h1>
                <p className="text-gray-600">Critical and high-priority tickets requiring immediate attention</p>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={loadUrgentTickets}
                  className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 transition-colors"
                  disabled={loading}
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  <span className="text-sm">Refresh</span>
                </button>
                <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                  {urgentTickets.length} URGENT
                </span>
                <span className="border border-gray-300 px-3 py-1 rounded-full text-sm font-medium">
                  0 OVERDUE
                </span>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
                {error}
                <button
                  onClick={loadUrgentTickets}
                  className="ml-4 text-red-800 underline hover:no-underline"
                >
                  Try Again
                </button>
              </div>
            )}

            {/* Alert Banner */}
            {urgentTickets.length > 0 && (
              <div className="border border-red-200 bg-red-50 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-6 w-6 text-red-600 animate-pulse" />
                  <div>
                    <p className="font-semibold text-red-800">
                      {urgentTickets.length === 1 ? 'Critical Alert: Urgent ticket requires immediate attention' : 'Critical Alert: Multiple urgent tickets require immediate attention'}
                    </p>
                    <p className="text-sm text-red-700">
                      {urgentTickets.length} urgent {urgentTickets.length === 1 ? 'ticket' : 'tickets'} found. Please review and assign immediately.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Urgent Tickets Grid */}
            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="w-12 h-12 animate-spin text-[#00ABE4] mx-auto mb-4" />
                <p className="text-gray-600">Loading urgent tickets...</p>
              </div>
            ) : urgentTickets.length === 0 ? (
              <div className="text-center py-12">
                <AlertTriangle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-800 mb-2">No Urgent Tickets! 🎉</h3>
                <p className="text-gray-600">All tickets are under control. Great work!</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {urgentTickets.map((ticket) => (
                  <div
                    key={ticket.id}
                    className={`border-2 rounded-lg p-4 ${ticket.priority?.toLowerCase() === "critical" ? "border-red-300 bg-red-50" : "border-orange-300 bg-orange-50"}`}
                  >
                    <div className="pb-3">
                      <div className="flex items-center justify-between mb-3">
                        <span className={`${getPriorityColor(ticket.priority)} px-3 py-1 rounded-full text-xs font-medium`}>
                          {ticket.priority?.toLowerCase() === "critical" ? "🔴 CRITICAL" : "⚠️ HIGH"}
                        </span>
                        <div className="text-right">
                          <p className="text-xs text-gray-500">Status</p>
                          <p className="text-sm font-mono text-blue-600">
                            {ticket.status || 'Open'}
                          </p>
                        </div>
                      </div>
                      <h2 className="text-lg font-bold">{ticket.title}</h2>
                      <p className="text-sm text-gray-500">
                        {ticket.id} • {ticket.ticket_category || 'General'}
                      </p>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-medium mb-1">Description:</p>
                        <p className="text-sm text-gray-600">{ticket.description || 'No description provided'}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <p className="font-medium">Customer:</p>
                          <p className="text-gray-600">{ticket.requester_name || ticket.user_email || 'Unknown'}</p>
                        </div>
                        <div>
                          <p className="font-medium">Created:</p>
                          <p className="text-gray-600">
                            {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : 'Unknown'}
                          </p>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Priority Level</span>
                          <span className="font-semibold">{ticket.priority?.toUpperCase() || 'UNKNOWN'}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${ticket.priority?.toLowerCase() === "critical" ? "bg-red-500" : "bg-orange-500"}`}
                            style={{ width: `${ticket.priority?.toLowerCase() === "critical" ? "100" : "75"}%` }}
                          ></div>
                        </div>
                      </div>

                    <div className="flex gap-2">
                      <button
                        className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center justify-center"
                        onClick={() => handleTakeTicket(ticket)}
                      >
                        <Zap className="h-4 w-4 mr-1" />
                        Take Ticket
                      </button>
                      <button
                        className="border border-gray-300 hover:bg-gray-100 px-4 py-2 rounded-lg text-sm font-medium"
                        onClick={() => handleEscalate(ticket)}
                      >
                        ⬆️ Escalate
                      </button>
                    </div>

                    <div className="flex gap-2">
                      <button
                        className="flex-1 border border-gray-300 hover:bg-gray-100 px-4 py-2 rounded-lg text-sm font-medium flex items-center justify-center"
                        onClick={() => handleEmergencyContact(ticket.customerPhone)}
                      >
                        <Phone className="h-4 w-4 mr-1" />
                        Call
                      </button>
                      <button className="flex-1 border border-gray-300 hover:bg-gray-100 px-4 py-2 rounded-lg text-sm font-medium flex items-center justify-center">
                        <Mail className="h-4 w-4 mr-1" />
                        Email
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              </div>
            )}

            {/* Team Availability */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                <User className="h-5 w-5" />
                <h2 className="text-xl font-semibold">Team Availability for Urgent Assignments</h2>
              </div>
              <p className="text-gray-600 mb-4">Current technician availability and skill matching</p>

              {/* Show which ticket will be assigned */}
              {urgentTickets.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                    <span className="font-medium text-blue-800">Next Ticket to Assign:</span>
                  </div>
                  <div className="text-sm text-blue-700">
                    <strong>{urgentTickets[0].TICKETNUMBER || urgentTickets[0].ticketnumber}</strong> - {urgentTickets[0].TITLE || urgentTickets[0].title}
                  </div>
                  <div className="text-xs text-blue-600 mt-1">
                    Priority: {urgentTickets[0].PRIORITY || urgentTickets[0].priority} |
                    Customer: {urgentTickets[0].REQUESTER_NAME || urgentTickets[0].requester_name || 'Unknown'}
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {availableTechnicians.map((tech, index) => (
                  <div
                    key={index}
                    className={`p-4 border rounded-lg ${tech.status === "available" ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200"}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium">{tech.name}</p>
                      <div
                        className={`w-3 h-3 rounded-full ${tech.status === "available" ? "bg-green-500" : "bg-yellow-500"}`}
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex gap-1 flex-wrap">
                        {tech.skills.map((skill) => (
                          <span key={skill} className="border border-gray-300 px-2 py-1 rounded-full text-xs">
                            {skill}
                          </span>
                        ))}
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Current Load:</span>
                        <span>{tech.currentLoad} tickets</span>
                      </div>
                      {urgentTickets.length > 0 && urgentTickets[0] && (
                        <button
                          className={`w-full px-4 py-2 rounded-lg text-sm font-medium ${tech.status === "available" ? "bg-blue-600 hover:bg-blue-700 text-white" : "border border-gray-300 text-gray-500 cursor-not-allowed"}`}
                          disabled={tech.status !== "available"}
                          onClick={() => tech.status === "available" && handleAssignTicket(tech.id, urgentTickets[0])}
                          title={tech.status === "available" ? `Assign ${urgentTickets[0].TICKETNUMBER || urgentTickets[0].ticketnumber || 'urgent ticket'} to ${tech.name}` : "Technician is busy"}
                        >
                          {tech.status === "available" ?
                            `Assign ${urgentTickets[0].TICKETNUMBER || urgentTickets[0].ticketnumber || 'Ticket'}` :
                            "Busy"
                          }
                        </button>
                      )}
                      {urgentTickets.length === 0 && (
                        <button
                          className="w-full px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-500 cursor-not-allowed"
                          disabled={true}
                        >
                          No Urgent Tickets
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Emergency Procedures */}
            <div className="border border-orange-200 bg-orange-50 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-5 w-5 text-orange-800" />
                <h2 className="text-xl font-semibold text-orange-800">Emergency Escalation Procedures</h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold text-orange-900 mb-2">📞 Emergency Contacts</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>IT Manager:</span>
                      <span className="font-mono">+1 (555) 123-4567</span>
                    </div>
                    <div className="flex justify-between">
                      <span>On-Call Senior Tech:</span>
                      <span className="font-mono">+1 (555) 987-6543</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Emergency Hotline:</span>
                      <span className="font-mono">+1 (555) 911-HELP</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-orange-900 mb-2">⚡ Escalation Triggers</h4>
                  <div className="space-y-1 text-sm text-orange-800">
                    <p>• Ticket overdue by 1+ hours</p>
                    <p>• System down affecting 10+ users</p>
                    <p>• Security incident detected</p>
                    <p>• Business critical system failure</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default UrgentTickets;