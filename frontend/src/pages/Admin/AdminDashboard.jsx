// frontend/src/pages/Admin/AdminDashboard.jsx
// Admin Dashboard - Entry page with tabs to switch between management pages

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminUserManagement from './AdminUserManagement.jsx';
import AdminKeyManagement from './AdminKeyManagement.jsx';
import styles from './AdminDashboard.module.css';
import { logout } from "../../api/auth";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('users'); // 'users' or 'keys'

  
  
  // Logout handler
  const handleLogout = async () => {

    await logout(); 
    // Clear local storage
    localStorage.removeItem('authUserId');
    localStorage.removeItem('authUsername');
    localStorage.removeItem('authUserRole');

    // Navigate to login page
    navigate('/login',{ replace: true });
  };

  return (
    <div className={styles.container}>
      {/* Top navigation bar */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Admin Dashboard</h1>
          <span className={styles.badge}>Admin Dashboard</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.username}>
            {localStorage.getItem('authUsername') || 'admin'}
          </span>
          <button className={styles.btnLogout} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Tab navigation */}
      <nav className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'users' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <svg className={styles.tabIcon} viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
          </svg>
          User Management
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'keys' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('keys')}
        >
          <svg className={styles.tabIcon} viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
          </svg>
          Batch Generate License Keys
        </button>
      </nav>

      {/* Main content area */}
      <main className={styles.main}>
        {activeTab === 'users' ? <AdminUserManagement /> : <AdminKeyManagement />}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <span>Accent 0</span>
      </footer>
    </div>
  );
}
