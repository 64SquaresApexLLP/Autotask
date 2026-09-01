import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserPlus, 
  Trash2, 
  Search, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  X, 
  Mail, 
  Phone, 
  Building2, 
  ShieldCheck, 
  Calendar 
} from 'lucide-react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { adminService } from '../../services/adminService';
import { ticketService } from '../../services/ticketService';

const DEPARTMENTS = [
  'General',
  'Customer Support',
  'Operations',
  'Network Engineering',
  'IT Operations',
  'Sales & Accounts',
  'Executive Management'
];

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDept, setFilterDept] = useState('all');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Add User Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    username: '',
    password: 'password123',
    full_name: '',
    email: '',
    phone_number: '',
    department: 'Customer Support',
    role: 'user'
  });

  const loadUsers = async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError('');

      const [usersRes, allTicketsRes] = await Promise.all([
        adminService.getUsers().catch(() => ({ users: [], total: 0 })),
        ticketService.getAllTickets({ limit: 300 }).catch(() => [])
      ]);

      const baseUsers = usersRes.users || [];
      const tickets = allTicketsRes || [];

      // Map tickets dynamically to each user
      const mappedUsers = baseUsers.map(u => {
        const uEmail = (u.email || '').toLowerCase().trim();
        const uName = (u.full_name || '').toLowerCase().trim();
        const uUname = (u.username || '').toLowerCase().trim();

        const userTickets = tickets.filter(t => {
          const tEmail = (t.user_email || '').toLowerCase().trim();
          const tUser = (t.user_id || '').toLowerCase().trim();
          const tReq = (t.requester_name || '').toLowerCase().trim();

          return (uEmail && tEmail === uEmail) ||
                 (uUname && tUser === uUname) ||
                 (uName && tReq === uName) ||
                 (uUname && tReq === uUname) ||
                 (uEmail && tReq === uEmail);
        });

        const activeCount = userTickets.filter(t => !['resolved', 'closed'].includes((t.status || '').toLowerCase())).length;
        const resolvedCount = userTickets.filter(t => ['resolved', 'closed'].includes((t.status || '').toLowerCase())).length;

        return {
          ...u,
          total_tickets: userTickets.length > 0 ? userTickets.length : (u.total_tickets || 0),
          active_tickets: userTickets.length > 0 ? activeCount : (u.active_tickets || 0),
          resolved_tickets: userTickets.length > 0 ? resolvedCount : (u.resolved_tickets || 0)
        };
      });

      setUsers(mappedUsers);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError('Unable to load user accounts.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUserForm.username || !newUserForm.full_name) {
      setError('Username and Full Name are required.');
      return;
    }

    try {
      setLoading(true);
      await adminService.createUser(newUserForm);
      setSuccessMessage(`User ${newUserForm.full_name} created successfully!`);
      setShowAddModal(false);
      setNewUserForm({
        username: '',
        password: 'password123',
        full_name: '',
        email: '',
        phone_number: '',
        department: 'Customer Support',
        role: 'user'
      });
      loadUsers(true);
    } catch (err) {
      setError(err.message || 'Failed to create user.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (!window.confirm(`Are you sure you want to remove user '${userName}'?`)) return;

    try {
      setLoading(true);
      await adminService.deleteUser(userId);
      setSuccessMessage(`User '${userName}' removed successfully.`);
      loadUsers(true);
    } catch (err) {
      setError(err.message || 'Failed to remove user.');
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(u => {
    const matchesSearch = 
      u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.department?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesDept = filterDept === 'all' || u.department?.toLowerCase() === filterDept.toLowerCase();

    return matchesSearch && matchesDept;
  });

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* Page Title Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-500 to-emerald-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">
                    User Administration
                  </h1>
                  <p className="text-gray-600 text-sm mt-0.5">
                    Manage registered employee accounts, contact details, departments, and support access privileges.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center space-x-2 bg-[#00ABE4] hover:bg-[#0095c8] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Add New User</span>
                </button>

                <button
                  onClick={() => loadUsers(true)}
                  disabled={loading || refreshing}
                  className="p-2.5 bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  title="Refresh Users"
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

            {/* Search and Department Filter Bar */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="relative w-full sm:w-96">
                <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 transform -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by name, username, email, department..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                />
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <span className="text-xs font-semibold text-gray-500 whitespace-nowrap">Department:</span>
                <select
                  value={filterDept}
                  onChange={(e) => setFilterDept(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#00ABE4]"
                >
                  <option value="all">All Departments</option>
                  {DEPARTMENTS.map((dept, idx) => (
                    <option key={idx} value={dept}>{dept}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {loading && !refreshing ? (
                <div className="p-12 flex flex-col items-center justify-center space-y-3">
                  <Loader2 className="w-8 h-8 animate-spin text-[#00ABE4]" />
                  <p className="text-sm font-medium text-gray-600">Loading user accounts...</p>
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="p-12 text-center">
                  <p className="text-gray-500 font-medium">No users found matching criteria.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600">
                    <thead className="bg-gray-50 text-xs uppercase font-semibold text-gray-500 border-b border-gray-200">
                      <tr>
                        <th className="py-3.5 px-4">User</th>
                        <th className="py-3.5 px-4">Email</th>
                        <th className="py-3.5 px-4">Department</th>
                        <th className="py-3.5 px-4">Phone</th>
                        <th className="py-3.5 px-4">Mapped Tickets</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {filteredUsers.map((u) => (
                        <tr key={u.user_id} className="hover:bg-gray-50/80 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="flex items-center space-x-3">
                              <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-sm">
                                {u.full_name?.charAt(0) || 'U'}
                              </div>
                              <div>
                                <p className="font-semibold text-gray-900">{u.full_name}</p>
                                <p className="text-xs text-gray-500">@{u.username}</p>
                              </div>
                            </div>
                          </td>

                          <td className="py-3.5 px-4 text-gray-700">
                            {u.email}
                          </td>

                          <td className="py-3.5 px-4">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              {u.department || 'General'}
                            </span>
                          </td>

                          <td className="py-3.5 px-4 text-gray-700">
                            {u.phone_number || 'N/A'}
                          </td>

                          <td className="py-3.5 px-4">
                            <div className="flex items-center space-x-2">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-blue-50 text-[#00ABE4]">
                                {u.total_tickets ?? 0} Total
                              </span>
                              {(u.active_tickets ?? 0) > 0 && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700">
                                  {u.active_tickets} Active
                                </span>
                              )}
                              {(u.resolved_tickets ?? 0) > 0 && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
                                  {u.resolved_tickets} Closed
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3.5 px-4">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              Active
                            </span>
                          </td>

                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => handleDeleteUser(u.user_id, u.full_name)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                              title="Delete User"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* MODAL: Add New User */}
            {showAddModal && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                      <UserPlus className="w-5 h-5 text-emerald-600" />
                      Add New User Account
                    </h3>
                    <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <form onSubmit={handleAddUser} className="space-y-3.5">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Username *</label>
                      <input
                        type="text"
                        required
                        value={newUserForm.username}
                        onChange={(e) => setNewUserForm({ ...newUserForm, username: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                        placeholder="e.g. john_doe"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Full Name *</label>
                      <input
                        type="text"
                        required
                        value={newUserForm.full_name}
                        onChange={(e) => setNewUserForm({ ...newUserForm, full_name: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                        placeholder="e.g. John Doe"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Email</label>
                      <input
                        type="email"
                        value={newUserForm.email}
                        onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                        placeholder="john@example.com"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Department</label>
                        <select
                          value={newUserForm.department}
                          onChange={(e) => setNewUserForm({ ...newUserForm, department: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none bg-white"
                        >
                          {DEPARTMENTS.map((dept, idx) => (
                            <option key={idx} value={dept}>{dept}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Phone Number</label>
                        <input
                          type="text"
                          value={newUserForm.phone_number}
                          onChange={(e) => setNewUserForm({ ...newUserForm, phone_number: e.target.value })}
                          className="w-full text-sm border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-[#00ABE4] focus:outline-none"
                          placeholder="+1-555-0100"
                        />
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
                        className="px-5 py-2 text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
                      >
                        Create User
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

export default AdminUsers;
