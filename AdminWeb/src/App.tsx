/**
 * PURPOSE:
 * Root router for AdminWeb. Defines protected page routes and includes
 *
 * API ENDPOINTS USED:
 * - None directly in this file (routing only).
 */
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './features/auth/LoginPage';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { InventoryPage } from './features/inventory/InventoryPage';
import { TransactionsPage } from './features/transactions/TransactionsPage';
import { ManualTransactionPage } from './features/manual-transaction/ManualTransactionPage';
import { ReportsPage } from './features/reports/ReportsPage';
import { MLDebugPage } from './features/debug/MLDebugPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Dashboard Routes */}
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/manual-transaction" element={<ManualTransactionPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/debug-ml" element={<MLDebugPage />} />
        </Route>

        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App

