import React, { useState } from 'react';

// Simple password strength function
function passwordStrength(password) {
  if (password.length > 8 && /[A-Z]/.test(password) && /\d/.test(password)) {
    return 'Strong';
  }
  if (password.length > 5) {
    return 'Moderate';
  }
  return 'Weak';
}

export default function Auth({ onLogin }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [role, setRole] = useState('client'); // 'client' or 'coach'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    if (!username || !password) {
      setError('Username and password are required.');
      return;
    }

    if (isSignUp && passwordStrength(password) === 'Weak') {
      setError('Password is too weak.');
      return;
    }

    // Mock authentication - replace with backend call in production
    onLogin({ username, role });
  };

  return (
    <div style={{ maxWidth: '400px', margin: 'auto', backgroundColor: '#daf2d1', padding: '1rem', borderRadius: '8px' }}>
      <h2>{isSignUp ? 'Sign Up' : 'Login'}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Username:
          <input
            style={{ width: '100%', padding: '0.5rem', margin: '0.5rem 0' }}
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />
        </label>
        <label>
          Password:
          <input
            style={{ width: '100%', padding: '0.5rem', margin: '0.5rem 0' }}
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
        </label>
        {isSignUp && (
          <>
            <p>Password strength: <strong>{passwordStrength(password)}</strong></p>
            <label>
              Role:
              <select value={role} onChange={e => setRole(e.target.value)} style={{ marginLeft: '0.5rem' }}>
                <option value="client">Client</option>
                <option value="coach">Coach / Support</option>
              </select>
            </label>
          </>
        )}
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button
          type="submit"
          style={{ padding: '0.5rem 1rem', marginTop: '1rem', backgroundColor: '#93c572', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {isSignUp ? 'Create Account' : 'Login'}
        </button>
      </form>
      <p style={{ marginTop: '1rem' }}>
        {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
        <button
          onClick={() => { setIsSignUp(!isSignUp); setError(null); }}
          style={{ background: 'none', border: 'none', color: '#509934', cursor: 'pointer', textDecoration: 'underline' }}
        >
          {isSignUp ? 'Login' : 'Sign Up'}
        </button>
      </p>
    </div>
  );
}
