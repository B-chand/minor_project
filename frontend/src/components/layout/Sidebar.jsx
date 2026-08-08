import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Layers,
  Boxes,
  Users,
  Truck,
  ShoppingBag,
  ShoppingCart,
  Bell,
  BarChart3,
  UserCheck,
  Building2,
  Cpu,
  MessageSquare,
  FileText,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar = () => {
  const { user, hasRole } = useAuth();

  const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Products', path: '/products', icon: Package },
  { label: 'Categories', path: '/categories', icon: Layers },
  { label: 'Inventory', path: '/inventory', icon: Boxes },
  { label: 'Customers', path: '/customers', icon: Users },
  { label: 'Suppliers', path: '/suppliers', icon: Truck },
  { label: 'Purchases', path: '/purchases', icon: ShoppingBag },
  { label: 'Sales', path: '/sales', icon: ShoppingCart },
  { label: 'Notifications', path: '/notifications', icon: Bell },
  { label: 'Reports', path: '/reports', icon: BarChart3 },
  { label: 'AI Assistant', path: '/ai', icon: Cpu },
  { label: 'AI Chat', path: '/ai-assistant', icon: MessageSquare },
  { label: 'AI Insights', path: '/ai-insights', icon: FileText },
];

  const adminItems = [
    { label: 'Staff Management', path: '/staff', icon: UserCheck },
    { label: 'Business Settings', path: '/business', icon: Building2 },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Cpu size={22} />
        </div>
        <div>
          <div className="sidebar-logo-text">SmartInventory</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
            {user?.organization || 'Multi-Tenant OS'}
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Core Operations</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        {hasRole(['ADMIN', 'SUPER_ADMIN']) && (
          <>
            <div className="nav-section-title" style={{ marginTop: '1rem' }}>
              Administration
            </div>
            {adminItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `nav-item ${isActive ? 'active' : ''}`
                  }
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </>
        )}
      </nav>
    </aside>
  );
};
