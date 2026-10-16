import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Inbox,
  Check,
  CheckCheck,
  ChevronRight,
  RotateCw
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { ticketService } from '../services/ticketService.js';
import { formatRelativeTime, calculateSlaStatus } from '../utils/dateUtils.js';

// Local storage helpers for notification read-state persistence
const getStorageKey = (user) => {
  const uid = user?.username || user?.email || user?.id || 'default_user';
  return `autotask_read_notifications_${uid}`;
};

const getStoredReadIds = (user) => {
  try {
    const raw = localStorage.getItem(getStorageKey(user));
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
};

const storeReadIds = (user, idSet) => {
  try {
    localStorage.setItem(getStorageKey(user), JSON.stringify(Array.from(idSet)));
  } catch {}
};

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
  const fetchNotifications = useCallback(async () => {
    try {
      setLoadingNotifications(true);
      const tickets = await ticketService.getAllTickets({ limit: 100 }).catch((err) => {
        console.warn('Failed to fetch tickets for notifications:', err);
        return [];
      });

      const currentUsername = (user?.username || '').toLowerCase().trim();
      const currentUserEmail = (user?.email || '').toLowerCase().trim();
      const currentFullName = (user?.full_name || '').toLowerCase().trim();
      const userRole = (user?.role || '').toLowerCase();
      const storedReadIds = getStoredReadIds(user);

      const notifList = [];

      tickets.forEach((ticket) => {
        const ticketId = ticket.id || ticket.ticket_number || ticket.ticketnumber || '';
        if (!ticketId) return;

        const title = ticket.title || ticket.issue || 'Operational Ticket';
        const priority = (ticket.priority || 'medium').toLowerCase();
        const status = (ticket.status || 'open').toLowerCase();
        const assignedTech = (ticket.assigned_technician || '').toLowerCase().trim();
        const techEmail = (ticket.technician_email || '').toLowerCase().trim();
        const userEmail = (ticket.user_email || '').toLowerCase().trim();

        const isClosed = ['resolved', 'closed', 'completed'].includes(status);
        const isAssignedToMe = (
          (currentUsername && (assignedTech === currentUsername || assignedTech.includes(currentUsername))) ||
          (currentUserEmail && (techEmail === currentUserEmail || assignedTech === currentUserEmail)) ||
          (currentFullName && assignedTech.includes(currentFullName))
        );
        const isMyTicket = (
          (currentUserEmail && userEmail === currentUserEmail) ||
          (currentUsername && (ticket.user_id === currentUsername || userEmail.includes(currentUsername)))
        );

        const sla = calculateSlaStatus(priority, ticket.created_at, ticket.resolved_at, status);
        const timeFormatted = formatRelativeTime(ticket.created_at || ticket.updated_at);

        if (userRole === 'user') {
          // For customers/users: notify on their own tickets
          if (isMyTicket || !currentUserEmail) {
            if (isClosed) {
              const nid = `resolved-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `Resolved: #${ticketId}`,
                subtitle: `${title} — Ticket resolved`,
                type: 'resolved',
                priority,
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: '/user/track-status'
              });
            } else if (sla.status === 'breached') {
              const nid = `sla-user-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `SLA Escalation: #${ticketId}`,
                subtitle: `${title} has been escalated for immediate priority handling.`,
                type: 'urgent',
                priority: 'critical',
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: '/user/track-status'
              });
            } else {
              const nid = `active-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `Ticket #${ticketId} is ${status.toUpperCase()}`,
                subtitle: assignedTech ? `Assigned to ${ticket.assigned_technician_display || assignedTech}` : title,
                type: 'task',
                priority,
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: '/user/track-status'
              });
            }
          }
        } else {
          // For technicians and admins:
          if (!isClosed) {
            // 1. SLA Breached
            if (sla.status === 'breached') {
              const nid = `sla-breach-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `SLA BREACH: #${ticketId}`,
                subtitle: `${title} (${sla.text}) • ${ticket.assigned_technician_display || assignedTech || 'Unassigned'}`,
                type: 'urgent',
                priority: 'critical',
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: `/technician/my-tickets/view/${ticketId}`
              });
            }
            // 2. SLA Approaching
            else if (sla.status === 'approaching') {
              const nid = `sla-warn-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `Approaching SLA: #${ticketId}`,
                subtitle: `${title} • ${sla.remainingHours}h remaining before SLA breach.`,
                type: 'urgent',
                priority: 'high',
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: `/technician/my-tickets/view/${ticketId}`
              });
            }
            // 3. Critical or High Priority Ticket Alert
            else if (priority === 'critical' || priority === 'high') {
              const nid = `crit-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `${priority.toUpperCase()}: #${ticketId}`,
                subtitle: isAssignedToMe ? 'Assigned to you • Immediate action requested' : `${title} • ${ticket.assigned_technician_display || assignedTech || 'Unassigned'}`,
                type: 'urgent',
                priority,
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: `/technician/my-tickets/view/${ticketId}`
              });
            }
            // 4. Assigned to me (Normal priority task)
            else if (isAssignedToMe) {
              const nid = `assign-${ticketId}`;
              notifList.push({
                id: nid,
                ticketId,
                title: `Active Task: #${ticketId}`,
                subtitle: `${title} • Status: ${status.toUpperCase()}`,
                type: 'task',
                priority,
                status,
                time: timeFormatted,
                read: storedReadIds.has(nid),
                link: `/technician/my-tickets/view/${ticketId}`
              });
            }
          }
        }
      });

      // System telemetry notification
      const sysId = 'sys-dispatch-live';
      notifList.push({
        id: sysId,
        ticketId: null,
        title: 'Snowflake Live Telemetry Active',
        subtitle: 'AutoTask ticket pipeline & technician workload synchronized.',
        type: 'system',
        priority: 'info',
        time: 'Live',
        read: storedReadIds.has(sysId),
        link: userRole === 'admin' ? '/admin/dashboard' : userRole === 'technician' ? '/technician/dashboard' : '/user/dashboard'
      });

      // Sort: unread first, then urgent first
      notifList.sort((a, b) => {
        if (a.read !== b.read) return a.read ? 1 : -1;
        if (a.type === 'urgent' && b.type !== 'urgent') return -1;
        if (b.type === 'urgent' && a.type !== 'urgent') return 1;
        return 0;
      });

      setNotifications(notifList);
    } catch (err) {
      console.warn('Failed to fetch notifications in top bar:', err);
    } finally {
      setLoadingNotifications(false);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000); // Check every 60s
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Global Refresh Handler
  const handleRefresh = async () => {
    setLocalRefreshing(true);
    try {
      if (typeof onRefresh === 'function') {
        await onRefresh();
      }
      window.dispatchEvent(new CustomEvent('app:refresh'));
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

  const markAllAsRead = (e) => {
    if (e) e.stopPropagation();
    const stored = getStoredReadIds(user);
    notifications.forEach((n) => stored.add(n.id));
    storeReadIds(user, stored);
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markAsRead = (id, e) => {
    if (e) e.stopPropagation();
    const stored = getStoredReadIds(user);
    stored.add(id);
    storeReadIds(user, stored);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const handleNotificationClick = (notif) => {
    markAsRead(notif.id);
    setShowNotifications(false);
    if (notif.link) {
      navigate(notif.link);
    }
  };

  const handleFooterQueueClick = () => {
    setShowNotifications(false);
    if (user?.role === 'technician') {
      navigate('/technician/my-tickets');
    } else if (user?.role === 'admin') {
      navigate('/technician/all-tickets');
    } else {
      navigate('/user/dashboard');
    }
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
          {/* Top-Bar Refresh Button */}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold text-gray-700 hover:text-[#00ABE4] bg-gray-50 hover:bg-blue-50/80 border border-gray-200 hover:border-blue-200 transition-all shadow-xs cursor-pointer disabled:opacity-50"
            title="Refresh active tickets & metrics across the system"
          >
            <RefreshCw className={`w-4 h-4 text-[#00ABE4] ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>

          {/* Interactive Notification Bell & Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              type="button"
              id="notification-bell-btn"
              aria-label="Open notifications"
              aria-expanded={showNotifications}
              onClick={() => {
                setShowNotifications((prev) => !prev);
                if (!showNotifications) {
                  fetchNotifications();
                }
              }}
              className={`relative p-2.5 rounded-xl border transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#00ABE4]/40 select-none ${
                showNotifications
                  ? 'bg-blue-50 text-[#00ABE4] border-blue-300 shadow-sm ring-2 ring-blue-100'
                  : 'text-gray-600 hover:text-gray-900 bg-gray-50/90 hover:bg-gray-100 border-gray-200 hover:border-gray-300 shadow-2xs'
              }`}
              title={unreadCount > 0 ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : "Notifications & SLA Alerts"}
            >
              <Bell className={`w-5 h-5 transition-transform duration-200 ${showNotifications ? 'scale-105 text-[#00ABE4]' : ''}`} />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-black text-white shadow-md ring-2 ring-white animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notification Center Popover */}
            {showNotifications && (
              <div 
                className="absolute right-0 mt-2.5 w-80 sm:w-[24rem] max-w-[calc(100vw-2rem)] rounded-2xl bg-white shadow-2xl border border-gray-200/90 z-50 overflow-hidden transform transition-all duration-200 animate-in fade-in slide-in-from-top-2"
                role="dialog"
                aria-label="Notification Center"
              >
                {/* Popover Header */}
                <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950 p-4 text-white flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="w-7 h-7 rounded-lg bg-blue-500/20 border border-blue-400/30 flex items-center justify-center">
                      <Bell className="w-4 h-4 text-[#00ABE4]" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold tracking-tight leading-tight">Notifications</h3>
                      <p className="text-[10px] text-gray-300">Live SLA & Ticket Alerts</p>
                    </div>
                    {unreadCount > 0 && (
                      <span className="ml-1 bg-[#00ABE4] text-white text-[10px] font-extrabold px-2 py-0.5 rounded-full shadow-xs">
                        {unreadCount} New
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        fetchNotifications();
                      }}
                      className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                      title="Refresh notifications"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${loadingNotifications ? 'animate-spin text-[#00ABE4]' : ''}`} />
                    </button>
                    {unreadCount > 0 && (
                      <button
                        type="button"
                        onClick={markAllAsRead}
                        className="flex items-center space-x-1 text-[11px] bg-white/10 hover:bg-white/20 text-blue-200 hover:text-white px-2 py-1 rounded-lg font-medium transition-colors cursor-pointer"
                        title="Mark all notifications as read"
                      >
                        <CheckCheck className="w-3 h-3" />
                        <span>Read all</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setShowNotifications(false)}
                      className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                      aria-label="Close notifications"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center border-b border-gray-100 bg-gray-50/90 px-3 py-1.5 text-xs font-semibold text-gray-600 gap-1.5">
                  <button
                    type="button"
                    onClick={() => setActiveTab('all')}
                    className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                      activeTab === 'all'
                        ? 'bg-white text-[#00ABE4] shadow-xs font-bold border border-gray-200/80'
                        : 'hover:text-gray-900 hover:bg-gray-100/60'
                    }`}
                  >
                    All ({notifications.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('urgent')}
                    className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                      activeTab === 'urgent'
                        ? 'bg-red-50 text-red-600 shadow-xs font-bold border border-red-200/80'
                        : 'hover:text-red-600 hover:bg-red-50/50'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                    <span>Urgent & Alerts</span>
                    {urgentCount > 0 && (
                      <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold leading-tight">
                        {urgentCount}
                      </span>
                    )}
                  </button>
                </div>

                {/* Notification Items List */}
                <div className="max-h-80 overflow-y-auto divide-y divide-gray-100/80">
                  {loadingNotifications && notifications.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#00ABE4] mb-2" />
                      <p className="text-xs font-medium">Loading notifications...</p>
                    </div>
                  ) : filteredNotifications.length === 0 ? (
                    <div className="p-8 text-center text-gray-400">
                      <Inbox className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                      <p className="text-xs font-semibold text-gray-700">All caught up!</p>
                      <p className="text-[11px] text-gray-400 mt-0.5">
                        {activeTab === 'urgent' ? 'No urgent SLA breaches or critical alerts.' : 'No new notifications right now.'}
                      </p>
                    </div>
                  ) : (
                    filteredNotifications.map((notif) => (
                      <div
                        key={notif.id}
                        onClick={() => handleNotificationClick(notif)}
                        className={`p-3.5 hover:bg-blue-50/50 transition-colors cursor-pointer flex items-start space-x-3 group relative ${
                          !notif.read ? 'bg-blue-50/35' : 'bg-white'
                        }`}
                      >
                        {/* Icon Indicator */}
                        <div className="mt-0.5 flex-shrink-0">
                          {notif.type === 'urgent' ? (
                            <div className="w-7 h-7 rounded-lg bg-red-100 text-red-600 flex items-center justify-center shadow-xs">
                              <AlertTriangle className="w-4 h-4" />
                            </div>
                          ) : notif.type === 'resolved' ? (
                            <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center shadow-xs">
                              <CheckCircle2 className="w-4 h-4" />
                            </div>
                          ) : notif.type === 'system' ? (
                            <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center shadow-xs">
                              <Bot className="w-4 h-4" />
                            </div>
                          ) : (
                            <div className="w-7 h-7 rounded-lg bg-blue-100 text-[#00ABE4] flex items-center justify-center shadow-xs">
                              <Clock className="w-4 h-4" />
                            </div>
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0 pr-6">
                          <div className="flex items-center justify-between gap-1">
                            <p className="text-xs font-bold text-gray-900 truncate group-hover:text-[#00ABE4] transition-colors">
                              {notif.title}
                            </p>
                          </div>
                          <p className="text-[11px] text-gray-600 mt-0.5 line-clamp-2 leading-relaxed">
                            {notif.subtitle}
                          </p>
                          <div className="flex items-center justify-between mt-1.5 text-[10px] text-gray-400 font-medium">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-gray-300" />
                              {notif.time}
                            </span>
                            <span className="text-[#00ABE4] flex items-center gap-0.5 font-semibold group-hover:underline">
                              View Details <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
                            </span>
                          </div>
                        </div>

                        {/* Quick Action: Mark read button & unread indicator */}
                        <div className="absolute top-3.5 right-3 flex items-center space-x-1">
                          {!notif.read && (
                            <button
                              type="button"
                              onClick={(e) => markAsRead(notif.id, e)}
                              className="p-1 rounded-md text-gray-400 hover:text-[#00ABE4] hover:bg-blue-100/60 transition-colors"
                              title="Mark as read"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {!notif.read && (
                            <span className="w-2 h-2 rounded-full bg-[#00ABE4] flex-shrink-0 animate-pulse"></span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Popover Footer Action */}
                <div className="bg-gray-50/90 border-t border-gray-100 p-2.5 px-4 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-gray-500 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Live AutoTask Alert Engine
                  </span>
                  <button
                    type="button"
                    onClick={handleFooterQueueClick}
                    className="text-[#00ABE4] hover:text-blue-700 font-bold transition-colors cursor-pointer text-xs flex items-center gap-1"
                  >
                    <span>
                      {user?.role === 'technician' ? 'View My Tickets Queue' : user?.role === 'admin' ? 'View All Tickets' : 'View My Tickets'}
                    </span>
                    <ChevronRight className="w-3.5 h-3.5" />
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
              <p className="text-[10px] text-gray-500 leading-none">
                {user?.full_name || user?.username || 'Active User'}
              </p>
            </div>
          </div>

          {/* Logout Button */}
          <button
            type="button"
            onClick={handleLogout}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold text-gray-600 hover:text-red-600 bg-gray-50 hover:bg-red-50 border border-gray-200 hover:border-red-200 transition-all shadow-xs cursor-pointer disabled:opacity-50"
            title="Sign out of system"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden md:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;