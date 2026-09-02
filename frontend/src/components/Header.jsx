import React, { useState, useEffect, useRef } from 'react';
import { 
  User, 
  LogOut, 
  Bot, 
  Loader2, 
  RefreshCw, 
  Bell, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  X, 
  ExternalLink, 
  ShieldAlert, 
  Sparkles, 
  Inbox,
  Check,
  ChevronRight
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { ticketService } from '../services/ticketService.js';

const Header = ({ onRefresh, isRefreshing = false }) => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();

  const [localRefreshing, setLocalRefreshing] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'urgent'
  const notifRef = useRef(null);

  // Close notifications dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch live notifications based on tickets and SLAs
  const fetchNotifications = async () => {
    try {
      setLoadingNotifications(true);
      const tickets = await ticketService.getAllTickets({ limit: 50 }).catch(() => []);
      
      const currentUsername = (user?.username || '').toLowerCase().trim();
      const currentUserEmail = (user?.email || '').toLowerCase().trim();
      const currentFullName = (user?.full_name || '').toLowerCase().trim();
      const userRole = (user?.role || '').toLowerCase();

      const notifList = [];

      // 1. Process tickets for alerts & urgent notifications
      tickets.forEach((ticket) => {
        const ticketId = ticket.id || ticket.ticket_number || ticket.ticketnumber || '';
        const title = ticket.title || ticket.issue || 'Operational Ticket';
        const priority = (ticket.priority || 'medium').toLowerCase();
        const status = (ticket.status || 'open').toLowerCase();
        const assignedTech = (ticket.assigned_technician || '').toLowerCase().trim();
        const techEmail = (ticket.technician_email || '').toLowerCase().trim();
        const isAssignedToMe = (
          (currentUsername && assignedTech === currentUsername) ||
          (currentUserEmail && (techEmail === currentUserEmail || assignedTech === currentUserEmail)) ||
          (currentFullName && assignedTech.includes(currentFullName))
        );

        const isClosed = ['resolved', 'closed', 'completed'].includes(status);

        if (!isClosed) {
          // Critical or High Priority Tickets
          if (priority === 'critical' || priority === 'high') {
            notifList.push({
              id: `crit-${ticketId}`,
              ticketId,
              title: `${priority.toUpperCase()}: ${title}`,
              subtitle: isAssignedToMe ? 'Assigned to you • Immediate action required' : `Assigned to ${ticket.assigned_technician || 'Unassigned'}`,
              type: 'urgent',
              priority,
              status,
              time: ticket.created_at || 'Just now',
              read: false,
              link: userRole === 'technician' ? `/technician/my-tickets/view/${ticketId}` : '/technician/all-tickets'
            });
          } else if (isAssignedToMe) {
            notifList.push({
              id: `assign-${ticketId}`,
              ticketId,
              title: `Active Task: ${title}`,
              subtitle: `Status: ${status.toUpperCase()} • Priority: ${priority}`,
              type: 'task',
              priority,
              status,
              time: ticket.created_at || 'Today',
              read: false,
              link: `/technician/my-tickets/view/${ticketId}`
            });
          }
        }
      });

      // 2. Add high-level system notifications
      notifList.push({
        id: 'sys-dispatch',
        ticketId: null,
        title: 'Snowflake Live Telemetry Active',
        subtitle: 'AutoTask ticket pipeline & technician workload synced.',
        type: 'system',
        priority: 'info',
        time: 'Active',
        read: true,
        link: userRole === 'admin' ? '/admin/dashboard' : '/technician/dashboard'
      });

      setNotifications(notifList);
    } catch (err) {
      console.warn('Failed to fetch notifications in top bar:', err);
    } finally {
      setLoadingNotifications(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000); // Check every 60s
    return () => clearInterval(interval);
  }, [user]);

  // Global Refresh Handler
  const handleRefresh = async () => {
    setLocalRefreshing(true);
    try {
      // 1. Trigger custom prop callback if supplied by parent page
      if (typeof onRefresh === 'function') {
        await onRefresh();
      }

      // 2. Dispatch global window event for any listening subcomponents
      window.dispatchEvent(new CustomEvent('app:refresh'));

      // 3. Refresh live notification alerts
      await fetchNotifications();
    } catch (err) {
      console.error('Refresh trigger error:', err);
    } finally {
      setTimeout(() => {
        setLocalRefreshing(false);
      }, 500);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
      navigate('/');
    }
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markAsRead = (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const unreadCount = notifications.filter((n) => !n.read).length;
  const urgentCount = notifications.filter((n) => n.type === 'urgent').length;

  const filteredNotifications = activeTab === 'urgent'
    ? notifications.filter((n) => n.type === 'urgent')
    : notifications;

  const refreshing = isRefreshing || localRefreshing;

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-4 sm:px-6 py-3.5 sticky top-0 z-30">
      <div className="flex items-center justify-between">
        {/* Left side - App brand with icon */}
        <div 
          onClick={() => navigate(user?.role === 'admin' ? '/admin/dashboard' : user?.role === 'technician' ? '/technician/dashboard' : '/user/dashboard')}
          className="flex items-center space-x-3 cursor-pointer group"
          title="Return to Dashboard"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-600 flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
            <Bot className="w-5 h-5" />
          </div>
          <div className="flex items-baseline space-x-2">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-800 tracking-tight group-hover:text-[#00ABE4] transition-colors">
              Autotask
            </h1>
            <span className="hidden sm:inline text-xs font-medium text-gray-400 tracking-wide">
              by InnoSquares
            </span>
          </div>
        </div>

        {/* Right side - Refresh, Notification Center, User profile, and Logout */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Workable Top-Bar Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold text-gray-700 hover:text-[#00ABE4] bg-gray-50 hover:bg-blue-50/80 border border-gray-200 hover:border-blue-200 transition-all shadow-sm cursor-pointer disabled:opacity-50"
            title="Refresh active tickets & metrics across the system"
          >
            <RefreshCw className={`w-4 h-4 text-[#00ABE4] ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>

          {/* Workable Notification Bell & Interactive Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => {
                setShowNotifications(!showNotifications);
                if (!showNotifications) fetchNotifications();
              }}
              className={`relative p-2 rounded-lg border transition-all cursor-pointer ${
                showNotifications
                  ? 'bg-blue-50 text-[#00ABE4] border-blue-300'
                  : 'text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 border-gray-200'
              }`}
              title="Notifications & SLA Alerts"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-bold text-white shadow-sm ring-2 ring-white animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notification Center Popover */}
            {showNotifications && (
              <div className="absolute right-0 mt-2.5 w-80 sm:w-96 rounded-2xl bg-white shadow-2xl border border-gray-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                {/* Popover Header */}
                <div className="bg-gradient-to-r from-slate-900 to-blue-950 p-4 text-white flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Bell className="w-4 h-4 text-[#00ABE4]" />
                    <h3 className="text-sm font-bold tracking-tight">Notification Center</h3>
                    {unreadCount > 0 && (
                      <span className="bg-[#00ABE4] text-white text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                        {unreadCount} New
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllAsRead}
                        className="text-[11px] text-blue-200 hover:text-white underline font-medium transition-colors"
                      >
                        Mark all read
                      </button>
                    )}
                    <button
                      onClick={() => setShowNotifications(false)}
                      className="text-gray-400 hover:text-white p-1 rounded-md transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center border-b border-gray-100 bg-gray-50/80 px-4 py-1.5 text-xs font-semibold text-gray-600 gap-2">
                  <button
                    onClick={() => setActiveTab('all')}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      activeTab === 'all'
                        ? 'bg-white text-[#00ABE4] shadow-sm font-bold'
                        : 'hover:text-gray-900'
                    }`}
                  >
                    All ({notifications.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('urgent')}
                    className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
                      activeTab === 'urgent'
                        ? 'bg-red-50 text-red-600 shadow-sm font-bold'
                        : 'hover:text-red-600'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                    Urgent & Critical ({urgentCount})
                  </button>
                </div>

                {/* Notification Items List */}
                <div className="max-h-80 overflow-y-auto divide-y divide-gray-100">
                  {loadingNotifications ? (
                    <div className="p-8 text-center text-gray-500">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#00ABE4] mb-2" />
                      <p className="text-xs font-medium">Loading notifications...</p>
                    </div>
                  ) : filteredNotifications.length === 0 ? (
                    <div className="p-8 text-center text-gray-400">
                      <Inbox className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                      <p className="text-xs font-semibold text-gray-600">All caught up!</p>
                      <p className="text-[11px] text-gray-400 mt-0.5">No new alerts or urgent tasks in this view.</p>
                    </div>
                  ) : (
                    filteredNotifications.map((notif) => (
                      <div
                        key={notif.id}
                        onClick={() => {
                          markAsRead(notif.id);
                          if (notif.link) {
                            navigate(notif.link);
                            setShowNotifications(false);
                          }
                        }}
                        className={`p-3.5 hover:bg-blue-50/50 transition-colors cursor-pointer flex items-start space-x-3 ${
                          !notif.read ? 'bg-blue-50/30' : 'bg-white'
                        }`}
                      >
                        {/* Icon Indicator */}
                        <div className="mt-0.5 flex-shrink-0">
                          {notif.type === 'urgent' ? (
                            <div className="w-7 h-7 rounded-lg bg-red-100 text-red-600 flex items-center justify-center">
                              <AlertTriangle className="w-4 h-4" />
                            </div>
                          ) : notif.type === 'system' ? (
                            <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
                              <CheckCircle2 className="w-4 h-4" />
                            </div>
                          ) : (
                            <div className="w-7 h-7 rounded-lg bg-blue-100 text-[#00ABE4] flex items-center justify-center">
                              <Clock className="w-4 h-4" />
                            </div>
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1">
                            <p className="text-xs font-bold text-gray-900 truncate">
                              {notif.title}
                            </p>
                            {!notif.read && (
                              <span className="w-2 h-2 rounded-full bg-[#00ABE4] flex-shrink-0"></span>
                            )}
                          </div>
                          <p className="text-[11px] text-gray-600 mt-0.5 line-clamp-2">
                            {notif.subtitle}
                          </p>
                          <div className="flex items-center justify-between mt-1.5 text-[10px] text-gray-400 font-medium">
                            <span>{notif.time}</span>
                            <span className="text-[#00ABE4] flex items-center gap-0.5 hover:underline font-semibold">
                              View Ticket <ChevronRight className="w-3 h-3" />
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Popover Footer Action */}
                <div className="bg-gray-50 border-t border-gray-100 p-2.5 px-4 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-gray-500 font-medium">
                    Live AutoTask Alert Engine
                  </span>
                  <button
                    onClick={() => {
                      setShowNotifications(false);
                      navigate(user?.role === 'technician' ? '/technician/my-tickets' : '/technician/all-tickets');
                    }}
                    className="text-[#00ABE4] hover:text-blue-700 font-bold transition-colors"
                  >
                    View Urgent Queue &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* User Profile Capsule */}
          <div className="flex items-center space-x-2.5 bg-[#E9F1FA] px-3 sm:px-4 py-1.5 rounded-lg border border-blue-100">
            <div className="w-7 h-7 rounded-full bg-white flex items-center justify-center shadow-xs">
              <User className="w-4 h-4 text-[#00ABE4]" />
            </div>
            <div className="text-right">
              <p className="text-xs sm:text-sm font-bold text-gray-800 capitalize leading-tight">
                {user?.role || 'User'}
              </p>
              <p className="text-[10px] sm:text-xs text-gray-600 leading-tight truncate max-w-[100px] sm:max-w-[130px]">
                {user?.full_name || user?.username}
              </p>
            </div>
          </div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            disabled={loading}
            className="flex items-center space-x-1 text-gray-600 hover:text-red-600 transition-colors p-2 hover:bg-red-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed border border-transparent hover:border-red-100"
            title="Logout"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin text-red-500" />
            ) : (
              <LogOut className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;