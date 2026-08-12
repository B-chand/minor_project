import React from 'react';
import { AIPage } from './pages/AIPage';
import { ChatbotPage } from './pages/ChatbotPage';
import { AIInsightsPage } from './pages/AIInsightsPage';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { MainLayout } from './components/layout/MainLayout';

import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProductsPage } from './pages/ProductsPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { InventoryPage } from './pages/InventoryPage';
import { CustomersPage } from './pages/CustomersPage';
import { SuppliersPage } from './pages/SuppliersPage';
import { PurchasesPage } from './pages/PurchasesPage';
import { SalesPage } from './pages/SalesPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { ReportsPage } from './pages/ReportsPage';
import { StaffPage } from './pages/StaffPage';
import { BusinessPage } from './pages/BusinessPage';

export function App() {
  return (
    <Router>
      <NotificationProvider>
        <AuthProvider>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/products" element={<ProductsPage />} />
             <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/customers" element={<CustomersPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
            <Route path="/purchases" element={<PurchasesPage />} />
            <Route path="/sales" element={<SalesPage />} />
           <Route path="/notifications" element={<NotificationsPage />} />

           {/* AI Chat — available to all authenticated users */}
          <Route path="/ai-assistant" element={<ChatbotPage />} />

            {/* Admin Only */}
         <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/reports" element={<ReportsPage />} />

           {/* AI (admin modules) */}
          <Route path="/ai" element={<AIPage />} />
          <Route path="/ai-insights" element={<AIInsightsPage />} />

         <Route path="/staff" element={<StaffPage />} />
         <Route path="/business" element={<BusinessPage />} />
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Route>

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </NotificationProvider>
    </Router>
  );
}

export default App;
