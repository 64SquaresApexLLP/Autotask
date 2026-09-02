import React, { useState, useEffect } from 'react';
import { 
  Wrench, 
  Plus, 
  Trash2, 
  Edit, 
  Clock, 
  Award, 
  ShieldCheck, 
  Search, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  X, 
  UserPlus,
  Phone,
  Mail,
  Sliders,
  Check
} from 'lucide-react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { adminService } from '../../services/adminService';
import { ticketService } from '../../services/ticketService';

const AVAILABLE_SKILLS = [
  'Network Routing & EVPN',
  'Optical & Fiber Trunks',
  'Hardware Diagnostics',
  'Software & OS Drift',
  'Active Directory',
  'Server Infrastructure',
  'VoIP & Central Office AP',
  'Emergency Triage',
  'Cloud Infrastructure',
  'Core MX960 Architecture'
];

const SHIFT_OPTIONS = [
  'Morning (08:00 - 16:00)',
  'Afternoon (14:00 - 22:00)',
  'Night (22:00 - 06:00)',
  'On-Call 24/7'
];

const AdminTechnicians = () => {
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterShift, setFilterShift] = useState('all');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [selectedTech, setSelectedTech] = useState(null);

  // Form states
  const [newTechForm, setNewTechForm] = useState({
    username: '',
    password: 'password123',
    full_name: '',
    email: '',
    phone_number: '',
    technician_role: 'L2 Specialist',
    primary_shift: 'Morning (08:00 - 16:00)',
    on_call_status: 'Standby',
    experience_level: 'L2 Specialist',
    skill_sets: ['Network Routing & EVPN', 'Hardware Diagnostics'],
    max_capacity: 10
  });

  const [scheduleForm, setScheduleForm] = useState({
    primary_shift: '',
    on_call_status: '',
    experience_level: '',
    max_capacity: 10,
    skill_sets: []
  });

  const loadTechnicians = async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError('');

      const [techsRes, allTicketsRes] = await Promise.all([
        adminService.getTechnicians().catch(() => ({ technicians: [], total: 0 })),
        ticketService.getAllTickets({ limit: 300 }).catch(() => [])
      ]);

      const baseTechs = techsRes.technicians || [];
      const tickets = allTicketsRes || [];

      // Map tickets dynamically to each technician
      const mappedTechs = baseTechs.map(tech => {
        const tName = (tech.full_name || '').toLowerCase().trim();
        const tUname = (tech.username || '').toLowerCase().trim();
        const tId = (tech.technician_id || '').toLowerCase().trim();

        const techTickets = tickets.filter(ticket => {
          const assigned = (ticket.assigned_technician_display || ticket.assigned_technician || ticket.assigned_to || ticket.technician_name || ticket.technician_id || '').toLowerCase().trim();

          return (tName && assigned.includes(tName)) ||
                 (tUname && assigned.includes(tUname)) ||
                 (tId && assigned.includes(tId)) ||
                 (assigned && (tName.includes(assigned) || tUname.includes(assigned)));
        });

        const activeTickets = techTickets.filter(t => !['resolved', 'closed'].includes((t.status || '').toLowerCase()));
        const resolvedTickets = techTickets.filter(t => ['resolved', 'closed'].includes((t.status || '').toLowerCase()));

        return {
          ...tech,
          current_tickets_load: techTickets.length > 0 ? activeTickets.length : (tech.current_tickets_load || 0),
          resolved_tickets_count: techTickets.length > 0 ? resolvedTickets.length : (tech.resolved_tickets_count || 0),
          assigned_tickets_preview: activeTickets.slice(0, 4)
        };
      });

      setTechnicians(mappedTechs);
    } catch (err) {
      console.error('Failed to load technicians:', err);
      setError('Unable to load technician roster.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadTechnicians();
  }, []);

  const handleAddTechnician = async (e) => {
    e.preventDefault();
    if (!newTechForm.username || !newTechForm.full_name) {
      setError('Username and Full Name are required.');
      return;
    }

    try {
      setLoading(true);
      await adminService.createTechnician(newTechForm);
      setSuccessMessage(`Technician ${newTechForm.full_name} added successfully!`);
      setShowAddModal(false);
      setNewTechForm({
        username: '',
        password: 'password123',
        full_name: '',
        email: '',
        phone_number: '',
        technician_role: 'L2 Specialist',
        primary_shift: 'Morning (08:00 - 16:00)',
        on_call_status: 'Standby',
        experience_level: 'L2 Specialist',
        skill_sets: ['Network Routing & EVPN', 'Hardware Diagnostics'],
        max_capacity: 10
      });
      loadTechnicians(true);
    } catch (err) {
      setError(err.message || 'Failed to add technician.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTechnician = async (techId, techName) => {
    if (!window.confirm(`Are you sure you want to remove technician ${techName}?`)) return;

    try {
      setLoading(true);
      await adminService.deleteTechnician(techId);
      setSuccessMessage(`Technician ${techName} removed.`);
      loadTechnicians(true);
    } catch (err) {
      setError(err.message || 'Failed to remove technician.');
    } finally {
      setLoading(false);
    }
  };

  const openScheduleModal = (tech) => {
    setSelectedTech(tech);
    setScheduleForm({
      primary_shift: tech.primary_shift || 'Morning (08:00 - 16:00)',
      on_call_status: tech.on_call_status || 'Standby',
      experience_level: tech.experience_level || 'L2 Specialist',
      max_capacity: tech.max_capacity || 10,
      skill_sets: Array.isArray(tech.skill_sets) ? [...tech.skill_sets] : []
    });
    setShowScheduleModal(true);
  };

  const handleUpdateSchedule = async (e) => {
    e.preventDefault();
    if (!selectedTech) return;

    try {
      setLoading(true);
      await adminService.updateTechnicianScheduleAndSkills(selectedTech.technician_id, scheduleForm);
      setSuccessMessage(`Updated schedule and skills for ${selectedTech.full_name}!`);
      setShowScheduleModal(false);
      loadTechnicians(true);
    } catch (err) {
      setError(err.message || 'Failed to update schedule.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSkill = (skill, isNew = false) => {
    if (isNew) {
      const current = newTechForm.skill_sets || [];
      const updated = current.includes(skill)
        ? current.filter(s => s !== skill)
        : [...current, skill];
      setNewTechForm({ ...newTechForm, skill_sets: updated });
    } else {
      const current = scheduleForm.skill_sets || [];
      const updated = current.includes(skill)
        ? current.filter(s => s !== skill)
        : [...current, skill];
      setScheduleForm({ ...scheduleForm, skill_sets: updated });
    }
  };

  const filteredTechs = technicians.filter(t => {
    const matchesSearch = 
      t.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.skill_sets?.some(s => s.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesShift = filterShift === 'all' || t.primary_shift?.toLowerCase().includes(filterShift.toLowerCase());

    return matchesSearch && matchesShift;
  });

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Page Title & Top Actions */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <Wrench className="w-6 h-6" />
                </div>
                {/* <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                    Technician Shifts & Skillsets
                  </h1>
                  <p className="text-gray-600 text-sm mt-0.5">
                    Schedule working shifts, on-call rotations, skill credentials, and maximum workload capacities.
                  </p>
                </div> */}
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center space-x-2 bg-[#00ABE4] hover:bg-[#0095c8] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Add Technician</span>
                </button>

                <button
                  onClick={() => loadTechnicians(true)}
                  disabled={loading || refreshing}
                  className="p-2.5 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  title="Refresh Roster"
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

            {successMessage && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span>{successMessage}</span>
                </div>
                <button onClick={() => setSuccessMessage('')} className="text-emerald-600 hover:text-emerald-800">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Search and Shift Filter Bar */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="relative w-full sm:w-96">
                <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 transform -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search technician by name, username, skill..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                />
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <span className="text-xs font-semibold text-gray-500 whitespace-nowrap">Shift Filter:</span>
                <select
                  value={filterShift}
                  onChange={(e) => setFilterShift(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                >
                  <option value="all">All Shifts (24/7)</option>
                  <option value="morning">Morning Shift</option>
                  <option value="afternoon">Afternoon Shift</option>
                  <option value="night">Night Shift</option>
                  <option value="on-call">On-Call</option>
                </select>
              </div>
            </div>

            {/* Technicians Grid / Table */}
            {loading && !refreshing ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4]" />
                <p className="text-sm font-medium text-gray-600">Loading technician roster...</p>
              </div>
            ) : filteredTechs.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                <p className="text-gray-500 font-medium">No technicians found matching criteria.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredTechs.map((tech) => (
                  <div key={tech.technician_id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col justify-between hover:border-gray-300 transition-all">
                    <div>
                      {/* Top Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold text-lg">
                            {tech.full_name?.charAt(0) || 'T'}
                          </div>
                          <div>
                            <h3 className="text-base font-bold text-gray-900">{tech.full_name}</h3>
                            <p className="text-xs text-gray-500">@{tech.username} • {tech.technician_role || 'Technician'}</p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-1.5">
                          <button
                            onClick={() => openScheduleModal(tech)}
                            className="p-1.5 text-gray-500 hover:text-[#00ABE4] hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                            title="Edit Schedule & Skills"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteTechnician(tech.technician_id, tech.full_name)}
                            className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                            title="Remove Technician"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Contact and Shift Badges */}
                      <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-3 text-xs">
                        <div className="flex items-center space-x-2 text-gray-600">
                          <Mail className="w-3.5 h-3.5 text-gray-400" />
                          <span className="truncate">{tech.email || 'N/A'}</span>
                        </div>
                        <div className="flex items-center space-x-2 text-gray-600">
                          <Phone className="w-3.5 h-3.5 text-gray-400" />
                          <span>{tech.phone_number || 'N/A'}</span>
                        </div>
                      </div>

                      {/* Shift & On-Call Status */}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          <Clock className="w-3.5 h-3.5" />
                          {tech.primary_shift}
                        </span>

                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold ${
                          tech.on_call_status === 'Active'
                            ? 'bg-purple-50 text-purple-700 border border-purple-200'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          <ShieldCheck className="w-3.5 h-3.5" />
                          {tech.on_call_status === 'Active' ? 'On-Call Ready' : 'Standby'}
                        </span>
                      </div>

                      {/* Skills List */}
                      <div className="mt-3">
                        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Assigned Skillsets</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(tech.skill_sets || []).map((skill, sIdx) => (
                            <span key={sIdx} className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-700">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Capacity Load Bar */}
                    <div className="mt-4 pt-3 border-t border-gray-100">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>Workload Capacity</span>
                        <span className="font-semibold text-gray-800">
                          {tech.current_tickets_load ?? 0} / {tech.max_capacity ?? 10} Tickets
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            ((tech.current_tickets_load ?? 0) / (tech.max_capacity ?? 10)) > 0.8
                              ? 'bg-red-500'
                              : ((tech.current_tickets_load ?? 0) / (tech.max_capacity ?? 10)) > 0.5
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, (((tech.current_tickets_load ?? 0) / (tech.max_capacity ?? 10)) * 100))}%` }}
                        ></div>
                      </div>
                    </div>

                  </div>
                ))}
              </div>
            )}

            {/* MODAL: Add Technician */}
            {showAddModal && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                      <UserPlus className="w-5 h-5 text-[#00ABE4]" />
                      Add New Technician
                    </h3>
                    <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <form onSubmit={handleAddTechnician} className="space-y-3.5">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Username *</label>
                        <input
                          type="text"
                          required
                          value={newTechForm.username}
                          onChange={(e) => setNewTechForm({ ...newTechForm, username: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                          placeholder="e.g. tech_sarah"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Full Name *</label>
                        <input
                          type="text"
                          required
                          value={newTechForm.full_name}
                          onChange={(e) => setNewTechForm({ ...newTechForm, full_name: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                          placeholder="e.g. Sarah Jenkins"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Email</label>
                        <input
                          type="email"
                          value={newTechForm.email}
                          onChange={(e) => setNewTechForm({ ...newTechForm, email: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                          placeholder="sarah@example.com"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Phone Number</label>
                        <input
                          type="text"
                          value={newTechForm.phone_number}
                          onChange={(e) => setNewTechForm({ ...newTechForm, phone_number: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                          placeholder="+1-555-0199"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Primary Shift</label>
                        <select
                          value={newTechForm.primary_shift}
                          onChange={(e) => setNewTechForm({ ...newTechForm, primary_shift: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none bg-white"
                        >
                          {SHIFT_OPTIONS.map((sh, idx) => (
                            <option key={idx} value={sh}>{sh}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">On-Call Status</label>
                        <select
                          value={newTechForm.on_call_status}
                          onChange={(e) => setNewTechForm({ ...newTechForm, on_call_status: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none bg-white"
                        >
                          <option value="Active">Active</option>
                          <option value="Standby">Standby</option>
                          <option value="Off">Off</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">Assign Skillsets</label>
                      <div className="flex flex-wrap gap-2">
                        {AVAILABLE_SKILLS.map((skill, sIdx) => {
                          const isSelected = (newTechForm.skill_sets || []).includes(skill);
                          return (
                            <button
                              type="button"
                              key={sIdx}
                              onClick={() => toggleSkill(skill, true)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1 cursor-pointer ${
                                isSelected 
                                  ? 'bg-[#00ABE4] text-white shadow-sm' 
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {isSelected && <Check className="w-3 h-3" />}
                              <span>{skill}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-100">
                      <button
                        type="button"
                        onClick={() => setShowAddModal(false)}
                        className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={loading}
                        className="px-5 py-2 text-sm bg-[#00ABE4] hover:bg-[#0095c8] text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
                      >
                        Save Technician
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* MODAL: Edit Schedule & Skills */}
            {showScheduleModal && selectedTech && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">Configure Shift & Skillsets</h3>
                      <p className="text-xs text-gray-500">Updating roster settings for {selectedTech.full_name}</p>
                    </div>
                    <button onClick={() => setShowScheduleModal(false)} className="text-gray-400 hover:text-gray-600">
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <form onSubmit={handleUpdateSchedule} className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Primary Shift</label>
                      <select
                        value={scheduleForm.primary_shift}
                        onChange={(e) => setScheduleForm({ ...scheduleForm, primary_shift: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none bg-white"
                      >
                        {SHIFT_OPTIONS.map((sh, idx) => (
                          <option key={idx} value={sh}>{sh}</option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">On-Call Rotation</label>
                        <select
                          value={scheduleForm.on_call_status}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, on_call_status: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none bg-white"
                        >
                          <option value="Active">Active</option>
                          <option value="Standby">Standby</option>
                          <option value="Off">Off</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Max Ticket Capacity</label>
                        <input
                          type="number"
                          min="1"
                          max="25"
                          value={scheduleForm.max_capacity}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, max_capacity: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-2">Technician Skills</label>
                      <div className="flex flex-wrap gap-2">
                        {AVAILABLE_SKILLS.map((skill, sIdx) => {
                          const isSelected = (scheduleForm.skill_sets || []).includes(skill);
                          return (
                            <button
                              type="button"
                              key={sIdx}
                              onClick={() => toggleSkill(skill, false)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                                isSelected 
                                  ? 'bg-[#00ABE4] text-white shadow-sm font-semibold' 
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {isSelected && <Check className="w-3.5 h-3.5" />}
                              <span>{skill}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-100">
                      <button
                        type="button"
                        onClick={() => setShowScheduleModal(false)}
                        className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={loading}
                        className="px-5 py-2 text-sm bg-[#00ABE4] hover:bg-[#0095c8] text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
                      >
                        Update Schedule & Skills
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminTechnicians;
