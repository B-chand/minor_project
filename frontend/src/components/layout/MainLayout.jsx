import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const MOBILE_QUERY = '(max-width: 960px)';

export const MainLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() =>
    window.matchMedia(MOBILE_QUERY).matches
  );

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY);
    const handleChange = (e) => {
      setIsMobile(e.matches);
      if (!e.matches) setMobileOpen(false);
    };
    mq.addEventListener('change', handleChange);
    return () => mq.removeEventListener('change', handleChange);
  }, []);

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileOpen((open) => !open);
    } else {
      setSidebarOpen((open) => !open);
    }
  };

  const closeMobileSidebar = () => setMobileOpen(false);

  const desktopHidden = !isMobile && !sidebarOpen;

  const containerClass = [
    'app-container',
    desktopHidden ? 'sidebar-hidden' : '',
    isMobile ? 'sidebar-mobile' : '',
    isMobile && mobileOpen ? 'sidebar-mobile-open' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClass}>
      {isMobile && mobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeMobileSidebar}
          aria-hidden="true"
        />
      )}
      <div className="sidebar-rail">
        <Sidebar onNavigate={closeMobileSidebar} />
      </div>
      {!isMobile && (
        <button
          className="sidebar-slide-control"
          onClick={toggleSidebar}
          title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
        >
          {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      )}
      <div className="main-content">
        <Header onToggleSidebar={toggleSidebar} isMobile={isMobile} />
        <main className="page-container">
          <Outlet />
        </main>
      </div>
    </div>
  );
};