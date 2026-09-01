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
import UrgentTickets from './pages/techPages/UrgentTickets';
import Analytics from './pages/techPages/Analytics';
import AllTickets from './pages/techPages/AllTickets';
import ViewTicket from './pages/techPages/ViewTicket';
import NetworkOntology from './pages/techPages/NetworkOntology';
import AdminDashboard from './pages/adminPages/AdminDashboard';
import AdminTechnicians from './pages/adminPages/AdminTechnicians';
import AdminUsers from './pages/adminPages/AdminUsers';
import AdminTicketsReport from './pages/adminPages/AdminTicketsReport';
import AdminWiderMttr from './pages/adminPages/AdminWiderMttr';

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
          <Route
            path="/technician/urgent-tickets"
            element={
              <ProtectedRoute>
                <UrgentTickets />
              </ProtectedRoute>
            }
          />
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
            path="/technician/all-tickets"
            element={
              <ProtectedRoute>
                <AllTickets />
              </ProtectedRoute>
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

          {/* Admin Routes */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/technicians"
            element={
              <ProtectedRoute>
                <AdminTechnicians />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <AdminUsers />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/tickets-report"
            element={
              <ProtectedRoute>
                <AdminTicketsReport />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/wider-mttr"
            element={
              <ProtectedRoute>
                <AdminWiderMttr />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;