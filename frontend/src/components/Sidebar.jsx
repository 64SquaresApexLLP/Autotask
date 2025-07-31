// src/components/Sidebar.jsx
import React from 'react';
import { Settings, Wrench, FileText, Users, BarChart3, CheckSquare } from 'lucide-react';
import useAuth from '../hooks/useAuth';

const Sidebar = () => {
  const { user } = useAuth();

  const userMenuItems = [
    { icon: FileText, label: 'Submit Request', active: true },
    { icon: BarChart3, label: 'Track Status', active: false },
    { icon: Settings, label: 'My Profile', active: false }
  ];

  const technicianMenuItems = [
    { icon: CheckSquare, label: 'Assigned Tasks', active: true },
    { icon: Users, label: 'Client Requests', active: false },
    { icon: Wrench, label: 'Tools & Resources', active: false }
  ];

  const menuItems = user?.role === 'user' ? userMenuItems : technicianMenuItems;

  return (
    <aside className="w-64 bg-white shadow-sm border-r border-gray-200 min-h-screen">
      <nav className="p-6">
        <div className="space-y-2">
          {menuItems.map((item, index) => (
            <button
              key={index}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors text-base text-left ${
                item.active 
                  ? 'bg-[#E9F1FA] text-[#00ABE4] font-semibold' 
                  : 'text-gray-700 hover:bg-[#E9F1FA] hover:text-[#00ABE4]'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </aside>
  );
};

export default Sidebar;