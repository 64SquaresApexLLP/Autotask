// src/pages/Login.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot } from 'lucide-react';
import useAuth from '../hooks/useAuth';

const Login = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = () => {
    if (!username || !password || !role) {
      setError('All fields are required');
      return;
    }

    setError('');
    login({ username, role });

    if (role === 'user') {
      navigate('/user');
    } else if (role === 'technician') {
      navigate('/technician');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#E9F1FA] to-[#00ABE4] p-6">
      <div className="bg-white shadow-xl rounded-2xl p-8 w-full max-w-md">
        <div className="flex justify-center mb-8">
          <div className="bg-[#00ABE4] p-4 rounded-full">
            <Bot className="w-12 h-12 text-white" />
          </div>
        </div>

        <h2 className="text-3xl font-bold text-center text-gray-800 mb-2">
          Welcome to Autotask
        </h2>
        <p className="text-center text-gray-600 mb-8 text-base">
          Please sign in to continue
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg text-center border border-red-200 text-base">
            {error}
          </div>
        )}

        <div className="space-y-6">
          <div>
            <label className="block text-gray-700 mb-3 font-semibold text-base">Select Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4] transition text-base"
            >
              <option value="">Choose your role</option>
              <option value="user">User</option>
              <option value="technician">Technician</option>
            </select>
          </div>

          <div>
            <label className="block text-gray-700 mb-3 font-semibold text-base">Username</label>
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4] transition text-base"
            />
          </div>

          <div>
            <label className="block text-gray-700 mb-3 font-semibold text-base">Password</label>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4] transition text-base"
            />
          </div>

          <button
            onClick={handleLogin}
            className="w-full bg-[#00ABE4] text-white py-4 rounded-lg font-semibold transition duration-300 shadow-md hover:shadow-lg hover:bg-blue-600 text-base"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;