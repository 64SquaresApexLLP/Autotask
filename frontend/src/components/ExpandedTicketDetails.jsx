import React from 'react';
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  Mail,
  Phone,
  Sparkles,
  User,
  ShieldAlert,
  Wrench
} from 'lucide-react';

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

/**
 * Splits a resolution string into actionable resolution steps and safety precautions.
 */
const parseResolutionContent = (rawResolution) => {
  if (!rawResolution || typeof rawResolution !== 'string') {
    return { steps: '', safety: '' };
  }

  const safetyKeywords = ['⚠️ SAFETY PRECAUTIONS:', 'SAFETY PRECAUTIONS:', '⚠️ SAFETY PRECAUTIONS', '[SAFETY PRECAUTIONS]'];
  for (const kw of safetyKeywords) {
    const idx = rawResolution.indexOf(kw);
    if (idx !== -1) {
      const steps = rawResolution.substring(0, idx).trim();
      const safety = rawResolution.substring(idx).trim();
      return { steps, safety };
    }
  }

  return { steps: rawResolution.trim(), safety: '' };
};

const ExpandedTicketDetails = ({ ticket }) => {
  if (!ticket) return null;

  const { steps, safety } = parseResolutionContent(ticket.resolution);

  return (
    <div className="border-t border-gray-200 p-4 md:p-6 bg-gray-50/60 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon(ticket.status)}
          <h4 className="font-semibold text-gray-800">Ticket Details</h4>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          ticket.status?.toLowerCase() === 'completed' || ticket.status?.toLowerCase() === 'resolved'
            ? 'text-green-600 bg-green-50 border border-green-200'
            : ticket.status?.toLowerCase() === 'in_progress' || ticket.status?.toLowerCase() === 'assigned'
              ? 'text-blue-600 bg-blue-50 border border-blue-200'
              : 'text-yellow-600 bg-yellow-50 border border-yellow-200'
        }`}>
          {ticket.status || 'Open'}
        </span>
      </div>

      <p className="text-gray-700 leading-relaxed text-sm bg-white p-3 rounded-lg border border-gray-200/80 shadow-sm">
        {ticket.description || 'No description provided.'}
      </p>

      {(ticket.ticket_category || ticket.issue_type) && (
        <div className="flex items-center flex-wrap gap-2">
          {ticket.ticket_category && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-[#E9F1FA] text-[#00ABE4] border border-[#00ABE4]/20">
              <Sparkles className="w-3.5 h-3.5" />
              Category: {ticket.ticket_category}
            </span>
          )}
          {ticket.issue_type && (
            <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
              Issue Type: {ticket.issue_type}
            </span>
          )}
          {ticket.sub_issue_type && (
            <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
              Sub-Issue: {ticket.sub_issue_type}
            </span>
          )}
        </div>
      )}

      {/* Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-sm text-gray-600 bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="flex items-center space-x-2.5">
          <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span className="truncate">Requester: <strong className="text-gray-700">{ticket.requester_name || 'Not specified'}</strong></span>
        </div>
        {ticket.phone_number && (
          <div className="flex items-center space-x-2.5">
            <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span>Phone: <strong className="text-gray-700">{ticket.phone_number}</strong></span>
          </div>
        )}
        {ticket.user_email && (
          <div className="flex items-center space-x-2.5">
            <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="truncate">Email: <strong className="text-gray-700">{ticket.user_email}</strong></span>
          </div>
        )}
        {ticket.due_date && (
          <div className="flex items-center space-x-2.5">
            <Calendar className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span>Due: <strong className="text-gray-700">{new Date(ticket.due_date).toLocaleDateString()}</strong></span>
          </div>
        )}
        <div className="flex items-center space-x-2.5">
          <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span>Created: <strong className="text-gray-700">{new Date(ticket.created_at || Date.now()).toLocaleDateString()}</strong></span>
        </div>
        {ticket.assigned_technician && (
          <div className="flex items-center space-x-2.5">
            <User className="w-4 h-4 text-[#00ABE4] flex-shrink-0" />
            <span>Assigned: <strong className="text-gray-800">{ticket.assigned_technician}</strong></span>
          </div>
        )}
      </div>

      {/* Resolution & Safety Precautions */}
      {ticket.resolution && (
        <div className="space-y-3 pt-1">
          {/* Actionable Resolution Steps */}
          <div className="bg-white rounded-lg border border-blue-100 p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2.5 text-blue-900 font-semibold text-sm">
              <Wrench className="w-4 h-4 text-[#00ABE4]" />
              <span>Resolution & Action Plan</span>
            </div>
            <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line font-sans pl-1">
              {steps || ticket.resolution}
            </div>
          </div>

          {/* Safety Precautions Highlight Callout */}
          {safety && (
            <div className="bg-amber-50/90 border-l-4 border-amber-500 rounded-r-lg p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2 text-amber-900 font-bold text-sm">
                <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <span>MANDATORY SAFETY PRECAUTIONS</span>
              </div>
              <div className="text-xs md:text-sm text-amber-900 leading-relaxed whitespace-pre-line font-medium pl-1">
                {safety.replace(/^⚠️?\s*SAFETY PRECAUTIONS:?\s*/i, '')}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExpandedTicketDetails;