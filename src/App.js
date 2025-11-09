import React, { useState } from 'react';
import Auth from './Auth';

// Placeholder components
function PhotoUpload() {
  return <div><h2>Photo Upload</h2><p>Meal photos with descriptions and ratings.</p></div>;
}

function MoodTracker() {
  return <div><h2>Mood Tracker</h2><p>Track mood, hunger, satisfaction, and journaling.</p></div>;
}

function BarcodeScanner() {
  return <div><h2>Barcode Scanner</h2><p>Scan barcodes and fetch nutrition info.</p></div>;
}

function SupportDashboard() {
  return <div><h2>Support Dashboard</h2><p>Coaches view client data, analytics, and communication tools.</p></div>;
}

function Profile() {
  return <div><h2>Profile</h2><p>Manage your profile, upload pictures, and personal info.</p></div>;
}

// Corrected Navbar component that conditionally shows "Support Dashboard" for coaches
function Navbar({ currentPage, setCurrentPage, userRole }) {
  return (
    <nav style={{ padding: '1rem', backgroundColor: '#d0f0c0' }}>
      {['Photo Upload', 'Mood Tracker', 'Barcode Scanner', 'Profile'].map(page => (
        <button
          key={page}
          onClick={() => setCurrentPage(page)}
          style={{
            marginRight: '1rem',
            padding: '0.5rem 1rem',
            backgroundColor: currentPage === page ? '#78c850' : '#a3d9a5',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {page}
        </button>
      ))}
      {userRole === 'coach' && (
        <button
          onClick={() => setCurrentPage('Support Dashboard')}
          style={{
            backgroundColor: currentPage === 'Support Dashboard' ? '#78c850' : '#a3d9a5',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Support Dashboard
        </button>
      )}
    </nav>
  );
}

export default function App() {
  const [user, setUser] = useState(null); // { username, role }
  const [currentPage, setCurrentPage] = useState('Photo Upload');

  if (!user) {
    return <Auth onLogin={setUser} />;
  }

  // Based on user role, render different layouts
  let content;
  if (user.role === 'client') {
    switch (currentPage) {
      case 'Mood Tracker':
        content = <MoodTracker />;
        break;
      case 'Barcode Scanner':
        content = <BarcodeScanner />;
        break;
      case 'Profile':
        content = <Profile />;
        break;
      default:
        content = <PhotoUpload />;
    }

    return (
      <div style={{ fontFamily: 'Arial, sans-serif', backgroundColor: '#e6f4d4', minHeight: '100vh' }}>
        <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} userRole={user.role} />
        <main style={{ padding: '1rem', maxWidth: '800px', margin: 'auto' }}>
          <h1>Welcome, {user.username} (Client)</h1>
          {content}
          <button onClick={() => setUser(null)} style={{ marginTop: '1rem' }}>
            Logout
          </button>
        </main>
      </div>
    );
  }

  else if (user.role === 'coach') {
    switch (currentPage) {
      case 'Support Dashboard':
        content = <SupportDashboard />;
        break;
      case 'Profile':
        content = <Profile />;
        break;
      default:
        content = <PhotoUpload />;
    }

    return (
      <div style={{ fontFamily: 'Arial, sans-serif', backgroundColor: '#d9f0db', minHeight: '100vh' }}>
        <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} userRole={user.role} />
        <main style={{ padding: '1rem', maxWidth: '900px', margin: 'auto' }}>
          <h1>Welcome, {user.username} (Coach)</h1>
          {content}
          <button onClick={() => setUser(null)} style={{ marginTop: '1rem' }}>
            Logout
          </button>
        </main>
      </div>
    );
  }

  return null; // fallback
}
