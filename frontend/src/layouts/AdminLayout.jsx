import React from 'react';
import Sidebar from '../components/Sidebar';

const AdminLayout = ({ children, isAuthenticated }) => {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar isAuthenticated={isAuthenticated} />
      <div className="flex-1 overflow-auto p-8 relative">
        {children}
      </div>
    </div>
  );
};

export default AdminLayout;
