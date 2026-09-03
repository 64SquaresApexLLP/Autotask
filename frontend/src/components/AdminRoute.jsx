import React from 'react';
import { Navigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

/**
 * Admin-only route guard. ProtectedRoute only checks that a user is logged
 * in (no role check) — this wrapper adds the role check on top of it, for
 * routes that must be admin-only. Non-admin authenticated users are sent to
 * their own dashboard rather than the login page; unauthenticated users are
 * sent to login. The real enforcement is server-side (require_admin on the
 * API), this just avoids rendering the page/flashing content for non-admins.
 */
const AdminRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" />;
  if (user.role !== 'admin') return <Navigate to="/" />;
  return children;
};

export default AdminRoute;
