import React, { useState } from 'react';

// Simple navigation component
function Navbar({ currentPage, setCurrentPage }) {
  return (
    <nav style={{ padding: '1rem', backgroundColor: '#d0f0c0' }}>
      {['Photo Upload', 'Mood Tracker', 'Barcode Scanner', 'Client Dashboard', 'Support Dashboard', 'Profile'].map(page => (
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
    </nav>
  );
}

// Placeholder components below will be replaced with full-feature implementations
function PhotoUpload() {
  return <div><h2>Photo Upload Demo</h2><p>Component to upload meal photos with descriptions and ratings.</p></div>;
}

function MoodTracker() {
  return <div><h2>Mood Tracker</h2><p>Component to track mood, hunger, satisfaction, and journaling.</p></div>;
}

function BarcodeScanner() {
  return <div><h2>Barcode Scanner</h2><p>Component to scan product barcodes and fetch nutrition info.</p></div>;
}

function ClientDashboard() {
  return <div><h2>Client Dashboard</h2><p>View and manage your meals, mood, profile, and progress.</p></div>;
}

function SupportDashboard() {
  return <div><h2>Support Dashboard</h2><p>Coaches view client data, analytics, and communication tools.</p></div>;
}

function Profile() {
  return <div><h2>Profile</h2><p>Manage your profile, upload pictures, and personal info.</p></div>;
}

export default function App() {
  const [currentPage, setCurrentPage] = useState('Photo Upload');

  let content;
  switch(currentPage) {
    case 'Mood Tracker': content = <MoodTracker />; break;
    case 'Barcode Scanner': content = <BarcodeScanner />; break;
    case 'Client Dashboard': content = <ClientDashboard />; break;
    case 'Support Dashboard': content = <SupportDashboard />; break;
    case 'Profile': content = <Profile />; break;
    default: content = <PhotoUpload />;
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', backgroundColor: '#e6f4d4', minHeight: '100vh' }}>
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <main style={{ padding: '1rem', maxWidth: '800px', margin: 'auto' }}>
        {content}
      </main>
    </div>
  );
}
