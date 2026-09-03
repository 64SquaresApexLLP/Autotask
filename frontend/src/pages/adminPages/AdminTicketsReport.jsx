import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, 
  Download, 
  Search, 
  Filter, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  TrendingUp,
  ArrowUpRight,
  ShieldCheck,
  Tag,
  User,
  Calendar
} from 'lucide-react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { adminService } from '../../services/adminService';
import { ticketService } from '../../services/ticketService';
import { calculateTicketSla } from '../../components/MttrCard';

const AdminTicketsReport = () => {
  const [reportData, setReportData] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [error, setError] = useState('');

  const loadMasterReport = async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError('');

      const [masterRes, allTicketsRes] = await Promise.all([
        adminService.getMasterTicketsReport().catch(() => null),
        ticketService.getAllTickets({ limit: 300 }).catch(() => [])
      ]);

      setReportData(masterRes);
      setTickets(allTicketsRes.length > 0 ? allTicketsRes : (masterRes?.tickets || []));
    } catch (err) {
      console.error('Failed to load master tickets report:', err);
      setError('Unable to load master tickets report.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadMasterReport();
  }, []);

  const handleExportCSV = () => {
    if (filteredTickets.length === 0) return;

    const headers = ['Ticket ID', 'Title', 'Category', 'Priority', 'Status', 'Assigned To', 'Requester', 'Created At'];
    const csvRows = [headers.join(',')];

    filteredTickets.forEach(t => {
      const row = [
        `"${t.id || t.ticket_id || t.ticket_number || ''}"`,
        `"${(t.title || '').replace(/"/g, '""')}"`,
        `"${t.category || t.ticket_category || 'General'}"`,
        `"${t.priority || 'Medium'}"`,
        `"${t.status || 'Open'}"`,
        `"${t.assigned_technician_display || t.assigned_technician || t.assigned_to || t.technician_name || 'Unassigned'}"`,
        `"${t.requester_name || t.user_email || t.user_id || ''}"`,
        `"${t.created_at || ''}"`
      ];
      csvRows.push(row.join(','));
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + csvRows.join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Master_Tickets_Report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredTickets = tickets.map(t => ({
    ...t,
    displayId: t.id || t.ticket_id || t.ticket_number || 'T-Unknown',
    displayCategory: t.category || t.ticket_category || 'General',
    displayTech: t.assigned_technician_display || t.assigned_technician || t.assigned_to || t.technician_name || 'Unassigned',
    displayRequester: t.requester_name || t.user_email || t.user_id || 'User'
  })).filter(t => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = 
      (t.title || '').toLowerCase().includes(term) ||
      (t.displayId || '').toLowerCase().includes(term) ||
      (t.displayTech || '').toLowerCase().includes(term) ||
      (t.displayRequester || '').toLowerCase().includes(term) ||
      (t.displayCategory || '').toLowerCase().includes(term);

    const matchesStatus = statusFilter === 'all' || (t.status || '').toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority = priorityFilter === 'all' || (t.priority || '').toLowerCase() === priorityFilter.toLowerCase();
    const matchesCategory = categoryFilter === 'all' || (t.displayCategory || '').toLowerCase() === categoryFilter.toLowerCase();

    return matchesSearch && matchesStatus && matchesPriority && matchesCategory;
  });

  const totalCount = tickets.length;
  const resolvedCount = tickets.filter(t => ['resolved', 'closed'].includes((t.status || '').toLowerCase())).length;
  const inProgressCount = tickets.filter(t => ['in progress', 'investigating', 'pending', 'assigned'].includes((t.status || '').toLowerCase())).length;
  const openCount = totalCount - resolvedCount - inProgressCount;
  const resolutionRate = totalCount > 0 ? Math.round((resolvedCount / totalCount) * 100) : 100;

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Header Banner */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <CheckSquare className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                   Exicutive Dashboard
                  </h1>
                  <p className="text-gray-600 text-sm mt-0.5">
                    Centralized system ticket logs, resolution lifecycle auditing, technician assignments, and CSV data exports.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleExportCSV}
                  disabled={filteredTickets.length === 0}
                  className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Export CSV</span>
                </button>

                <button
                  onClick={() => loadMasterReport(true)}
                  disabled={loading || refreshing}
                  className="p-2.5 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  title="Refresh Report"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-[#00ABE4]' : ''}`} />
                </button>
              </div>
            </div>

            {/* Alerts */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Master Summary KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Tickets</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalCount}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">Across all departments</p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-blue-50 text-[#00ABE4] flex items-center justify-center">
                  <CheckSquare className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Resolved Tickets</p>
                  <h3 className="text-2xl font-bold text-emerald-600 mt-1">{resolvedCount}</h3>
                  <p className="text-xs text-emerald-600 font-medium mt-0.5">Closed successfully</p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">In Progress / Active</p>
                  <h3 className="text-2xl font-bold text-amber-600 mt-1">{inProgressCount}</h3>
                  <p className="text-xs text-amber-600 font-medium mt-0.5">Under technician queue</p>
                </div>
                <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Clock className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Resolution Rate</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    {resolutionRate >= 80 ? 'Target Met' : 'Attention'}
                  </span>
                </div>
                <div className="mt-2">
                  <div className="flex items-baseline justify-between">
                    <h3 className="text-2xl font-bold text-gray-900">{resolutionRate}%</h3>
                    <span className="text-xs text-gray-500">Fleet Average</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 mt-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${resolutionRate}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-col lg:flex-row items-center justify-between gap-4">
              <div className="relative w-full lg:w-80">
                <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 transform -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search tickets by ID, title, tech..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                >
                  <option value="all">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="in progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>

                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                >
                  <option value="all">All Priorities</option>
                  <option value="critical">Critical (P1)</option>
                  <option value="high">High (P2)</option>
                  <option value="medium">Medium (P3)</option>
                  <option value="low">Low (P4)</option>
                </select>

                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                >
                  <option value="all">All Categories</option>
                  <option value="network">Network</option>
                  <option value="hardware">Hardware</option>
                  <option value="software">Software</option>
                  <option value="security">Security</option>
                </select>
              </div>
            </div>

            {/* Master Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {loading && !refreshing ? (
                <div className="p-12 flex flex-col items-center justify-center space-y-3">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4]" />
                  <p className="text-sm font-medium text-gray-600">Compiling master ticket report...</p>
                </div>
              ) : filteredTickets.length === 0 ? (
                <div className="p-12 text-center">
                  <p className="text-gray-500 font-medium">No tickets found matching criteria.</p>
                </div>
              ) : (
                <div className="w-full">
                  <table className="w-full table-fixed text-left text-sm text-gray-600">
                    <thead className="bg-gray-50 text-xs uppercase font-semibold text-gray-500 border-b border-gray-200">
                      <tr>
                        <th className="py-3.5 px-4">Ticket ID</th>
                        <th className="py-3.5 px-4">Title & Issue</th>
                        <th className="py-3.5 px-4">Category</th>
                        <th className="py-3.5 px-4">Priority</th>
                        <th className="py-3.5 px-4">Assigned Tech</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4">Created Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {filteredTickets.map((t, idx) => {
                        const priorityLower = (t.priority || 'medium').toLowerCase();
                        const statusLower = (t.status || 'open').toLowerCase();

                        return (
                          <tr key={idx} className="hover:bg-gray-50/80 transition-colors">
                            <td className="py-3.5 px-4 font-mono font-bold text-xs text-[#00ABE4]">
                              {t.displayId}
                            </td>

                            <td className="py-3.5 px-4">
                              <p className="font-semibold text-gray-900 line-clamp-1">{t.title}</p>
                              {t.displayRequester && (
                                <p className="text-xs text-gray-400">By: {t.displayRequester}</p>
                              )}
                            </td>

                            <td className="py-3.5 px-4">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                {t.displayCategory}
                              </span>
                            </td>

                            <td className="py-3.5 px-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold ${
                                priorityLower === 'critical'
                                  ? 'bg-red-100 text-red-700 border border-red-200'
                                  : priorityLower === 'high'
                                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                    : priorityLower === 'medium'
                                      ? 'bg-blue-100 text-blue-800'
                                      : 'bg-gray-100 text-gray-700'
                              }`}>
                                {t.priority || 'Medium'}
                              </span>
                            </td>

                            <td className="py-3.5 px-4 text-gray-800 font-medium">
                              {t.displayTech}
                            </td>

                            <td className="py-3.5 px-4">
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                                ['resolved', 'closed'].includes(statusLower)
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : ['in progress', 'investigating'].includes(statusLower)
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                    : 'bg-blue-50 text-blue-700 border border-blue-200'
                              }`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${
                                  ['resolved', 'closed'].includes(statusLower)
                                    ? 'bg-emerald-500'
                                    : ['in progress', 'investigating'].includes(statusLower)
                                      ? 'bg-amber-500'
                                      : 'bg-blue-500'
                                }`}></span>
                                {t.status || 'Open'}
                              </span>
                            </td>

                            <td className="py-3.5 px-2 sm:px-4 text-xs text-gray-500">
                              {t.created_at ? new Date(t.created_at).toLocaleDateString() : 'Recent'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminTicketsReport;
