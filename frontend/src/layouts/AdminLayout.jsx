import React from 'react';
import Sidebar from '../components/Sidebar';

const AdminLayout = ({ children, isAuthenticated }) => {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isAuthenticated={isAuthenticated} />
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
};

export default AdminLayout;
