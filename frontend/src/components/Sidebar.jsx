import React from 'react';
import { Settings, Wrench, FileText, Users, BarChart3, CheckSquare, AlertCircle, List, Timer, Network, ShieldCheck, Truck } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  const { user } = useAuth();

  const userMenuItems = [
    { icon: FileText, label: 'Submit Request', path: '/user' },
    { icon: BarChart3, label: 'Track Status', path: '/user/track-status' },
    { icon: Settings, label: 'My Profile', path: '/user/profile' }
  ];

  const technicianMenuItems = [
    { icon: Wrench, label: 'Dashboard', path: '/technician/dashboard' },
    { icon: List, label: 'My Tickets', path: '/technician/my-tickets' },
    { icon: Network, label: 'Network Ontology', path: '/technician/ontology' },
    { icon: Timer, label: 'MTTR Report', path: '/technician/mttr-report' },
  ];

  const adminMenuItems = [
    { icon: CheckSquare, label: 'Executive Dashboard', path: '/admin/tickets-report' },
    { icon: List, label: 'All Tickets', path: '/admin/all-tickets' },
    { icon: Wrench, label: 'Technicians & Shifts', path: '/admin/technicians' },
    { icon: Users, label: 'User Management', path: '/admin/users' },
    { icon: Timer, label: 'Reports', path: '/admin/wider-mttr' },
    { icon: Truck, label: 'ONT Truck Roll Report', path: '/admin/ont-truck-roll' },
    { icon: Network, label: 'Network Ontology', path: '/technician/ontology' }
  ];

  const menuItems = user?.role === 'admin' 
    ? adminMenuItems 
    : user?.role === 'user' 
      ? userMenuItems 
      : technicianMenuItems;

  return (
    <aside className="w-64 bg-white shadow-sm border-r border-gray-200 min-h-screen">
      <nav className="p-6">
        <div className="space-y-2">
          {menuItems.map((item, index) => (
            <NavLink
              to={item.path}
              key={index}
              className={({ isActive }) => 
                `w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors text-base ${
                  isActive 
                    ? 'bg-[#E9F1FA] text-[#00ABE4] font-semibold' 
                    : 'text-gray-700 hover:bg-[#E9F1FA] hover:text-[#00ABE4]'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </aside>
  );
};

export default Sidebar;