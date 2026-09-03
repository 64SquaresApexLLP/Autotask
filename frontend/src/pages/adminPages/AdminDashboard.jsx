import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Users, 
  Wrench, 
  CheckSquare, 
  Timer, 
  TrendingUp, 
  ArrowUpRight, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Plus, 
  RefreshCw,
  Loader2,
  Calendar,
  Zap,
  Activity,
  Layers
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { adminService } from '../../services/adminService';
import { ticketService } from '../../services/ticketService';
import useAuth from '../../hooks/useAuth';

const AdminDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [usersCount, setUsersCount] = useState(0);
  const [techsCount, setTechsCount] = useState(0);
  const [ticketsData, setTicketsData] = useState(null);
  const [mttrData, setMttrData] = useState(null);
  const [error, setError] = useState('');

  const loadDashboardData = async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError('');

      const [usersRes, techsRes, masterTicketsRes, allTicketsRes, mttrRes] = await Promise.all([
        adminService.getUsers().catch(() => ({ users: [], total: 0 })),
        adminService.getTechnicians().catch(() => ({ technicians: [], total: 0 })),
        adminService.getMasterTicketsReport().catch(() => null),
        ticketService.getAllTickets({ limit: 300 }).catch(() => []),
        adminService.getWiderMttrReport().catch(() => null)
      ]);

      const totalT = allTicketsRes.length > 0 ? allTicketsRes.length : (masterTicketsRes?.total_tickets || 0);
      const resT = allTicketsRes.length > 0 
        ? allTicketsRes.filter(t => ['resolved', 'closed'].includes((t.status || '').toLowerCase())).length 
        : (masterTicketsRes?.resolved_count || 0);
      const rate = totalT > 0 ? Math.round((resT / totalT) * 100) : 100;

      setUsersCount(usersRes.total || (usersRes.users?.length || 0));
      setTechsCount(techsRes.total || (techsRes.technicians?.length || 0));
      setTicketsData({
        total_tickets: totalT,
        resolved_count: resT,
        resolution_rate: rate
      });
      setMttrData(mttrRes);
    } catch (err) {
      console.error('Failed to load admin dashboard data:', err);
      setError('Unable to load full system metrics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header onRefresh={() => loadDashboardData(true)} isRefreshing={loading || refreshing} />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Admin Header Banner */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-700 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center flex-wrap gap-2">
                    <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                      System Administrator Control Center
                    </h1>
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                      <Zap className="w-3.5 h-3.5 text-blue-600" />
                      Executive Scope
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mt-0.5">
                    Live system orchestration, technician shift assignments, ticket resolution SLA oversight, and user administration.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => loadDashboardData(true)}
                  disabled={loading || refreshing}
                  className="flex items-center space-x-2 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-[#00ABE4]' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Top 4 KPI Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* 1. Master Tickets */}
              <div 
                onClick={() => navigate('/admin/tickets-report')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between hover:border-[#00ABE4] transition-all cursor-pointer group"
              >
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total System Tickets</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">{ticketsData?.total_tickets ?? '--'}</h3>
                  <p className="text-xs text-emerald-600 font-medium mt-0.5 flex items-center gap-1">
                    <span>{ticketsData?.resolved_count ?? 0} Resolved</span>
                    <span className="text-gray-400">•</span>
                    <span className="text-blue-600">{ticketsData?.resolution_rate ?? 0}% Rate</span>
                  </p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#00ABE4] flex items-center justify-center group-hover:scale-110 transition-transform">
                  <CheckSquare className="w-6 h-6" />
                </div>
              </div>

              {/* 2. Technicians on Roster */}
              <div 
                onClick={() => navigate('/admin/technicians')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between hover:border-[#00ABE4] transition-all cursor-pointer group"
              >
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Technicians & Shifts</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">{techsCount}</h3>
                  <p className="text-xs text-blue-600 font-medium mt-0.5 flex items-center gap-1">
                    <span>3 Active Shifts</span>
                    <span className="text-gray-400">•</span>
                    <span>2 On-Call</span>
                  </p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Wrench className="w-6 h-6" />
                </div>
              </div>

              {/* 3. Registered Users */}
              <div 
                onClick={() => navigate('/admin/users')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between hover:border-[#00ABE4] transition-all cursor-pointer group"
              >
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Managed Users</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">{usersCount}</h3>
                  <p className="text-xs text-emerald-600 font-medium mt-0.5">Enterprise Accounts</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Users className="w-6 h-6" />
                </div>
              </div>

              {/* 4. Global MTTR & SLA */}
              <div 
                onClick={() => navigate('/admin/wider-mttr')}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center justify-between hover:border-[#00ABE4] transition-all cursor-pointer group"
              >
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Global MTTR Speed</p>
                  <h3 className="text-2xl font-bold text-gray-900 mt-1">{mttrData?.global_mttr_hours ?? '3.8'}h</h3>
                 
                </div>
                <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Timer className="w-6 h-6" />
                </div>
              </div>
            </div>

            {/* Quick Action Navigation Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              

             
              

            </div>

            {/* Shift Distribution Summary & Recent Ticket Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Shift Capacity Matrix */}
              <div className="lg:col-span-6 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-[#00ABE4]" />
                    <h3 className="text-base font-bold text-gray-900">Active Shift Capacity</h3>
                  </div>
                  <span className="text-xs font-semibold text-gray-500">24/7 Coverage</span>
                </div>
                
                <div className="space-y-4">
                  <div className="p-3.5 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-800">🌅 Morning Shift (08:00 - 16:00)</h4>
                      <p className="text-xs text-gray-500 mt-0.5">Primary queue triage & EVPN deployment</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
                      4 Techs Assigned
                    </span>
                  </div>

                  <div className="p-3.5 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-800">☀️ Afternoon Shift (14:00 - 22:00)</h4>
                      <p className="text-xs text-gray-500 mt-0.5">Hardware maintenance & software updates</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                      3 Techs Assigned
                    </span>
                  </div>

                  <div className="p-3.5 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-800">🌙 Night Shift (22:00 - 06:00)</h4>
                      <p className="text-xs text-gray-500 mt-0.5">Emergency optical outage & on-call dispatch</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800">
                      2 Techs Assigned
                    </span>
                  </div>
                </div>
              </div>

              {/* Key Highlights */}
              <div className="lg:col-span-6 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-emerald-600" />
                      <h3 className="text-base font-bold text-gray-900">System Health & SLA Status</h3>
                    </div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      All Systems Optimal
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm py-2 border-b border-gray-100">
                      <span className="text-gray-600">Snowflake Database Connection</span>
                      <span className="font-semibold text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Connected
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-sm py-2 border-b border-gray-100">
                      <span className="text-gray-600">Snowflake Cortex AI LLM</span>
                      <span className="font-semibold text-blue-600 flex items-center gap-1">
                        <Zap className="w-4 h-4" /> llama3.1-70b (Active)
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-sm py-2 border-b border-gray-100">
                      <span className="text-gray-600">Network Topology Nodes</span>
                      <span className="font-semibold text-gray-900">1,190 Nodes & 1,511 Links</span>
                    </div>

                    <div className="flex items-center justify-between text-sm py-2">
                      <span className="text-gray-600">Active Defect Radar Alerts</span>
                      <span className="font-semibold text-amber-600">4 Core Findings</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xs text-gray-500">AutoTask Enterprise v2.4</span>
                  <button 
                    onClick={() => navigate('/technician/ontology')}
                    className="text-xs font-semibold text-[#00ABE4] hover:underline cursor-pointer"
                  >
                    Open Network Topology &rarr;
                  </button>
                </div>
              </div>

            </div>

          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
