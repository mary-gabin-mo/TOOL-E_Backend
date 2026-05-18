/**
 * PURPOSE:
 * Shared authenticated layout with sidebar navigation for all admin pages,
 * including entry to the ML debug page.
 *
 * API ENDPOINTS USED:
 * - None directly. `handleSync()` triggers React Query refetch of data,
 *   and endpoint calls happen inside each feature page/query function.
 */
import { useState } from 'react';
import { NavLink, Outlet, useNavigate, Navigate } from 'react-router-dom';
import { LayoutDashboard, Package, ArrowRightLeft, PenTool, FileBarChart, Terminal, LogOut, User, RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { useAuthStore } from '../../lib/authStore';

export const DashboardLayout = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
        // Invalidate all queries to trigger a refetch of active ones
        await queryClient.invalidateQueries();
    } finally {
        // specific timeout to show the animation for a bit
        setTimeout(() => setIsSyncing(false), 1000);
    }
  };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Inventory', path: '/inventory', icon: Package },
    { name: 'Transactions', path: '/transactions', icon: ArrowRightLeft },
    { name: 'Manual Transaction', path: '/manual-transaction', icon: PenTool },
    { name: 'Reports', path: '/reports', icon: FileBarChart },
    { name: 'Access Debug', path: '/debug-ml', icon: Terminal },
  ];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-[#0f172a] text-white flex flex-col flex-shrink-0">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wide">TOOL-E Admin</h1>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* User Info & Logout Footer */}
        <div className="p-4 bg-[#1e293b] border-t border-gray-700 space-y-3">
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="w-full flex items-center px-4 py-2 text-sm font-medium text-blue-400 bg-blue-900/20 hover:bg-blue-900/40 border border-blue-900/50 rounded-md transition-all hover:text-blue-300 disabled:opacity-50"
          >
            <RefreshCw className={clsx("w-4 h-4 mr-2", isSyncing && "animate-spin")} />
            {isSyncing ? 'Syncing...' : 'Sync Data'}
          </button>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-medium text-white truncate">
                {user?.user_name || 'Admin User'}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {user?.email || 'admin@schulich.edu'}
              </p>
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-4 py-2 text-sm font-medium text-red-400 hover:bg-gray-800 hover:text-red-300 rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
