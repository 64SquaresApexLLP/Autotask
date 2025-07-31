// src/components/Sidebar.jsx
import React from 'react';
import { Settings, Wrench, FileText, Users, BarChart3, CheckSquare, AlertCircle, List } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  const { user } = useAuth();

  const userMenuItems = [
    { icon: FileText, label: 'Submit Request', active: true, path: '/user' },
    { icon: BarChart3, label: 'Track Status', active: false, path: '/user/track-status' },
    { icon: Settings, label: 'My Profile', active: false, path: '/user/profile' }
  ];

  const technicianMenuItems = [
    { icon: Wrench, label: 'Dashboard', path: '/technician/dashboard' },
    { icon: List, label: 'My Tickets', path: '/technician/my-tickets' },
    { icon: AlertCircle, label: 'Urgent Tickets', path: '/technician/urgent-tickets' },
    { icon: BarChart3, label: 'Analytics', path: '/technician/analytics' },
    { icon: CheckSquare, label: 'All Tickets', path: '/technician/all-tickets' }
  ];

  const menuItems = user?.role === 'user' ? userMenuItems : technicianMenuItems;

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