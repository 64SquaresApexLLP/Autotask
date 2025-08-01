import React, { useState } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import { Search, Filter, Download, UserCheck, RotateCcw, AlertTriangle, Calendar, User } from 'lucide-react';

const technicians = ['Aditya', 'Mahima', 'Archit'];

const allTickets = [
  {
    id: 'TKT-001234',
    title: 'Password Reset Request',
    status: 'resolved',
    priority: 'medium',
    category: 'Account',
    customer: 'Anant',
    assignedTech: 'Aditya',
    createdDate: '2024-01-15',
    department: 'Finance',
  },
  {
    id: 'TKT-001235',
    title: 'Software Installation - Adobe Creative Suite',
    status: 'progress',
    priority: 'low',
    category: 'Software',
    customer: 'Raj',
    assignedTech: 'Mahima',
    createdDate: '2024-01-16',
    department: 'Marketing',
  },
  {
    id: 'TKT-001236',
    title: 'Network Connectivity Issues',
    status: 'open',
    priority: 'high',
    category: 'Network',
    customer: 'Avishkar',
    assignedTech: 'Aditya',
    createdDate: '2024-01-17',
    department: 'Engineering',
  },
  {
    id: 'TKT-001237',
    title: 'Desktop Computer Not Starting',
    status: 'progress',
    priority: 'critical',
    category: 'Hardware',
    customer: 'Anant',
    assignedTech: 'Aditya',
    createdDate: '2024-01-17',
    department: 'Finance',
  },
  {
    id: 'TKT-001238',
    title: 'Email Configuration Help',
    status: 'open',
    priority: 'medium',
    category: 'Email',
    customer: 'Raj',
    assignedTech: 'Unassigned',
    createdDate: '2024-01-17',
    department: 'Marketing',
  },
  {
    id: 'TKT-001239',
    title: 'VPN Access Issues',
    status: 'open',
    priority: 'high',
    category: 'Network',
    customer: 'Avishkar',
    assignedTech: 'Unassigned',
    createdDate: '2024-01-17',
    department: 'Engineering',
  },
  {
    id: 'TKT-001240',
    title: 'Printer Not Working',
    status: 'closed',
    priority: 'low',
    category: 'Hardware',
    customer: 'Anant',
    assignedTech: 'Archit',
    createdDate: '2024-01-16',
    department: 'Finance',
  },
];

const AllTickets = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [technicianFilter, setTechnicianFilter] = useState('all');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [selectedTickets, setSelectedTickets] = useState([]);

  const departments = [...new Set(allTickets.map(t => t.department))];

  const filteredTickets = allTickets.filter(ticket => {
    const matchesSearch = ticket.title.toLowerCase().includes(searchTerm.toLowerCase())
      || ticket.id.toLowerCase().includes(searchTerm.toLowerCase())
      || ticket.customer.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || ticket.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || ticket.priority === priorityFilter;
    const matchesTech = technicianFilter === 'all' || ticket.assignedTech === technicianFilter;
    const matchesDept = departmentFilter === 'all' || ticket.department === departmentFilter;

    return matchesSearch && matchesStatus && matchesPriority && matchesTech && matchesDept;
  });

  const getPriorityColor = priority => {
    return {
      low: 'text-green-600',
      medium: 'text-yellow-600',
      high: 'text-orange-600',
      critical: 'text-red-600',
    }[priority] || 'text-gray-600';
  };

  const getStatusStyle = status => {
    return {
      open: 'bg-blue-100 text-blue-800',
      progress: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      closed: 'bg-gray-100 text-gray-800',
    }[status] || 'bg-gray-200 text-gray-800';
  };

  const toggleSelectTicket = id => {
    setSelectedTickets(prev =>
      prev.includes(id) ? prev.filter(tid => tid !== id) : [...prev, id]
    );
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">📋 All Tickets</h1>
              <p className="text-gray-600">Manage all system-wide tickets</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Total Tickets</p>
                <p className="text-2xl font-bold">{allTickets.length}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Unassigned</p>
                <p className="text-2xl font-bold text-orange-600">{allTickets.filter(t => t.assignedTech === 'Unassigned').length}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Critical / High</p>
                <p className="text-2xl font-bold text-red-600">{allTickets.filter(t => ['critical', 'high'].includes(t.priority)).length}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-sm text-gray-500">Open / Progress</p>
                <p className="text-2xl font-bold text-blue-600">{allTickets.filter(t => ['open', 'progress'].includes(t.status)).length}</p>
              </div>
            </div>

            {/* Filter Card */}
            <div className="bg-white rounded-lg shadow p-4 space-y-4">
              <div className="flex items-center gap-2">
                <Filter className="h-5 w-5 text-gray-500" />
                <h2 className="text-lg font-semibold text-gray-800">Filter Tickets</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                <input
                  type="text"
                  placeholder="Search..."
                  className="px-3 py-2 border rounded w-full"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Status</option>
                  <option value="open">Open</option>
                  <option value="progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
                <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Priority</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select value={technicianFilter} onChange={e => setTechnicianFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Technicians</option>
                  <option value="Unassigned">Unassigned</option>
                  {technicians.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <select value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)} className="px-3 py-2 border rounded w-full">
                  <option value="all">All Departments</option>
                  {departments.map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-auto bg-white rounded-lg shadow">
              <table className="min-w-full text-sm text-left">
                <thead className="bg-gray-100 border-b">
                  <tr>
                    <th className="p-3">#</th>
                    <th className="p-3">Title</th>
                    <th className="p-3">Customer</th>
                    <th className="p-3">Dept</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Priority</th>
                    <th className="p-3">Technician</th>
                    <th className="p-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTickets.map((ticket, idx) => (
                    <tr key={ticket.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-mono text-xs">{ticket.id}</td>
                      <td className="p-3">{ticket.title}</td>
                      <td className="p-3 flex items-center gap-1"><User className="w-4 h-4 text-gray-400" />{ticket.customer}</td>
                      <td className="p-3">{ticket.department}</td>
                      <td className="p-3"><span className={`px-2 py-1 rounded text-xs font-medium ${getStatusStyle(ticket.status)}`}>{ticket.status}</span></td>
                      <td className="p-3"><span className={`${getPriorityColor(ticket.priority)} font-semibold`}>{ticket.priority}</span></td>
                      <td className="p-3">{ticket.assignedTech === 'Unassigned' ? <span className="text-orange-600 font-medium flex items-center"><AlertTriangle className="w-4 h-4 mr-1" />Unassigned</span> : ticket.assignedTech}</td>
                      <td className="p-3 flex items-center gap-1"><Calendar className="w-4 h-4 text-gray-400" />{ticket.createdDate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            
            
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default AllTickets;
