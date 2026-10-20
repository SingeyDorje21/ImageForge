import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Layers, LogOut, Home } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

const Sidebar = () => {
  const handleLogout = () => {
    localStorage.removeItem('imageforge_token');
    window.location.href = '/';
  };

  return (
    <aside className="w-60 border-r border-line h-full flex flex-col py-5 px-3 shrink-0 bg-surface">
      <div className="flex items-center justify-between px-3 mb-8">
        <div className="flex items-center gap-2 font-semibold tracking-tight">
          <img src="/favicon.svg" alt="" className="h-6 w-6" />
          ImageForge
        </div>
        <ThemeToggle />
      </div>

      <nav className="flex-1 space-y-1">
        <NavLink to="/admin" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={16} />
          Overview
        </NavLink>
        <NavLink to="/admin/queue" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Layers size={16} />
          Jobs
        </NavLink>
        <NavLink to="/" className="nav-item">
          <Home size={16} />
          Public site
        </NavLink>
      </nav>

      <button onClick={handleLogout} className="nav-item w-full hover:text-danger">
        <LogOut size={16} />
        Sign out
      </button>
    </aside>
  );
};

export default Sidebar;
