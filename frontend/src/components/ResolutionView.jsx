import React, { useState } from 'react';
import { UserCheck, Wrench, ShieldAlert } from 'lucide-react';
import { parseResolutionContent } from '../utils/resolutionParser';

const ResolutionView = ({
  resolution,
  initialTab = 'all',
  showSelector = true,
  compact = false,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState(initialTab);

  if (!resolution) {
    return (
      <div className="text-xs md:text-sm text-gray-500 italic p-3 bg-gray-50 rounded-lg">
        No resolution generated yet.
      </div>
    );
  }

  const { subscriber, technician, safety } = parseResolutionContent(resolution);

  return (
    <div className={`space-y-3.5 ${className}`}>
      {/* View Switcher Pills */}
      {showSelector && (
        <div className="flex items-center justify-between flex-wrap gap-2 pb-0.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 uppercase tracking-wider">
            <span>Resolutions</span>
          </div>
          <div className="inline-flex rounded-lg bg-gray-200/70 p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1 rounded-md transition-all ${
                activeTab === 'all'
                  ? 'bg-white text-gray-900 shadow-sm font-semibold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              All Views
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('subscriber')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'subscriber'
                  ? 'bg-white text-emerald-800 shadow-sm font-semibold'
                  : 'text-gray-600 hover:text-emerald-700'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
              Subscriber View
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('technician')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'technician'
                  ? 'bg-white text-blue-800 shadow-sm font-semibold'
                  : 'text-gray-600 hover:text-blue-700'
              }`}
            >
              <Wrench className="w-3.5 h-3.5 text-[#00ABE4]" />
              Technician View
            </button>
          </div>
        </div>
      )}

      {/* 1. Subscriber Self-Service Resolution Card */}
      {(activeTab === 'all' || activeTab === 'subscriber') && subscriber && (
        <div className="bg-emerald-50/60 rounded-lg border border-emerald-200 p-3.5 sm:p-4 shadow-sm transition-all">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm">
              <UserCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Subscriber Self-Service Guidance</span>
            </div>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300/60">
              Customer Safe Actions
            </span>
          </div>
          <div className="text-xs md:text-sm text-emerald-950 leading-relaxed whitespace-pre-line font-sans pl-0.5">
            {subscriber}
          </div>
        </div>
      )}

      {/* 2. Technician Field Remediation Card */}
      {(activeTab === 'all' || activeTab === 'technician') && technician && (
        <div className="bg-white rounded-lg border border-blue-200 p-3.5 sm:p-4 shadow-sm transition-all">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-blue-900 font-bold text-sm">
              <Wrench className="w-4 h-4 text-[#00ABE4] flex-shrink-0" />
              <span>Technician Field Remediation Protocol</span>
            </div>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Engineering Action Plan
            </span>
          </div>
          <div className="text-xs md:text-sm text-gray-800 leading-relaxed whitespace-pre-line font-sans pl-0.5">
            {technician}
          </div>
        </div>
      )}

      {/* 3. Mandatory Safety Precautions Callout */}
      {safety && (
        <div className="bg-amber-50/90 border-l-4 border-amber-500 rounded-r-lg p-3.5 sm:p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1.5 text-amber-900 font-bold text-sm">
            <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>MANDATORY SAFETY PRECAUTIONS</span>
          </div>
          <div className="text-xs md:text-sm text-amber-900 leading-relaxed whitespace-pre-line font-medium pl-0.5">
            {safety}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResolutionView;
