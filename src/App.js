import React, { useState } from 'react';
import Auth from './Auth';

// Placeholder components
function PhotoUpload() { return <div><h2>Photo Upload</h2><p>Meal photos and ratings.</p></div>; }
function MoodTracker() { return <div><h2>Mood Tracker</h2><p>Track mood and journaling.</p></div>; }
function BarcodeScanner() { return <div><h2>Barcode Scanner</h2><p>Scan barcodes for nutrition.</p></div>; }
function SupportDashboard() { return <div><h2>Support Dashboard</h2><p>Coaches' client insights.</p></div>; }
function Profile() { return <div><h2>Profile</h2><p>Manage your profile.</p></div>; }

function Navbar({ currentPage, setCurrentPage, userRole }) {
  return (
    <nav style={{padding: '1rem', backgroundColor: '#d0f0c0'}}>
      {['Photo Upload', 'Mood Tracker', 'Barcode Scanner', 'Profile'].map(page => (
        <button key={page} onClick={() => setCurrentPage(page)}
          style={{
            marginRight: '1rem',
            padding: '0.5rem 1rem',
            backgroundColor: currentPage === page ? '#78c850' : '#a3d9a5',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}>{page}</button>
      ))}
      {userRole === 'coach' && (
        <button onClick={() => setCurrentPage('Support Dashboard')} 
          style={{
            backgroundColor: currentPage === 'Support Dashboard' ? '#78c850' : '#a3d9a5',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}>Support Dashboard</button>
      )}
    </nav>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('Photo Upload');

  if (!user) return <Auth onLogin={setUser} />;

  let content;
  if (user.role === 'client') {
    switch(currentPage) {
      case 'Mood Tracker': content = <MoodTracker />; break;
      case 'Barcode Scanner': content = <BarcodeScanner />; break;
      case 'Profile': content = <Profile />; break;
      default: content = <PhotoUpload />;
    }
  } else if (user.role === 'coach') {
    switch(currentPage) {
      case 'Support Dashboard': content = <SupportDashboard />; break;
      case 'Profile': content = <Profile />; break;
      default: content = <PhotoUpload />;
    }
  }

  return (
    <div style={{fontFamily: 'Arial, sans-serif', backgroundColor: user.role === 'coach' ? '#d9f0db' : '#e6f4d4', minHeight: '100vh'}}>
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} userRole={user.role} />
      <main style={{padding: '1rem', maxWidth: user.role === 'coach' ? '900px' : '800px', margin: 'auto'}}>
        <h1>Welcome, {user.username} ({user.role.charAt(0).toUpperCase() + user.role.slice(1)})</h1>
        {content}
        <button onClick={() => setUser(null)} style={{marginTop: '1rem'}}>Logout</button>
      </main>
    </div>
  );
}
