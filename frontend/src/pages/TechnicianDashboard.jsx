// src/pages/TechnicianDashboard.jsx
import React from 'react';
import { Wrench } from 'lucide-react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatButton from '../components/ChatButton';

const TechnicianDashboard = () => {
  return (
    <div className="flex min-h-screen bg-gray-50">
    <Sidebar />
    <div className="flex-1">
      <Header />
      <main className="p-6 md:p-8">
        <div className="max-w-6xl mx-auto">
          <div className="mb-8">
            <h1 className="text-2xl md:text-3xl font-bold text-gray-800 mb-3">Technician Dashboard</h1>
            <p className="text-gray-600 text-base md:text-lg">Overview of your tasks and performance.</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
            <h2 className="text-lg md:text-xl font-semibold text-gray-800 mb-6">Task Overview</h2>
            <div className="bg-[#E9F1FA] border-2 border-dashed border-[#00ABE4] rounded-lg p-8 md:p-12 text-center">
              <Wrench className="w-12 h-12 text-[#00ABE4] mx-auto mb-4" />
              <p className="text-gray-600 text-base md:text-lg">Dashboard components will be added here</p>
              <p className="text-gray-500 text-sm mt-2">Quick stats, recent activity, etc.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
    <ChatButton />
  </div>
  );
};

export default TechnicianDashboard;