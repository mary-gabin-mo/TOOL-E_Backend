/**
 * PURPOSE:
 * Admin authentication page that collects credentials and starts a session.
 *
 * API ENDPOINTS USED:
 * - POST /api/auth/login (via `login()` helper)
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate, Navigate } from 'react-router-dom';
import { login } from './api/login';
import { useAuthStore } from '../../lib/authStore';

export const LoginPage = () => {
  // Local state for form inputs
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const navigate = useNavigate();
  const { login: setAuth, isAuthenticated } = useAuthStore();

  // Redirect if already logged in
  if (isAuthenticated()) {
    return <Navigate to="/dashboard" replace />;
  }

  const loginMutation = useMutation({
    mutationFn: login,
    // Redirect to dashboard only after a successful login API call
    onSuccess: (data) => {
      setAuth(data.user, data.token);
      navigate('/dashboard');
    },
  });

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    // Start login request with the form values
    loginMutation.mutate({ email, password });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white text-black font-sans">
      {/* Header Section */}
      <div className="text-center mb-12">
        <h2 className="text-3xl font-normal mb-1">Schulich</h2>
        <h1 className="text-6xl font-bold tracking-tight mb-2">MAKERSPACE</h1>
        <h3 className="text-2xl font-light">Admin</h3>
      </div>

      {/* Login Form Card */}
      <div className="w-full max-w-md p-8 bg-white rounded-lg border border-gray-100 shadow-sm">
        <form onSubmit={handleLogin} className="space-y-6">

          {/* Email Input */}
          <div>
            <input
              type="text"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-md border border-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-transparent transition-all bg-white text-gray-800 placeholder-gray-400"
            />
          </div>

          {/* Password Input */}
          <div>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-md border border-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-transparent transition-all bg-white text-gray-800 placeholder-gray-400"
            />
          </div>

          {/* Sign In Button */}
          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full py-3 px-4 bg-[#242424] hover:bg-black disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors duration-200"
          >
            {loginMutation.isPending ? 'Signing In...' : 'Sign In'}
          </button>

          {loginMutation.isError && (
            <div className="text-red-500 text-sm text-center mt-2">
              Unable to sign in. Please check your credentials.
            </div>
          )}

        </form>
      </div>
    </div>
  );
};
