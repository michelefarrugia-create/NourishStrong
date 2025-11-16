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

  // Profile state
  const [showProfile, setShowProfile] = useState(false);
  const [profileData, setProfileData] = useState({
    age: '',
    gender: '',
    height: '',
    weight: '',
    activity_level: '',
    goal_weight: ''
  });

  // Coach assignment state
  const [showCoachAssignment, setShowCoachAssignment] = useState(false);
  const [coachEmail, setCoachEmail] = useState('');

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
  const [selectedUserInfo, setSelectedUserInfo] = useState(null);

  // Gamification state
  const [streak, setStreak] = useState({ current_streak: 0, streak_record: 0 });
  const [badges, setBadges] = useState({ earned_badges: [], all_badges: [], total_earned: 0, total_available: 0 });
  const [dailyChallenge, setDailyChallenge] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [progressPhotos, setProgressPhotos] = useState([]);
  const [showProgressPhotos, setShowProgressPhotos] = useState(false);
  const [showBadges, setShowBadges] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [newBadgesCelebration, setNewBadgesCelebration] = useState([]);
  const [capturedProgressPhoto, setCapturedProgressPhoto] = useState(null);
  const [progressPhotoWeight, setProgressPhotoWeight] = useState('');
  const [progressPhotoNotes, setProgressPhotoNotes] = useState('');
  const [dailyQuote, setDailyQuote] = useState(null);
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeResult, setBarcodeResult] = useState(null);
  const [scanningBarcode, setScanningBarcode] = useState(false);
  
  // Activity tracking state
  const [showActivityLogger, setShowActivityLogger] = useState(false);
  const [activityTypes, setActivityTypes] = useState([]);
  const [activities, setActivities] = useState([]);
  const [activityStats, setActivityStats] = useState(null);
  const [activityForm, setActivityForm] = useState({
    activity_type: 'walking',
    duration_minutes: '',
    intensity: 'moderate',
    notes: ''
  });
  const [showHealthImport, setShowHealthImport] = useState(false);
  const [importingHealth, setImportingHealth] = useState(false);

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
        fetchGameificationData();
        fetchAnalytics();
        fetchProgressPhotos();
        fetchActivityTypes();
        fetchActivities();
        fetchActivityStats();
        // Load profile data
        if (user.profile) {
          setProfileData({
            age: user.profile.age || '',
            gender: user.profile.gender || '',
            height: user.profile.height || '',
            weight: user.profile.weight || '',
            activity_level: user.profile.activity_level || '',
            goal_weight: user.profile.goal_weight || ''
          });
        }
      }
    }
  }, [user]);

  const fetchActivityTypes = async () => {
    try {
      const data = await apiCall('/api/activities/types');
      setActivityTypes(data.activities);
    } catch (err) {
      console.error('Failed to load activity types:', err);
    }
  };

  const fetchActivities = async () => {
    try {
      const data = await apiCall('/api/activities');
      setActivities(data.activities);
    } catch (err) {
      console.error('Failed to load activities:', err);
    }
  };

  const fetchActivityStats = async () => {
    try {
      const data = await apiCall('/api/activities/stats');
      setActivityStats(data);
    } catch (err) {
      console.error('Failed to load activity stats:', err);
    }
  };

  const fetchGameificationData = async () => {
    try {
      const streakData = await apiCall('/api/gamification/streak');
      setStreak(streakData);

      const badgesData = await apiCall('/api/gamification/badges');
      setBadges(badgesData);

      const challengeData = await apiCall('/api/gamification/challenge');
      setDailyChallenge(challengeData);

      const quoteData = await apiCall('/api/gamification/quote');
      setDailyQuote(quoteData);
    } catch (err) {
      console.error('Failed to load gamification data:', err);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const data = await apiCall('/api/analytics/overview');
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  };

  const fetchProgressPhotos = async () => {
    try {
      const data = await apiCall('/api/progress-photos');
      setProgressPhotos(data.photos);
    } catch (err) {
      console.error('Failed to load progress photos:', err);
    }
  };

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
      setSelectedUserInfo(data.user);
      
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

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const profileToSend = {};
      Object.keys(profileData).forEach(key => {
        if (profileData[key] !== '') {
          profileToSend[key] = profileData[key];
        }
      });

      await apiCall('/api/profile', 'PUT', profileToSend);
      setSuccess('Profile updated successfully!');
      setShowProfile(false);
      fetchCurrentUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignCoach = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const data = await apiCall('/api/assign-coach', 'POST', { coach_email: coachEmail });
      setSuccess(data.message);
      setShowCoachAssignment(false);
      setCoachEmail('');
      fetchCurrentUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveCoach = async () => {
    if (!window.confirm('Are you sure you want to remove your coach?')) return;
    
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const data = await apiCall('/api/remove-coach', 'DELETE');
      setSuccess(data.message);
      fetchCurrentUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadProgressPhoto = async () => {
    if (!capturedProgressPhoto) {
      setError('Please capture or upload a progress photo');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const base64Data = capturedProgressPhoto.split(',')[1] || capturedProgressPhoto;
      
      await apiCall('/api/progress-photos', 'POST', {
        image_base64: base64Data,
        weight: progressPhotoWeight ? parseFloat(progressPhotoWeight) : null,
        notes: progressPhotoNotes
      });
      
      setSuccess('Progress photo uploaded!');
      setCapturedProgressPhoto(null);
      setProgressPhotoWeight('');
      setProgressPhotoNotes('');
      fetchProgressPhotos();
      setShowProgressPhotos(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteProgressPhoto = async (photoId) => {
    try {
      await apiCall(`/api/progress-photos/${photoId}`, 'DELETE');
      fetchProgressPhotos();
    } catch (err) {
      setError('Failed to delete progress photo');
    }
  };

  const handleCompleteChallenge = async () => {
    if (!dailyChallenge) return;
    
    try {
      await apiCall('/api/gamification/challenge/complete', 'POST', {
        challenge_id: dailyChallenge.challenge_id
      });
      setSuccess('Challenge completed! 🎉');
      fetchGameificationData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleBarcodeScann = async () => {
    if (!barcodeInput || barcodeInput.length < 8) {
      setError('Please enter a valid barcode (at least 8 digits)');
      return;
    }

    setScanningBarcode(true);
    setError('');

    try {
      const data = await apiCall('/api/barcode-scan', 'POST', {
        barcode: barcodeInput
      });

      if (data.success) {
        setBarcodeResult(data.product);
        setSuccess(`Found: ${data.product.food_name}!`);
      } else {
        setError(data.message);
        setBarcodeResult(null);
      }
    } catch (err) {
      setError('Failed to scan barcode. Please try again.');
      setBarcodeResult(null);
    } finally {
      setScanningBarcode(false);
    }
  };

  const addBarcodeProduct = () => {
    if (!barcodeResult) return;

    // Create a virtual image for the barcode product
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 300;
    const ctx = canvas.getContext('2d');
    
    // Create a simple placeholder image
    ctx.fillStyle = '#f3f4f6';
    ctx.fillRect(0, 0, 400, 300);
    ctx.fillStyle = '#1f2937';
    ctx.font = '24px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(barcodeResult.food_name, 200, 150);
    ctx.font = '16px Arial';
    ctx.fillText(barcodeResult.brand || 'Scanned Product', 200, 180);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    setCapturedImage(imageData);
    setShowBarcodeScanner(false);
    setBarcodeInput('');
    setBarcodeResult(null);
  };

  const handleLogActivity = async (e) => {
    e.preventDefault();
    
    if (!activityForm.duration_minutes || activityForm.duration_minutes <= 0) {
      setError('Please enter a valid duration');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const data = await apiCall('/api/activities', 'POST', {
        activity_type: activityForm.activity_type,
        duration_minutes: parseInt(activityForm.duration_minutes),
        intensity: activityForm.intensity,
        notes: activityForm.notes
      });

      setSuccess(data.message);
      setShowActivityLogger(false);
      setActivityForm({
        activity_type: 'walking',
        duration_minutes: '',
        intensity: 'moderate',
        notes: ''
      });
      
      fetchActivities();
      fetchActivityStats();
      fetchGameificationData();

      // Check for new badges
      if (data.new_badges && data.new_badges.length > 0) {
        setNewBadgesCelebration(data.new_badges);
        setTimeout(() => setNewBadgesCelebration([]), 5000);
      }

      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteActivity = async (activityId) => {
    try {
      await apiCall(`/api/activities/${activityId}`, 'DELETE');
      fetchActivities();
      fetchActivityStats();
    } catch (err) {
      setError('Failed to delete activity');
    }
  };

  const handleHealthFileImport = async (e, fileType) => {
    const file = e.target.files[0];
    if (!file) return;

    setImportingHealth(true);
    setError('');
    setSuccess('');

    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Content = reader.result.split(',')[1];
        
        const data = await apiCall('/api/activities/import', 'POST', {
          file_type: fileType,
          file_content: base64Content
        });

        if (data.success) {
          setSuccess(data.message);
          setShowHealthImport(false);
          fetchActivities();
          fetchActivityStats();
          fetchGameificationData();

          // Check for new badges
          if (data.new_badges && data.new_badges.length > 0) {
            setNewBadgesCelebration(data.new_badges);
            setTimeout(() => setNewBadgesCelebration([]), 5000);
          }
        } else {
          setError(data.message);
        }

        setImportingHealth(false);
      };

      reader.readAsDataURL(file);
    } catch (err) {
      setError(err.message);
      setImportingHealth(false);
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
      fetchGameificationData();
      fetchAnalytics();
      
      // Check for new badges and celebrations
      if (data.new_badges && data.new_badges.length > 0) {
        setNewBadgesCelebration(data.new_badges);
        setTimeout(() => setNewBadgesCelebration([]), 5000);
      }
      
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
        <div className="brand-header">
          <h1 className="auth-title">NourishStrong</h1>
          <p className="brand-tagline">Your Journey to Wellness</p>
        </div>
        <p className="auth-subtitle">Continue your wellness journey</p>
        
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
        <div className="brand-header">
          <h1 className="auth-title">NourishStrong</h1>
          <p className="brand-tagline">Your Journey to Wellness</p>
        </div>
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

  const renderProfileModal = () => (
    <div className="modal-overlay" onClick={() => setShowProfile(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Update Profile</h2>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <form onSubmit={handleUpdateProfile}>
          <input
            type="number"
            placeholder="Age"
            value={profileData.age}
            onChange={(e) => setProfileData({...profileData, age: e.target.value})}
            className="input-field"
          />
          
          <select
            value={profileData.gender}
            onChange={(e) => setProfileData({...profileData, gender: e.target.value})}
            className="input-field"
          >
            <option value="">Select Gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
          
          <input
            type="number"
            step="0.1"
            placeholder="Height (cm)"
            value={profileData.height}
            onChange={(e) => setProfileData({...profileData, height: e.target.value})}
            className="input-field"
          />
          
          <input
            type="number"
            step="0.1"
            placeholder="Current Weight (kg)"
            value={profileData.weight}
            onChange={(e) => setProfileData({...profileData, weight: e.target.value})}
            className="input-field"
          />
          
          <select
            value={profileData.activity_level}
            onChange={(e) => setProfileData({...profileData, activity_level: e.target.value})}
            className="input-field"
          >
            <option value="">Select Activity Level</option>
            <option value="sedentary">Sedentary (little or no exercise)</option>
            <option value="light">Lightly active (1-3 days/week)</option>
            <option value="moderate">Moderately active (3-5 days/week)</option>
            <option value="very">Very active (6-7 days/week)</option>
            <option value="extra">Extra active (athlete)</option>
          </select>
          
          <input
            type="number"
            step="0.1"
            placeholder="Goal Weight (kg)"
            value={profileData.goal_weight}
            onChange={(e) => setProfileData({...profileData, goal_weight: e.target.value})}
            className="input-field"
          />
          
          <div className="modal-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Profile'}
            </button>
            <button type="button" onClick={() => setShowProfile(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  const renderCoachAssignmentModal = () => (
    <div className="modal-overlay" onClick={() => setShowCoachAssignment(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Assign a Coach</h2>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <p className="modal-subtitle">Enter your coach's email address to connect with them.</p>
        
        <form onSubmit={handleAssignCoach}>
          <input
            type="email"
            placeholder="Coach's Email"
            value={coachEmail}
            onChange={(e) => setCoachEmail(e.target.value)}
            required
            className="input-field"
          />
          
          <div className="modal-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Assigning...' : 'Assign Coach'}
            </button>
            <button type="button" onClick={() => setShowCoachAssignment(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  const renderBadgesModal = () => (
    <div className="modal-overlay" onClick={() => setShowBadges(false)}>
      <div className="modal-content badges-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Your Badges</h2>
        <p className="badge-progress">{badges.total_earned} of {badges.total_available} earned</p>
        
        <div className="badges-grid">
          {badges.all_badges.map((badge) => (
            <div key={badge.id} className={`badge-item ${badge.earned ? 'earned' : 'locked'}`}>
              <div className="badge-icon">{badge.icon}</div>
              <h4>{badge.name}</h4>
              <p>{badge.description}</p>
              {!badge.earned && <div className="badge-lock">🔒</div>}
            </div>
          ))}
        </div>
        
        <button onClick={() => setShowBadges(false)} className="btn-primary" style={{marginTop: '24px'}}>
          Close
        </button>
      </div>
    </div>
  );

  const renderAnalyticsModal = () => (
    <div className="modal-overlay" onClick={() => setShowAnalytics(false)}>
      <div className="modal-content analytics-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Your Insights</h2>
        
        {analytics && (
          <>
            <div className="analytics-summary">
              <div className="analytics-card">
                <h4>This Week</h4>
                <p className="analytics-value">{analytics.meals_this_week}</p>
                <p className="analytics-label">meals logged</p>
              </div>
              <div className="analytics-card">
                <h4>This Month</h4>
                <p className="analytics-value">{analytics.meals_this_month}</p>
                <p className="analytics-label">meals logged</p>
              </div>
              <div className="analytics-card">
                <h4>Total</h4>
                <p className="analytics-value">{analytics.total_meals}</p>
                <p className="analytics-label">all time</p>
              </div>
            </div>

            <div className="analytics-section">
              <h3>Weekly Trend</h3>
              <div className="weekly-chart">
                {analytics.weekly_trend.map((day) => (
                  <div key={day.date} className="chart-bar">
                    <div className="bar" style={{height: `${day.meals * 30}px`}}>
                      <span className="bar-value">{day.meals}</span>
                    </div>
                    <span className="bar-label">{day.day_name}</span>
                  </div>
                ))}
              </div>
            </div>

            {analytics.meal_times && analytics.meal_times.length > 0 && (
              <div className="analytics-section">
                <h3>Most Common Meal Times</h3>
                <div className="meal-times-list">
                  {analytics.meal_times.map((time, index) => (
                    <div key={index} className="meal-time-item">
                      <span>{time.hour}:00</span>
                      <span>{time.count} meals</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        
        <button onClick={() => setShowAnalytics(false)} className="btn-primary" style={{marginTop: '24px'}}>
          Close
        </button>
      </div>
    </div>
  );

  const renderProgressPhotosModal = () => (
    <div className="modal-overlay" onClick={() => setShowProgressPhotos(false)}>
      <div className="modal-content progress-photos-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Progress Photos</h2>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        {!capturedProgressPhoto ? (
          <div>
            <div className="progress-upload-section">
              <label className="btn-secondary upload-label" style={{width: '100%'}}>
                Upload Progress Photo
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      const reader = new FileReader();
                      reader.onloadend = () => setCapturedProgressPhoto(reader.result);
                      reader.readAsDataURL(file);
                    }
                  }} 
                  style={{display: 'none'}} 
                />
              </label>
            </div>

            <div className="progress-photos-grid">
              {progressPhotos.length === 0 ? (
                <p className="empty-state">No progress photos yet. Upload your first one!</p>
              ) : (
                progressPhotos.map((photo) => (
                  <div key={photo.photo_id} className="progress-photo-card">
                    <img 
                      src={`data:image/jpeg;base64,${photo.image_base64}`} 
                      alt="Progress" 
                      className="progress-photo-image"
                    />
                    <div className="progress-photo-info">
                      <p className="progress-photo-date">{new Date(photo.timestamp).toLocaleDateString()}</p>
                      {photo.weight && <p className="progress-photo-weight">Weight: {photo.weight} kg</p>}
                      {photo.notes && <p className="progress-photo-notes">{photo.notes}</p>}
                      <button 
                        onClick={() => deleteProgressPhoto(photo.photo_id)} 
                        className="btn-remove-coach"
                        style={{marginTop: '8px', width: '100%'}}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div>
            <img src={capturedProgressPhoto} alt="Preview" className="preview-image" />
            <input
              type="number"
              step="0.1"
              placeholder="Current Weight (kg) - Optional"
              value={progressPhotoWeight}
              onChange={(e) => setProgressPhotoWeight(e.target.value)}
              className="input-field"
            />
            <textarea
              placeholder="Notes (optional)"
              value={progressPhotoNotes}
              onChange={(e) => setProgressPhotoNotes(e.target.value)}
              className="notes-input"
            />
            <div className="modal-actions">
              <button onClick={handleUploadProgressPhoto} className="btn-primary" disabled={loading}>
                {loading ? 'Uploading...' : 'Upload Photo'}
              </button>
              <button onClick={() => setCapturedProgressPhoto(null)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        )}
        
        {!capturedProgressPhoto && (
          <button onClick={() => setShowProgressPhotos(false)} className="btn-secondary" style={{marginTop: '16px', width: '100%'}}>
            Close
          </button>
        )}
      </div>
    </div>
  );

  const renderBarcodeScannerModal = () => (
    <div className="modal-overlay" onClick={() => setShowBarcodeScanner(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Scan Barcode</h2>
        <p className="modal-subtitle">Enter the barcode number from packaged food</p>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <input
          type="text"
          placeholder="Enter barcode number"
          value={barcodeInput}
          onChange={(e) => setBarcodeInput(e.target.value)}
          className="input-field"
          maxLength="20"
        />
        
        <button 
          onClick={handleBarcodeScann} 
          className="btn-primary" 
          disabled={scanningBarcode}
          style={{width: '100%', marginBottom: '16px'}}
        >
          {scanningBarcode ? 'Scanning...' : 'Scan Barcode'}
        </button>
        
        {barcodeResult && (
          <div className="barcode-result">
            <h3>Product Found!</h3>
            <div className="barcode-product-info">
              <p className="product-name">{barcodeResult.food_name}</p>
              {barcodeResult.brand && <p className="product-brand">{barcodeResult.brand}</p>}
              <div className="nutrition-grid">
                <div className="nutrition-item">
                  <span className="nutrition-label">Calories</span>
                  <span className="nutrition-value">{barcodeResult.calories}</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-label">Protein</span>
                  <span className="nutrition-value">{barcodeResult.protein}g</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-label">Carbs</span>
                  <span className="nutrition-value">{barcodeResult.carbs}g</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-label">Fats</span>
                  <span className="nutrition-value">{barcodeResult.fats}g</span>
                </div>
              </div>
              <p className="serving-size">Serving: {barcodeResult.serving_size}</p>
              <button onClick={addBarcodeProduct} className="btn-primary" style={{width: '100%', marginTop: '16px'}}>
                Add to Meal Log
              </button>
            </div>
          </div>
        )}
        
        <button onClick={() => {
          setShowBarcodeScanner(false);
          setBarcodeInput('');
          setBarcodeResult(null);
        }} className="btn-secondary" style={{width: '100%'}}>
          Cancel
        </button>
      </div>
    </div>
  );

  const renderActivityLoggerModal = () => (
    <div className="modal-overlay" onClick={() => setShowActivityLogger(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Log Activity</h2>
        <p className="modal-subtitle">Track your workouts and exercises</p>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <form onSubmit={handleLogActivity}>
          <label className="input-label">Activity Type</label>
          <select
            value={activityForm.activity_type}
            onChange={(e) => setActivityForm({...activityForm, activity_type: e.target.value})}
            className="input-field"
          >
            {activityTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.icon} {type.name}
              </option>
            ))}
          </select>

          <label className="input-label">Duration (minutes)</label>
          <input
            type="number"
            placeholder="Duration in minutes"
            value={activityForm.duration_minutes}
            onChange={(e) => setActivityForm({...activityForm, duration_minutes: e.target.value})}
            className="input-field"
            min="1"
            required
          />

          <label className="input-label">Intensity</label>
          <select
            value={activityForm.intensity}
            onChange={(e) => setActivityForm({...activityForm, intensity: e.target.value})}
            className="input-field"
          >
            <option value="low">Low - Light effort</option>
            <option value="moderate">Moderate - Some effort</option>
            <option value="high">High - Intense effort</option>
          </select>

          <label className="input-label">Notes (optional)</label>
          <textarea
            placeholder="Add any notes about your workout"
            value={activityForm.notes}
            onChange={(e) => setActivityForm({...activityForm, notes: e.target.value})}
            className="notes-input"
            rows="3"
          />

          <div className="modal-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Logging...' : 'Log Activity'}
            </button>
            <button type="button" onClick={() => setShowActivityLogger(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  const renderHealthImportModal = () => (
    <div className="modal-overlay" onClick={() => setShowHealthImport(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Sync Wearable Data</h2>
        <p className="modal-subtitle">Import activities from your health apps</p>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <div className="health-import-options">
          <div className="import-card">
            <div className="import-icon">🍎</div>
            <h3>Apple Health</h3>
            <p>Import workouts from iPhone Health app</p>
            <div className="import-steps">
              <ol>
                <li>Open Health app on iPhone</li>
                <li>Tap your profile (top right)</li>
                <li>Scroll down → "Export All Health Data"</li>
                <li>Save the export.zip file</li>
                <li>Extract and upload export.xml below</li>
              </ol>
            </div>
            <label className="btn-primary upload-label" style={{width: '100%', marginTop: '16px'}}>
              {importingHealth ? 'Importing...' : 'Upload Apple Health XML'}
              <input 
                type="file" 
                accept=".xml" 
                onChange={(e) => handleHealthFileImport(e, 'apple_health')}
                disabled={importingHealth}
                style={{display: 'none'}} 
              />
            </label>
          </div>

          <div className="import-card">
            <div className="import-icon">🤖</div>
            <h3>Google Fit</h3>
            <p>Import activities from Google Fit</p>
            <div className="import-steps">
              <ol>
                <li>Go to Google Takeout</li>
                <li>Select only "Fit" data</li>
                <li>Choose CSV format</li>
                <li>Download your data</li>
                <li>Upload the CSV file below</li>
              </ol>
            </div>
            <label className="btn-primary upload-label" style={{width: '100%', marginTop: '16px'}}>
              {importingHealth ? 'Importing...' : 'Upload Google Fit CSV'}
              <input 
                type="file" 
                accept=".csv" 
                onChange={(e) => handleHealthFileImport(e, 'google_fit')}
                disabled={importingHealth}
                style={{display: 'none'}} 
              />
            </label>
          </div>
        </div>

        <div className="import-note">
          <p><strong>💡 Tip:</strong> This is a one-time import. For continuous syncing, export and upload regularly, or consider upgrading to automatic sync in the future.</p>
        </div>

        <button 
          onClick={() => setShowHealthImport(false)} 
          className="btn-secondary" 
          style={{width: '100%', marginTop: '16px'}}
        >
          Close
        </button>
      </div>
    </div>
  );

  const renderUserDashboard = () => (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <div className="dashboard-brand">
            <h1>NourishStrong</h1>
            <span className="dashboard-tagline">Your Wellness Journey</span>
          </div>
          <div className="header-actions">
            <span className="user-name">Hi, {user?.name}!</span>
            <button onClick={() => setShowProfile(true)} className="btn-secondary">Profile</button>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        {success && <div className="success-message">{success}</div>}
        {error && <div className="error-message">{error}</div>}

        {/* Badge Celebration */}
        {newBadgesCelebration.length > 0 && (
          <div className="celebration-banner">
            <h3>🎉 New Badge{newBadgesCelebration.length > 1 ? 's' : ''} Earned!</h3>
            <div className="celebration-badges">
              {newBadgesCelebration.map((badge, index) => (
                <div key={index} className="celebration-badge">
                  <span className="celebration-icon">{badge.icon}</span>
                  <span>{badge.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Gamification Dashboard */}
        <div className="gamification-bar">
          <div className="streak-display" onClick={() => setShowAnalytics(true)}>
            <span className="streak-icon">🔥</span>
            <div className="streak-info">
              <span className="streak-number">{streak.current_streak}</span>
              <span className="streak-label">day streak</span>
            </div>
          </div>
          
          <div className="badges-display" onClick={() => setShowBadges(true)}>
            <span className="badges-icon">🏆</span>
            <div className="badges-info">
              <span className="badges-number">{badges.total_earned}/{badges.total_available}</span>
              <span className="badges-label">badges</span>
            </div>
          </div>

          <button onClick={() => setShowActivityLogger(true)} className="quick-action-btn">
            <span>🏃</span>
            <span>Log Activity</span>
          </button>

          <button onClick={() => setShowHealthImport(true)} className="quick-action-btn">
            <span>📱</span>
            <span>Sync Data</span>
          </button>

          <button onClick={() => setShowProgressPhotos(true)} className="quick-action-btn">
            <span>📸</span>
            <span>Progress</span>
          </button>

          <button onClick={() => setShowAnalytics(true)} className="quick-action-btn">
            <span>📊</span>
            <span>Insights</span>
          </button>
        </div>

        {/* Activity Stats Summary */}
        {activityStats && activityStats.total_activities > 0 && (
          <div className="activity-stats-summary">
            <h3>This Week's Activity</h3>
            <div className="stats-quick-view">
              <div className="stat-item">
                <span className="stat-icon">🏃</span>
                <div>
                  <span className="stat-number">{activityStats.this_week_activities}</span>
                  <span className="stat-label">workouts</span>
                </div>
              </div>
              <div className="stat-item">
                <span className="stat-icon">🔥</span>
                <div>
                  <span className="stat-number">{activityStats.this_week_calories}</span>
                  <span className="stat-label">calories burned</span>
                </div>
              </div>
              <div className="stat-item">
                <span className="stat-icon">⏱️</span>
                <div>
                  <span className="stat-number">{activityStats.this_week_minutes}</span>
                  <span className="stat-label">minutes</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Daily Challenge */}
        {dailyChallenge && !dailyChallenge.completed && (
          <div className="daily-challenge-card">
            <div className="challenge-header">
              <span className="challenge-icon">{dailyChallenge.challenge.icon}</span>
              <div>
                <h3>{dailyChallenge.challenge.title}</h3>
                <p>{dailyChallenge.challenge.description}</p>
              </div>
            </div>
            <button onClick={handleCompleteChallenge} className="btn-primary challenge-btn">
              Mark Complete
            </button>
          </div>
        )}

        {/* Motivational Quote */}
        {dailyQuote && (
          <div className="motivational-quote-card">
            <span className="quote-icon">{dailyQuote.icon}</span>
            <p className="quote-text">"{dailyQuote.quote}"</p>
            <span className="quote-category">{dailyQuote.category}</span>
          </div>
        )}

        {/* Coach Info Section */}
        {user?.coach ? (
          <div className="coach-info-card">
            <h3>Your Coach</h3>
            <p><strong>{user.coach.name}</strong></p>
            <p>{user.coach.email}</p>
            <button onClick={handleRemoveCoach} className="btn-remove-coach">
              Remove Coach
            </button>
          </div>
        ) : (
          <div className="coach-info-card">
            <h3>No Coach Assigned</h3>
            <p>Connect with a coach to get personalized support!</p>
            <button onClick={() => setShowCoachAssignment(true)} className="btn-primary">
              Add a Coach
            </button>
          </div>
        )}

        {/* Profile Summary */}
        {user?.profile && Object.keys(user.profile).length > 0 && (
          <div className="profile-summary">
            <h3>Your Profile</h3>
            <div className="profile-grid">
              {user.profile.age && <div><strong>Age:</strong> {user.profile.age}</div>}
              {user.profile.gender && <div><strong>Gender:</strong> {user.profile.gender}</div>}
              {user.profile.height && <div><strong>Height:</strong> {user.profile.height} cm</div>}
              {user.profile.weight && <div><strong>Weight:</strong> {user.profile.weight} kg</div>}
              {user.profile.goal_weight && <div><strong>Goal:</strong> {user.profile.goal_weight} kg</div>}
              {user.profile.activity_level && <div><strong>Activity:</strong> {user.profile.activity_level}</div>}
            </div>
          </div>
        )}

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

              <button onClick={() => setShowBarcodeScanner(true)} className="btn-secondary">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="9" y1="3" x2="9" y2="21"></line>
                  <line x1="15" y1="3" x2="15" y2="21"></line>
                </svg>
                Scan Barcode
              </button>
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

        {/* Activity History */}
        <div className="meals-section">
          <h2 className="section-title">Recent Activities</h2>
          <div className="meals-grid">
            {activities.length === 0 ? (
              <p className="empty-state">No activities logged yet. Start by logging your first workout!</p>
            ) : (
              activities.slice(0, 6).map((activity) => (
                <div key={activity.activity_id} className="meal-card activity-card">
                  <div className="activity-header">
                    <span className="activity-type-icon">
                      {activity.activity_info?.icon || '🏃'}
                    </span>
                    <div className="activity-details">
                      <h4>{activity.activity_info?.name || activity.activity_type}</h4>
                      <p className="activity-duration">{activity.duration_minutes} minutes • {activity.intensity} intensity</p>
                    </div>
                  </div>
                  <div className="activity-stats">
                    <div className="activity-stat">
                      <span className="activity-stat-icon">🔥</span>
                      <span>{activity.calories_burned} cal</span>
                    </div>
                  </div>
                  <div className="meal-info">
                    <p className="meal-time">{new Date(activity.timestamp).toLocaleString()}</p>
                    {activity.notes && <p className="meal-notes">{activity.notes}</p>}
                  </div>
                  <button 
                    onClick={() => deleteActivity(activity.activity_id)} 
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

      {/* Modals */}
      {showProfile && renderProfileModal()}
      {showCoachAssignment && renderCoachAssignmentModal()}
      {showBadges && renderBadgesModal()}
      {showAnalytics && renderAnalyticsModal()}
      {showProgressPhotos && renderProgressPhotosModal()}
      {showBarcodeScanner && renderBarcodeScannerModal()}
      {showActivityLogger && renderActivityLoggerModal()}
      {showHealthImport && renderHealthImportModal()}

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
          <div className="dashboard-brand">
            <h1>NourishStrong Coach</h1>
            <span className="dashboard-tagline">Support & Guide</span>
          </div>
          <div className="header-actions">
            <span className="user-name">Coach {user?.name}</span>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content coach-view">
        <div className="users-sidebar">
          <h2 className="section-title">Your Clients</h2>
          <p className="coach-email-info">Share your email with clients: <strong>{user?.email}</strong></p>
          <div className="users-list">
            {allUsers.length === 0 ? (
              <p className="empty-state-small">No clients yet. Share your email with users so they can add you as their coach!</p>
            ) : (
              allUsers.map((u) => (
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
              ))
            )}
          </div>
        </div>

        <div className="user-details">
          {selectedUserId ? (
            <>
              {selectedUserInfo && selectedUserInfo.profile && Object.keys(selectedUserInfo.profile).length > 0 && (
                <div className="client-profile-section">
                  <h2 className="section-title">Client Profile</h2>
                  <div className="profile-grid">
                    {selectedUserInfo.profile.age && <div><strong>Age:</strong> {selectedUserInfo.profile.age}</div>}
                    {selectedUserInfo.profile.gender && <div><strong>Gender:</strong> {selectedUserInfo.profile.gender}</div>}
                    {selectedUserInfo.profile.height && <div><strong>Height:</strong> {selectedUserInfo.profile.height} cm</div>}
                    {selectedUserInfo.profile.weight && <div><strong>Current Weight:</strong> {selectedUserInfo.profile.weight} kg</div>}
                    {selectedUserInfo.profile.goal_weight && <div><strong>Goal Weight:</strong> {selectedUserInfo.profile.goal_weight} kg</div>}
                    {selectedUserInfo.profile.activity_level && <div><strong>Activity Level:</strong> {selectedUserInfo.profile.activity_level}</div>}
                  </div>
                </div>
              )}

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
