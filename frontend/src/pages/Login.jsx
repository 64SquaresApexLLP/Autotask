import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, User, Wrench, Eye, EyeOff, Loader2 } from 'lucide-react';
import useAuth from '../hooks/useAuth';

const Login = () => {
  const { login, loading, error: authError, clearError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!username || !password || !role) {
      setError('All fields are required');
      return;
    }

    setError('');
    clearError();

    try {
      await login({ username, password, role });

      // Navigate based on role
      if (role === 'user') {
        navigate('/user');
      } else if (role === 'technician') {
        navigate('/technician');
      }
    } catch (error) {
      setError(error.message || 'Login failed. Please check your credentials.');
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

        {(error || authError) && (
          <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg text-center border border-red-200 text-base">
            {error || authError}
          </div>
        )}

        <div className="space-y-6">
          {/* Enhanced Role Selection */}
          <div className="mb-6">
            <label className="block text-gray-700 mb-4 font-semibold text-base">Select Your Role</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setRole('user')}
                className={`p-4 border-2 rounded-xl flex flex-col items-center transition-all duration-200 ${role === 'user'
                    ? 'border-[#00ABE4] bg-[#E9F1FA] shadow-md'
                    : 'border-gray-200 hover:border-gray-300'
                  }`}
              >
                <div className={`p-3 rounded-full mb-3 ${role === 'user' ? 'bg-[#00ABE4] text-white' : 'bg-gray-100 text-gray-600'
                  }`}>
                  <User className="w-6 h-6" />
                </div>
                <span className={`font-medium ${role === 'user' ? 'text-[#00ABE4]' : 'text-gray-600'
                  }`}>User</span>
              </button>

              <button
                type="button"
                onClick={() => setRole('technician')}
                className={`p-4 border-2 rounded-xl flex flex-col items-center transition-all duration-200 ${role === 'technician'
                    ? 'border-[#00ABE4] bg-[#E9F1FA] shadow-md'
                    : 'border-gray-200 hover:border-gray-300'
                  }`}
              >
                <div className={`p-3 rounded-full mb-3 ${role === 'technician' ? 'bg-[#00ABE4] text-white' : 'bg-gray-100 text-gray-600'
                  }`}>
                  <Wrench className="w-6 h-6" />
                </div>
                <span className={`font-medium ${role === 'technician' ? 'text-[#00ABE4]' : 'text-gray-600'
                  }`}>Technician</span>
              </button>
            </div>
          </div>

          {/* Enhanced Username Field with Floating Label */}
          <div className="relative">
            <input
              type="text"
              placeholder=""
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4] transition text-base peer"
            />
            <label className={`absolute left-4 text-gray-500 transition-all duration-200 bg-white px-1 text-xs ${username ? '-top-2' : 'top-4 peer-focus:-top-2 peer-focus:text-xs peer-focus:text-[#00ABE4]'
              }`}>
              Username
            </label>
          </div>

          <div className="relative mt-6">
            <input
              type={showPassword ? "text" : "password"}
              placeholder=" "
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ABE4] transition text-base peer pr-12"
            />
            <label className={`absolute left-4 text-gray-500 transition-all duration-200 bg-white px-1 text-xs ${password ? '-top-2' : 'top-4 peer-focus:-top-2 peer-focus:text-xs peer-focus:text-[#00ABE4]'
              }`}>
              Password
            </label>
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          {/* Enhanced Login Button */}
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full bg-[#00ABE4] text-white py-4 rounded-lg font-semibold transition-all duration-300 shadow-md hover:shadow-lg hover:bg-blue-600 text-base transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {loading ? (
              <div className="flex items-center justify-center space-x-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Signing In...</span>
              </div>
            ) : (
              'Sign In'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;