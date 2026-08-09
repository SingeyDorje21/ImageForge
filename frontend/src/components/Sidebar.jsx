import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Layers, LogOut, Home } from 'lucide-react';

const Sidebar = () => {
  const handleLogout = () => {
    localStorage.removeItem('imageforge_token');
    window.location.href = '/';
  };

  return (
    <div className="w-64 bg-panel border-r border-border h-full flex flex-col pt-6 pb-6 px-4 shrink-0">
      <div className="mb-10 px-2">
        <h1 className="text-2xl font-black tracking-tighter text-white">
          IMAGEFLOW <span className="text-primary">ADMIN</span>
        </h1>
      </div>

      <nav className="flex-1 space-y-2">
        <NavLink to="/admin" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={20} />
          Overview
        </NavLink>
        <NavLink to="/admin/queue" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Layers size={20} />
          Queue Monitor
        </NavLink>
        <NavLink to="/" className="nav-item">
          <Home size={20} />
          Public Site
        </NavLink>
      </nav>

      <div className="mt-auto border-t border-border pt-4">
        <button onClick={handleLogout} className="nav-item w-full justify-start text-danger hover:bg-danger/10 hover:text-danger">
          <LogOut size={20} />
          Sign Out
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
