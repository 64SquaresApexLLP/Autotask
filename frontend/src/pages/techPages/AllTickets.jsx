// src/pages/techPages/AllTickets.jsx
import React from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';

const AllTickets = () => {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1">
        <Header />
        <main className="p-6 md:p-8">
          <div className="max-w-6xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-800 mb-3">All Tickets</h1>
              <p className="text-gray-600 text-base md:text-lg">View and manage all system tickets.</p>
            </div>
            {/* Add your ticket management components here */}
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
};

export default AllTickets;