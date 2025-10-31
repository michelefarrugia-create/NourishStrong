import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [currentView, setCurrentView] = useState('login');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [meals, setMeals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Login/Register state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('user');

  // Camera state
  const [showCamera, setShowCamera] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [mealNotes, setMealNotes] = useState('');
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // Coach view state
  const [allUsers, setAllUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [userMeals, setUserMeals] = useState([]);
  const [userStats, setUserStats] = useState(null);

  // Check authentication on load
  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      if (user.role === 'coach') {
        fetchAllUsers();
      } else {
        fetchMeals();
      }
    }
  }, [user]);

  // API calls
  const apiCall = async (endpoint, method = 'GET', body = null) => {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
      method,
      headers,
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Request failed');
    }
    
    return response.json();
  };

  const fetchCurrentUser = async () => {
    try {
      const data = await apiCall('/api/auth/me');
      setUser(data);
    } catch (err) {
      console.error('Failed to fetch user:', err);
      logout();
    }
  };

  const fetchMeals = async () => {
    try {
      const data = await apiCall('/api/meals');
      setMeals(data.meals);
    } catch (err) {
      setError('Failed to load meals');
    }
  };

  const fetchAllUsers = async () => {
    try {
      const data = await apiCall('/api/coach/users');
      setAllUsers(data.users);
    } catch (err) {
      setError('Failed to load users');
    }
  };

  const fetchUserMeals = async (userId) => {
    try {
      setLoading(true);
      const data = await apiCall(`/api/coach/users/${userId}/meals`);
      setUserMeals(data.meals);
      
      const stats = await apiCall(`/api/coach/users/${userId}/stats`);
      setUserStats(stats);
    } catch (err) {
      setError('Failed to load user data');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await apiCall('/api/auth/login', 'POST', { email, password });
      setToken(data.token);
      localStorage.setItem('token', data.token);
      setUser(data.user);
      setCurrentView('dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await apiCall('/api/auth/register', 'POST', { email, password, name, role });
      setToken(data.token);
      localStorage.setItem('token', data.token);
      setUser(data.user);
      setCurrentView('dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setCurrentView('login');
  };

  // Camera functions
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' },
        audio: false 
      });
      
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setShowCamera(true);
    } catch (err) {
      setError('Could not access camera. Please check permissions.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setShowCamera(false);
  };

  const capturePhoto = () => {
    if (!canvasRef.current || !videoRef.current) return;
    
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    setCapturedImage(imageData);
    stopCamera();
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onloadend = () => {
      setCapturedImage(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const submitMeal = async () => {
    if (!capturedImage) {
      setError('Please capture or upload a food image');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Remove data:image/jpeg;base64, prefix if present
      const base64Data = capturedImage.split(',')[1] || capturedImage;
      
      const data = await apiCall('/api/meals', 'POST', {
        image_base64: base64Data,
        notes: mealNotes
      });
      
      setSuccess(data.message);
      setCapturedImage(null);
      setMealNotes('');
      fetchMeals();
      
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteMeal = async (mealId) => {
    try {
      await apiCall(`/api/meals/${mealId}`, 'DELETE');
      fetchMeals();
    } catch (err) {
      setError('Failed to delete meal');
    }
  };

  // Render functions
  const renderLogin = () => (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Welcome Back</h1>
        <p className="auth-subtitle">Continue your weight loss journey</p>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleLogin}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-field"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="input-field"
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <p className="auth-switch">
          Don't have an account?
          <button onClick={() => setCurrentView('register')} className="link-button">
            Sign Up
          </button>
        </p>
      </div>
    </div>
  );

  const renderRegister = () => (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Create Account</h1>
        <p className="auth-subtitle">Start your wellness journey today</p>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleRegister}>
          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="input-field"
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-field"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="input-field"
          />
          
          <div className="role-selector">
            <label className="role-label">I am a:</label>
            <div className="role-options">
              <label className={`role-option ${role === 'user' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  value="user"
                  checked={role === 'user'}
                  onChange={(e) => setRole(e.target.value)}
                />
                <span>User</span>
              </label>
              <label className={`role-option ${role === 'coach' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  value="coach"
                  checked={role === 'coach'}
                  onChange={(e) => setRole(e.target.value)}
                />
                <span>Coach/Supporter</span>
              </label>
            </div>
          </div>
          
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        
        <p className="auth-switch">
          Already have an account?
          <button onClick={() => setCurrentView('login')} className="link-button">
            Sign In
          </button>
        </p>
      </div>
    </div>
  );

  const renderUserDashboard = () => (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Your Journey</h1>
          <div className="header-actions">
            <span className="user-name">Hi, {user?.name}!</span>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        {success && <div className="success-message">{success}</div>}
        {error && <div className="error-message">{error}</div>}

        <div className="capture-section">
          <h2 className="section-title">Log Your Meal</h2>
          
          {!capturedImage ? (
            <div className="capture-options">
              <button onClick={startCamera} className="btn-primary">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                  <circle cx="12" cy="13" r="4"></circle>
                </svg>
                Take Photo
              </button>
              
              <label className="btn-secondary upload-label">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                Upload Photo
                <input type="file" accept="image/*" onChange={handleFileUpload} style={{display: 'none'}} />
              </label>
            </div>
          ) : (
            <div className="meal-preview">
              <img src={capturedImage} alt="Captured meal" className="preview-image" />
              <textarea
                placeholder="Add notes about your meal (optional)"
                value={mealNotes}
                onChange={(e) => setMealNotes(e.target.value)}
                className="notes-input"
              />
              <div className="preview-actions">
                <button onClick={submitMeal} className="btn-primary" disabled={loading}>
                  {loading ? 'Analyzing...' : 'Submit Meal'}
                </button>
                <button onClick={() => setCapturedImage(null)} className="btn-secondary">
                  Retake
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="meals-section">
          <h2 className="section-title">Your Meal History</h2>
          <div className="meals-grid">
            {meals.length === 0 ? (
              <p className="empty-state">No meals logged yet. Start by capturing your first meal!</p>
            ) : (
              meals.map((meal) => (
                <div key={meal.meal_id} className="meal-card">
                  <img 
                    src={`data:image/jpeg;base64,${meal.image_base64}`} 
                    alt="Meal" 
                    className="meal-image"
                  />
                  <div className="meal-info">
                    <p className="meal-time">{new Date(meal.timestamp).toLocaleString()}</p>
                    {meal.notes && <p className="meal-notes">{meal.notes}</p>}
                  </div>
                  <button 
                    onClick={() => deleteMeal(meal.meal_id)} 
                    className="delete-button"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Hidden camera elements */}
      <div style={{display: showCamera ? 'block' : 'none'}}>
        {showCamera && (
          <div className="camera-modal">
            <div className="camera-container">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline
                className="camera-video"
              />
              <div className="camera-controls">
                <button onClick={capturePhoto} className="btn-primary">
                  Capture
                </button>
                <button onClick={stopCamera} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      <canvas ref={canvasRef} style={{display: 'none'}} />
    </div>
  );

  const renderCoachDashboard = () => (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Coach Dashboard</h1>
          <div className="header-actions">
            <span className="user-name">Coach {user?.name}</span>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content coach-view">
        <div className="users-sidebar">
          <h2 className="section-title">Your Clients</h2>
          <div className="users-list">
            {allUsers.map((u) => (
              <div 
                key={u.user_id} 
                className={`user-item ${selectedUserId === u.user_id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedUserId(u.user_id);
                  fetchUserMeals(u.user_id);
                }}
              >
                <div className="user-info">
                  <h3>{u.name}</h3>
                  <p>{u.email}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="user-details">
          {selectedUserId ? (
            <>
              {userStats && (
                <div className="stats-section">
                  <h2 className="section-title">Nutrition Stats</h2>
                  <div className="stats-grid">
                    <div className="stat-card">
                      <h3>Total Meals</h3>
                      <p className="stat-value">{userStats.total_meals}</p>
                    </div>
                    <div className="stat-card">
                      <h3>Total Calories</h3>
                      <p className="stat-value">{Math.round(userStats.total_calories)}</p>
                    </div>
                    <div className="stat-card">
                      <h3>Avg Calories/Meal</h3>
                      <p className="stat-value">{Math.round(userStats.avg_calories_per_meal)}</p>
                    </div>
                    <div className="stat-card">
                      <h3>Total Protein</h3>
                      <p className="stat-value">{Math.round(userStats.total_protein)}g</p>
                    </div>
                    <div className="stat-card">
                      <h3>Total Carbs</h3>
                      <p className="stat-value">{Math.round(userStats.total_carbs)}g</p>
                    </div>
                    <div className="stat-card">
                      <h3>Total Fats</h3>
                      <p className="stat-value">{Math.round(userStats.total_fats)}g</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="meals-section">
                <h2 className="section-title">Meal History</h2>
                <div className="meals-grid">
                  {userMeals.map((meal) => (
                    <div key={meal.meal_id} className="meal-card coach-meal-card">
                      <img 
                        src={`data:image/jpeg;base64,${meal.image_base64}`} 
                        alt="Meal" 
                        className="meal-image"
                      />
                      <div className="meal-info">
                        <h4>{meal.nutrition?.food_name || 'Unknown'}</h4>
                        <p className="meal-time">{new Date(meal.timestamp).toLocaleString()}</p>
                        {meal.notes && <p className="meal-notes">{meal.notes}</p>}
                        <div className="nutrition-details">
                          <p><strong>Calories:</strong> {meal.nutrition?.calories || 0}</p>
                          <p><strong>Protein:</strong> {meal.nutrition?.protein || 0}g</p>
                          <p><strong>Carbs:</strong> {meal.nutrition?.carbs || 0}g</p>
                          <p><strong>Fats:</strong> {meal.nutrition?.fats || 0}g</p>
                          <p><strong>Portion:</strong> {meal.nutrition?.portion_size || 'unknown'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>Select a client to view their progress</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Main render
  if (!token) {
    return currentView === 'login' ? renderLogin() : renderRegister();
  }

  if (!user) {
    return <div className="loading">Loading...</div>;
  }

  return user.role === 'coach' ? renderCoachDashboard() : renderUserDashboard();
}

export default App;
