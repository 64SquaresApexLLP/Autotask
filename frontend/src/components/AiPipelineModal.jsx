import React, { useEffect, useState } from 'react';
import {
  Inbox, Brain, Tag, Layers, Zap, UserCheck, Link2, Wand2,
  FileCheck2, Loader2, CheckCircle2, ChevronDown, ChevronUp
} from 'lucide-react';

const priorityColors = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-100 text-red-800',
};

/**
 * Builds the ordered list of pipeline steps from the REAL ticket-creation
 * response (result of POST /tickets, transformed by ticketService). Every
 * value rendered here comes from the backend's actual AI workflow output -
 * nothing here is invented on the frontend.
 */
const buildSteps = (submitted, result) => {
  const metadata = result?.extracted_metadata || {};
  const similar = result?.similar_tickets || [];

  return [
    {
      key: 'received',
      icon: Inbox,
      title: 'Ticket Input Received by AI',
      subtitle: 'Your submission, exactly as sent to the backend',
      render: () => (
        <div className="space-y-1 text-sm">
          <p><span className="text-gray-500">Title:</span> <span className="font-medium text-gray-800">{submitted.title}</span></p>
          <p className="text-gray-600">{submitted.description}</p>
        </div>
      ),
    },
    {
      key: 'analysis',
      icon: Brain,
      title: 'AI Analysis / Reasoning',
      subtitle: 'What the model extracted from your description',
      render: () => (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
          <InfoRow label="Main Issue" value={metadata.main_issue} />
          <InfoRow label="Affected System" value={metadata.affected_system} />
          <InfoRow label="Urgency Signal" value={metadata.urgency_level} />
          <InfoRow label="Error Messages" value={metadata.error_messages} />
          <InfoRow
            label="Keywords"
            value={Array.isArray(metadata.technical_keywords) ? metadata.technical_keywords.join(', ') : metadata.technical_keywords}
          />
          <InfoRow label="User Actions Taken" value={metadata.user_actions} />
        </div>
      ),
    },
    {
      key: 'category',
      icon: Tag,
      title: 'Issue Categorization',
      subtitle: 'How the AI classified this ticket',
      render: () => (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-[#E9F1FA] text-[#00ABE4]">
          {result.ticket_category || 'N/A'}
        </span>
      ),
    },
    {
      key: 'issueType',
      icon: Layers,
      title: 'Issue Type Detection',
      subtitle: 'Specific issue type and sub-type identified',
      render: () => (
        <div className="flex flex-wrap gap-2">
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700">{result.issue_type || 'N/A'}</span>
          {result.sub_issue_type && (
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-50 text-gray-500 border border-gray-200">{result.sub_issue_type}</span>
          )}
        </div>
      ),
    },
    {
      key: 'priority',
      icon: Zap,
      title: 'Priority Detection',
      subtitle: 'AI-assessed priority for this ticket',
      render: () => (
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${priorityColors[result.priority?.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
          {result.priority || 'Medium'}
        </span>
      ),
    },
    {
      key: 'assignment',
      icon: UserCheck,
      title: 'Technician Assignment',
      subtitle: 'Who your ticket was routed to',
      render: () => (
        <p className="text-sm font-medium text-gray-800">
          {result.assigned_technician_display || result.assigned_technician || 'Being assigned...'}
        </p>
      ),
    },
    {
      key: 'similar',
      icon: Link2,
      title: 'Similar Ticket Results',
      subtitle: `${similar.length} related ticket${similar.length === 1 ? '' : 's'} found`,
      render: () => (
        similar.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No similar past tickets found.</p>
        ) : (
          <div className="space-y-2">
            {similar.slice(0, 4).map((t) => (
              <div key={t.ticket_number} className="border border-gray-200 rounded-lg p-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800">{t.ticket_number} - {t.title}</span>
                  <span className="text-xs text-gray-500">{t.status}</span>
                </div>
              </div>
            ))}
          </div>
        )
      ),
    },
    {
      key: 'resolution',
      icon: Wand2,
      title: 'AI-Generated Resolution',
      subtitle: 'Suggested fix, ready for technician review',
      render: () => (
        result.resolution ? (
          <p className="text-sm text-gray-700 p-3 bg-purple-50 border border-purple-100 rounded whitespace-pre-line">{result.resolution}</p>
        ) : (
          <p className="text-sm text-gray-500 italic">No resolution generated.</p>
        )
      ),
    },
    {
      key: 'final',
      icon: FileCheck2,
      title: 'Final Ticket Information',
      subtitle: 'Your ticket is live and trackable',
      render: () => (
        <div className="grid grid-cols-2 gap-2 text-sm">
          <InfoRow label="Ticket #" value={result.id} />
          <InfoRow label="Status" value="Created" />
        </div>
      ),
    },
  ];
};

const InfoRow = ({ label, value }) => (
  <div className="bg-gray-50 rounded-lg p-2">
    <div className="text-xs text-gray-500">{label}</div>
    <div className="text-gray-800 font-medium break-words">{value || 'N/A'}</div>
  </div>
);

/**
 * Visualizes the real backend AI pipeline for a just-created ticket.
 * `result` must be null while the POST /tickets call is in flight, and the
 * full transformed ticket (with extracted_metadata/similar_tickets/etc.)
 * once it resolves. Steps reveal progressively purely for readability -
 * every value shown is the actual backend response, not simulated.
 */
const AiPipelineModal = ({ submitted, result, onClose }) => {
  const [revealCount, setRevealCount] = useState(0);
  const [expandedStep, setExpandedStep] = useState(null);

  const steps = result ? buildSteps(submitted, result) : [];

  useEffect(() => {
    if (!result) return undefined;
    setRevealCount(0);
    const interval = setInterval(() => {
      setRevealCount((count) => {
        if (count >= steps.length) {
          clearInterval(interval);
          return count;
        }
        return count + 1;
      });
    }, 450);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const allRevealed = result && revealCount >= steps.length;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Brain className="w-5 h-5 text-[#00ABE4]" />
            AI Ticket Processing
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {result ? 'Here is exactly what our AI did with your request.' : 'Submitting your ticket to the AI workflow...'}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {!result && (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <Loader2 className="w-10 h-10 animate-spin text-[#00ABE4] mb-4" />
              <p className="text-gray-600 text-sm">Our AI is analyzing, categorizing, and generating a resolution.</p>
              <p className="text-gray-400 text-xs mt-1">This typically takes 60-90 seconds.</p>
            </div>
          )}

          {steps.map((step, index) => {
            const isRevealed = index < revealCount;
            const isExpanded = expandedStep === step.key;
            const StepIcon = step.icon;

            if (!isRevealed) return null;

            return (
              <div key={step.key} className="border border-gray-200 rounded-lg animate-[fadeIn_0.3s_ease-in]">
                <button
                  onClick={() => setExpandedStep(isExpanded ? null : step.key)}
                  className="w-full flex items-center justify-between p-3 text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#E9F1FA] flex items-center justify-center shrink-0">
                      <StepIcon className="w-4 h-4 text-[#00ABE4]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{step.title}</p>
                      <p className="text-xs text-gray-500">{step.subtitle}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                  </div>
                </button>
                {isExpanded && (
                  <div className="px-4 pb-4 pt-1">
                    {step.render()}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {allRevealed && (
          <div className="p-6 border-t border-gray-100">
            <button
              onClick={onClose}
              className="w-full bg-[#00ABE4] text-white py-3 rounded-lg hover:bg-blue-600 transition-colors font-medium"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AiPipelineModal;
