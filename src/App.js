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
