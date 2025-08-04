import React from 'react';
import { User, LogOut, Bot, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

const Header = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
      // Still navigate to login page even if logout API fails
      navigate('/');
    }
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left side - App name with icon */}
        <div className="flex items-center space-x-3">
          <Bot className="w-8 h-8 text-[#00ABE4]" />
          <h1 className="text-2xl font-bold text-gray-800">Autotask</h1>
        </div>

        {/* Right side - User info and logout */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3 bg-[#E9F1FA] px-4 py-2 rounded-lg">
            <User className="w-6 h-6 text-[#00ABE4]" />
            <div className="text-right">
              <p className="text-base font-semibold text-gray-800 capitalize">{user?.role}</p>
              <p className="text-sm text-gray-600">{user?.username}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            disabled={loading}
            className="flex items-center space-x-2 text-gray-600 hover:text-red-600 transition-colors p-2 hover:bg-red-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            title="Logout"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
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