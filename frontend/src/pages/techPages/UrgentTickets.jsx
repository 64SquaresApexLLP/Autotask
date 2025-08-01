import React, { useState } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import { AlertTriangle, User, Phone, Mail, Zap } from 'lucide-react';
import useAuth from '../../hooks/useAuth';

// Mock urgent tickets data
const urgentTickets = [
  {
    id: "TKT-001237",
    title: "Desktop Computer Not Starting",
    priority: "critical",
    customer: "Anant",
    customerEmail: "anantlad66@gmail.com",
    customerPhone: "+1 (555) 123-4567",
    department: "Finance",
    createdDate: "2024-01-17 13:30",
    slaDeadline: "2024-01-17 17:30",
    description: "Desktop computer completely unresponsive, no power lights. User cannot work.",
    businessImpact: "High - Finance team member unable to process payroll",
    escalationLevel: 1,
    timeRemaining: "2h 15m",
    status: "progress",
  },
  {
    id: "TKT-001239",
    title: "Email Server Down - Multiple Users Affected",
    priority: "down",
    customer: "System Alert",
    customerEmail: "alerts@company.com",
    customerPhone: "+1 (555) 123-4567",
    department: "IT Infrastructure",
    createdDate: "2024-01-17 15:45",
    slaDeadline: "2024-01-17 16:45",
    description: "Email server unresponsive. 50+ users cannot send/receive emails.",
    businessImpact: "Critical - Company-wide email outage affecting all departments",
    escalationLevel: 2,
    timeRemaining: "OVERDUE",
    status: "open",
  },
  {
    id: "TKT-001240",
    title: "Network Outage - Building A",
    priority: "critical",
    customer: "Network Monitor",
    customerEmail: "network@company.com",
    customerPhone: "+1 (555) 123-4567",
    department: "IT Infrastructure",
    createdDate: "2024-01-17 16:00",
    slaDeadline: "2024-01-17 20:00",
    description: "Complete network outage in Building A affecting 30+ workstations",
    businessImpact: "High - Entire Building A cannot access network resources",
    escalationLevel: 1,
    timeRemaining: "3h 45m",
    status: "open",
  },
];

const availableTechnicians = [
  { name: "Aditya", skills: ["Hardware", "Network"], status: "available", currentLoad: 3 },
  { name: "Mahima", skills: ["Software", "Cloud", "SaaS"], status: "busy", currentLoad: 5 },
  { name: "Archit", skills: ["Admin", "HR", "IT"], status: "available", currentLoad: 2 },
];

const UrgentTickets = () => {
  const { user } = useAuth();
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const handleTakeTicket = (ticketId) => {
    setToastMessage({
      title: "Ticket Assigned! 🚨",
      description: `Urgent ticket ${ticketId} has been assigned to you. Customer notified.`,
    });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleEscalate = (ticketId) => {
    setToastMessage({
      title: "Ticket Escalated! ⬆️",
      description: `Ticket ${ticketId} has been escalated to senior technician. Management notified.`,
    });
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
    switch (priority) {
      case "critical":
        return "bg-red-500 text-white";
      case "down":
        return "bg-purple-600 text-white";
      default:
        return "bg-orange-500 text-white";
    }
  };

  

  const getSLAProgress = (timeRemaining) => {
    if (timeRemaining === "OVERDUE") return 0;
    // Mock calculation - in real app, calculate based on actual time
    const hours = parseFloat(timeRemaining.replace(/[^\d.]/g, ""));
    return Math.max(0, Math.min(100, (hours / 4) * 100));
  };

  const getTimeRemainingColor = (timeRemaining) => {
    if (timeRemaining === "OVERDUE") return "text-red-600 font-bold";
    if (timeRemaining.includes("h") && parseInt(timeRemaining) < 2) return "text-orange-600 font-semibold";
    return "text-gray-600";
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto ">
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
                <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                  {urgentTickets.length} URGENT
                </span>
                <span className="border border-gray-300 px-3 py-1 rounded-full text-sm font-medium">
                  {urgentTickets.filter((t) => t.timeRemaining === "OVERDUE").length} OVERDUE
                </span>
              </div>
            </div>

            {/* Alert Banner */}
            <div className="border border-red-200 bg-red-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-6 w-6 text-red-600 animate-pulse" />
                <div>
                  <p className="font-semibold text-red-800">
                    Critical Alert: Multiple urgent tickets require immediate attention
                  </p>
                  <p className="text-sm text-red-700">
                    {urgentTickets.filter((t) => t.timeRemaining === "OVERDUE").length} tickets are overdue. Emergency
                    escalation protocols may be triggered.
                  </p>
                </div>
              </div>
            </div>

            {/* Urgent Tickets Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {urgentTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className={`border-2 rounded-lg p-4 ${ticket.priority === "down" ? "border-purple-300 bg-purple-50" : "border-red-300 bg-red-50"}`}
                >
                  <div className="pb-3">
                    <div className="flex items-center justify-between mb-3">
                      <span className={`${getPriorityColor(ticket.priority)} px-3 py-1 rounded-full text-xs font-medium`}>
                        {ticket.priority === "down" ? "🚨 SYSTEM DOWN" : "🔴 CRITICAL"}
                      </span>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">SLA</p>
                        <p className={`text-sm font-mono ${getTimeRemainingColor(ticket.timeRemaining)}`}>
                          {ticket.timeRemaining}
                        </p>
                      </div>
                    </div>
                    <h2 className="text-lg font-bold">{ticket.title}</h2>
                    <p className="text-sm text-gray-500">
                      {ticket.id} • {ticket.department}
                    </p>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-1">Business Impact:</p>
                      <p className="text-sm text-red-700 bg-red-100 p-2 rounded">{ticket.businessImpact}</p>
                    </div>

                    <div>
                      <p className="text-sm font-medium mb-1">Description:</p>
                      <p className="text-sm text-gray-600">{ticket.description}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="font-medium">Customer:</p>
                        <p className="text-gray-600">{ticket.customer}</p>
                      </div>
                      <div>
                        <p className="font-medium">Created:</p>
                        <p className="text-gray-600">{ticket.createdDate}</p>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>SLA Progress</span>
                        <span>{getSLAProgress(ticket.timeRemaining)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${ticket.timeRemaining === "OVERDUE" ? "bg-red-500" : "bg-blue-500"}`}
                          style={{ width: `${getSLAProgress(ticket.timeRemaining)}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button
                        className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center justify-center"
                        onClick={() => handleTakeTicket(ticket.id)}
                      >
                        <Zap className="h-4 w-4 mr-1" />
                        Take Ticket
                      </button>
                      <button
                        className="border border-gray-300 hover:bg-gray-100 px-4 py-2 rounded-lg text-sm font-medium"
                        onClick={() => handleEscalate(ticket.id)}
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

                    {ticket.escalationLevel > 1 && (
                      <div className="p-2 bg-yellow-100 border border-yellow-300 rounded text-xs">
                        <p className="font-medium text-yellow-800">⚠️ Escalation Level {ticket.escalationLevel}</p>
                        <p className="text-yellow-700">Management has been notified</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Team Availability */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                <User className="h-5 w-5" />
                <h2 className="text-xl font-semibold">Team Availability for Urgent Assignments</h2>
              </div>
              <p className="text-gray-600 mb-6">Current technician availability and skill matching</p>
              
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
                      <button
                        className={`w-full px-4 py-2 rounded-lg text-sm font-medium ${tech.status === "available" ? "bg-blue-600 hover:bg-blue-700 text-white" : "border border-gray-300 text-gray-500 cursor-not-allowed"}`}
                        disabled={tech.status !== "available"}
                      >
                        {tech.status === "available" ? "Assign Ticket" : "Busy"}
                      </button>
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