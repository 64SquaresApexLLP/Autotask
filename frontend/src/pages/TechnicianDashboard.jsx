import React from 'react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatButton from '../components/ChatButton';
import { Wrench, Bell, Clock, AlertTriangle, Settings, Users, FileText, Calendar, TrendingUp } from 'lucide-react';
import useAuth from '../hooks/useAuth';

const ProgressBar = ({ percentage, color = "bg-blue-500" }) => (
  <div className="w-full bg-gray-200 rounded-full h-3">
    <div 
      className={`${color} h-3 rounded-full transition-all duration-300`} 
      style={{ width: `${percentage}%` }}
    ></div>
  </div>
);

const TechnicianDashboard = () => {

  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto max-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            
            {/* Welcome Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
              <div className="flex items-center space-x-3 mb-4 sm:mb-0">
                <div className="text-2xl">🔧</div>
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-800">Welcome back, {user?.username} !</h1>
                  <p className="text-gray-600 text-sm lg:text-base">Here's your current workload and team status</p>
                </div>
              </div>
              <div className="relative">
                <Bell className="w-6 h-6 text-gray-500 hover:text-gray-700 cursor-pointer" />
                <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  2
                </span>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">📋</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">My Active Tickets</h3>
                <div className="text-3xl font-bold text-gray-900 mb-2">5</div>
                <p className="text-sm text-green-600">+1 since yesterday</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">🚨</div>
                  <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">2</span>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Urgent Tickets</h3>
                <div className="text-3xl font-bold text-red-600 mb-2">2</div>
                <p className="text-sm text-red-600">Requires immediate attention</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">📅</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Today's Assignments</h3>
                <div className="text-3xl font-bold text-blue-600 mb-2">3</div>
                <p className="text-sm text-gray-600">New tickets assigned today</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-2xl">⏱️</div>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Avg Resolution Time</h3>
                <div className="text-3xl font-bold text-green-600 mb-2">4.2 hours</div>
                <p className="text-sm text-green-600">20% faster than team avg</p>
              </div>
            </div>

            {/* Performance Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Performance Metrics */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <TrendingUp className="w-5 h-5 text-yellow-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Performance Metrics</h2>
                </div>
                <p className="text-gray-600 mb-6">Your current performance indicators</p>
                
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">Ticket Completion Rate</span>
                      <span className="text-gray-900 font-semibold">92%</span>
                    </div>
                    <ProgressBar percentage={92} color="bg-blue-500" />
                  </div>
                  
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">Customer Satisfaction</span>
                      <span className="text-gray-900 font-semibold">4.7/5.0</span>
                    </div>
                    <ProgressBar percentage={94} color="bg-green-500" />
                  </div>
                  
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-700 font-medium">SLA Compliance</span>
                      <span className="text-gray-900 font-semibold">94%</span>
                    </div>
                    <ProgressBar percentage={94} color="bg-blue-500" />
                  </div>
                </div>
              </div>

              {/* Team Status */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Users className="w-5 h-5 text-blue-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Team Status</h2>
                </div>
                <p className="text-gray-600 mb-6">Current workload across the team</p>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <div>
                        <div className="font-semibold text-gray-800">Aditya</div>
                        <div className="flex space-x-2 text-xs">
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">Hardware</span>
                          <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">Network</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-gray-600">5 tickets</span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <div>
                        <div className="font-semibold text-gray-800">Mahima</div>
                        <div className="flex space-x-2 text-xs">
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded">Software</span>
                          <span className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded">Cloud</span>
                          <span className="bg-pink-100 text-pink-800 px-2 py-1 rounded">SaaS</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-gray-600">3 tickets</span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <div>
                        <div className="font-semibold text-gray-800">Archit</div>
                        <div className="flex space-x-2 text-xs">
                          <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded">Admin</span>
                          <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded">HR</span>
                          <span className="bg-cyan-100 text-cyan-800 px-2 py-1 rounded">IT</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-gray-600">4 tickets</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Assignments */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
              <div className="flex items-center space-x-2 mb-6">
                <Clock className="w-5 h-5 text-blue-500" />
                <h2 className="text-xl font-semibold text-gray-800">Recent Assignments</h2>
              </div>
              <p className="text-gray-600 mb-6">Latest tickets assigned to you with SLA timers</p>
              
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-red-200 bg-red-50 rounded-lg">
                  <div className="flex items-start space-x-3 mb-3 sm:mb-0">
                    <div className="w-3 h-3 bg-red-500 rounded-full mt-1"></div>
                    <div>
                      <div className="font-semibold text-gray-800">Desktop Computer Not Starting</div>
                      <div className="text-sm text-gray-600 mt-1">TKT-001237 • Customer: Anant • Assigned: 14:00</div>
                    </div>
                  </div>
                  <div className="flex flex-col sm:items-end space-y-2">
                    <span className="text-sm font-medium text-red-600">SLA: 2h 30m</span>
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">View Details</button>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-orange-200 bg-orange-50 rounded-lg">
                  <div className="flex items-start space-x-3 mb-3 sm:mb-0">
                    <div className="w-3 h-3 bg-orange-500 rounded-full mt-1"></div>
                    <div>
                      <div className="font-semibold text-gray-800">Network Connectivity Issues</div>
                      <div className="text-sm text-gray-600 mt-1">TKT-001236 • Customer: Raj • Assigned: 11:00</div>
                    </div>
                  </div>
                  <div className="flex flex-col sm:items-end space-y-2">
                    <span className="text-sm font-medium text-orange-600">SLA: 5h 15m</span>
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">View Details</button>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
                  <div className="flex items-start space-x-3 mb-3 sm:mb-0">
                    <div className="w-3 h-3 bg-yellow-500 rounded-full mt-1"></div>
                    <div>
                      <div className="font-semibold text-gray-800">Email Configuration Help</div>
                      <div className="text-sm text-gray-600 mt-1">TKT-001238 • Customer: Avishkar • Assigned: 09:30</div>
                    </div>
                  </div>
                  <div className="flex flex-col sm:items-end space-y-2">
                    <span className="text-sm font-medium text-yellow-600">SLA: 1d 2h</span>
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">View Details</button>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pending Actions */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <h2 className="text-xl font-semibold text-gray-800">Pending Actions</h2>
                </div>
                <p className="text-gray-600 mb-6">Tickets requiring your attention or updates</p>
                
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-orange-200 bg-orange-50 rounded-lg">
                    <div>
                      <div className="font-semibold text-gray-800 mb-1">Software Installation - Adobe Creative Suite</div>
                      <div className="text-sm text-gray-600 mb-2">TKT-001235 • Raj</div>
                      <div className="flex items-center space-x-1 text-sm text-orange-600">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Awaiting license verification</span>
                      </div>
                    </div>
                    <button className="mt-3 sm:mt-0 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-medium text-sm">
                      Take Action
                    </button>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 border border-orange-200 bg-orange-50 rounded-lg">
                    <div>
                      <div className="font-semibold text-gray-800 mb-1">Password Reset Request</div>
                      <div className="text-sm text-gray-600 mb-2">TKT-001234 • Anant</div>
                      <div className="flex items-center space-x-1 text-sm text-orange-600">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Waiting for user confirmation</span>
                      </div>
                    </div>
                    <button className="mt-3 sm:mt-0 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-medium text-sm">
                      Take Action
                    </button>
                  </div>
                </div>
              </div>

              {/* System Alerts */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Bell className="w-5 h-5 text-blue-500" />
                  <h2 className="text-xl font-semibold text-gray-800">System Alerts</h2>
                </div>
                
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <div className="text-xl">🔧</div>
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">Maintenance</span>
                      </div>
                      <div className="font-semibold text-gray-800 mb-2">File Server Maintenance Scheduled</div>
                      <p className="text-sm text-gray-600">
                        Scheduled maintenance this Saturday 2:00 AM - 6:00 AM EST. Plan accordingly for file access requests.
                      </p>
                    </div>
                  </div>
                </div>
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