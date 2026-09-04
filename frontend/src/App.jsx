import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard';
import TechnicianDashboard from './pages/TechnicianDashboard';
import TrackStatus from './pages/TrackStatus';
import UserProfile from './pages/UserProfile';
import MttrReport from './pages/MttrReport';
import MyTickets from './pages/techPages/MyTickets';
// import UrgentTickets from './pages/techPages/UrgentTickets'; // Removed: urgent tickets are shown on My Tickets page
import Analytics from './pages/techPages/Analytics';
import AllTickets from './pages/techPages/AllTickets';
import ViewTicket from './pages/techPages/ViewTicket';
import NetworkOntology from './pages/techPages/NetworkOntology';
import AdminDashboard from './pages/adminPages/AdminDashboard';
import AdminTechnicians from './pages/adminPages/AdminTechnicians';
import AdminUsers from './pages/adminPages/AdminUsers';
import AdminTicketsReport from './pages/adminPages/AdminTicketsReport';
import AdminWiderMttr from './pages/adminPages/AdminWiderMttr';
import AdminOntTruckRoll from './pages/adminPages/AdminOntTruckRoll';
import AdminRoute from './components/AdminRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />

          {/* User Routes */}
          <Route
            path="/user"
            element={
              <ProtectedRoute>
                <UserDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/user/dashboard"
            element={
              <ProtectedRoute>
                <UserDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/user/track-status"
            element={
              <ProtectedRoute>
                <TrackStatus />
              </ProtectedRoute>
            }
          />

          <Route
            path="/user/mttr-report"
            element={
              <ProtectedRoute>
                <MttrReport />
              </ProtectedRoute>
            }
          />

          <Route
            path="/user/profile"
            element={
              <ProtectedRoute>
                <UserProfile />
              </ProtectedRoute>
            }
          />

          {/* Technician Routes */}
          <Route
            path="/technician"
            element={
              <ProtectedRoute>
                <TechnicianDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/technician/dashboard"
            element={
              <ProtectedRoute>
                <TechnicianDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/technician/my-tickets"
            element={
              <ProtectedRoute>
                <MyTickets />
              </ProtectedRoute>
            }
          />

          <Route
            path="/technician/my-tickets/view/:ticketId"
            element={
              <ProtectedRoute>
                <ViewTicket />
              </ProtectedRoute>
            }
          />
          {/* Urgent Tickets page removed — urgent (High/Critical) tickets are viewable via My Tickets priority filters */}
          {/* <Route
            path="/technician/urgent-tickets"
            element={
              <ProtectedRoute>
                <UrgentTickets />
              </ProtectedRoute>
            }
          /> */}
          <Route
            path="/technician/mttr-report"
            element={
              <ProtectedRoute>
                <MttrReport />
              </ProtectedRoute>
            }
          />
          <Route
            path="/technician/analytics"
            element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/all-tickets"
            element={
              <AdminRoute>
                <AllTickets />
              </AdminRoute>
            }
          />
          <Route
            path="/technician/ontology"
            element={
              <ProtectedRoute>
                <NetworkOntology />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ontology"
            element={
              <ProtectedRoute>
                <NetworkOntology />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes — AdminRoute enforces role === 'admin' on the frontend;
               backend endpoints all use Depends(require_admin) for real enforcement */}
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/dashboard"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/technicians"
            element={
              <AdminRoute>
                <AdminTechnicians />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <AdminUsers />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/tickets-report"
            element={
              <AdminRoute>
                <AdminTicketsReport />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/wider-mttr"
            element={
              <AdminRoute>
                <AdminWiderMttr />
              </AdminRoute>
            }
          />

          <Route
            path="/admin/ont-truck-roll"
            element={
              <AdminRoute>
                <AdminOntTruckRoll />
              </AdminRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;