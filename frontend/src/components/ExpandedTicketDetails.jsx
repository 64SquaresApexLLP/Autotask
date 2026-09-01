import React from 'react';
import { AlertCircle, Calendar, CheckCircle, Clock, Mail, Phone, Sparkles, User } from 'lucide-react';

const getStatusIcon = (status) => {
  switch (status?.toLowerCase()) {
    case 'completed':
    case 'resolved':
      return <CheckCircle className="w-5 h-5 text-green-600" />;
    case 'in_progress':
    case 'assigned':
      return <Clock className="w-5 h-5 text-blue-600" />;
    default:
      return <AlertCircle className="w-5 h-5 text-yellow-600" />;
  }
};

const ExpandedTicketDetails = ({ ticket }) => {
  if (!ticket) return null;

  return (
    <div className="border-t border-gray-200 p-4 md:p-6 bg-gray-50/60">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          {getStatusIcon(ticket.status)}
          <h4 className="font-semibold text-gray-800">Ticket Details</h4>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          ticket.status?.toLowerCase() === 'completed' || ticket.status?.toLowerCase() === 'resolved'
            ? 'text-green-600 bg-green-50'
            : ticket.status?.toLowerCase() === 'in_progress' || ticket.status?.toLowerCase() === 'assigned'
              ? 'text-blue-600 bg-blue-50'
              : 'text-yellow-600 bg-yellow-50'
        }`}>
        </span>
      </div>

      <p className="text-gray-600 mb-4">{ticket.description || 'No description provided.'}</p>

      {(ticket.ticket_category || ticket.issue_type) && (
        <div className="flex items-center flex-wrap gap-2 mb-4">
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-500">
        <div className="flex items-center space-x-2">
          <User className="w-4 h-4" />
          <span>Requester: {ticket.requester_name || 'Not specified'}</span>
        </div>
        {ticket.phone_number && (
          <div className="flex items-center space-x-2">
            <Phone className="w-4 h-4" />
            <span>{ticket.phone_number}</span>
          </div>
        )}
        {ticket.user_email && (
          <div className="flex items-center space-x-2">
            <Mail className="w-4 h-4" />
            <span>{ticket.user_email}</span>
          </div>
        )}
        {ticket.due_date && (
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4" />
            <span>Due: {new Date(ticket.due_date).toLocaleDateString()}</span>
          </div>
        )}
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4" />
          <span>Created: {new Date(ticket.created_at || Date.now()).toLocaleDateString()}</span>
        </div>
        {ticket.assigned_technician && (
          <div className="flex items-center space-x-2">
            <User className="w-4 h-4" />
            <span>Assigned to: {ticket.assigned_technician}</span>
          </div>
        )}
        {ticket.resolution && (
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4" />
            <span>Resolution: {ticket.resolution}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExpandedTicketDetails;