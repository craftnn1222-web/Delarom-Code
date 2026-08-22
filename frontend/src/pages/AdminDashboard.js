import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Shield, AlertCircle, Globe } from 'lucide-react';
import AdminNPCManager from '../components/AdminNPCManager';
import AdminWorldPulse from '../components/AdminWorldPulse';
import AdminLawPanel from '../components/AdminLawPanel';
import ApplicationsTab from '../components/admin/ApplicationsTab';
import UsersTab from '../components/admin/UsersTab';
import IpBansTab from '../components/admin/IpBansTab';
import LocationsTab from '../components/admin/LocationsTab';
import DatabaseSeedPanel from '../components/admin/DatabaseSeedPanel';
import CharterReviewTab from '../components/admin/CharterReviewTab';


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminDashboard = () => {
  const navigate = useNavigate();
  // Source the current user from AuthContext (cookie-driven). No local
  // /auth/me fetch — that was the cause of a Temporal Dead Zone crash and
  // is redundant now that AuthContext owns the session.
  const { currentUser } = useAuth();
  const [locations, setLocations] = useState([]);
  // Cities for the "Create Location" parent-city picker. Lazily fetched per
  // nation via the lightweight /api/cities/{nation} endpoint when the create
  // modal opens — the all-nations /api/cities returns enormous base64 image
  // blobs (~335MB on a fully-illustrated realm) and was breaking the admin
  // dashboard load entirely.
  const [modalCities, setModalCities] = useState([]);
  const [locationModal, setLocationModal] = useState({ open: false, mode: 'create', location: null });

  const [applications, setApplications] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});
  const [modalState, setModalState] = useState({ 
    open: false, 
    type: null, // 'suspend', 'ban', 'promote', 'demote', 'reject', 'resetPassword', 'removeAccount', 'viewUser', 'addIpBan'
    userId: null, 
    username: null,
    email: null,
    suspendDays: '7',
    reason: '',
    newPassword: '',
    banIp: false,
    ipAddress: '',
    userDetails: null
  });
  
  // IP Bans state
  const [ipBans, setIpBans] = useState([]);
  
  // Database seeding state
  const [dbStatus, setDbStatus] = useState(null);
  const [seedStatus, setSeedStatus] = useState(null); // { status, phase, progress, message, results, error }
  const [withImages, setWithImages] = useState(true);
  const seeding = seedStatus?.status === 'running';

  const fetchData = useCallback(async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    try {
      // Auth is carried by the httpOnly cookie — axios.defaults.withCredentials
      // is enabled in utils/api.js so every request below sends it.
      const headers = {};

      // Applications — admin only
      let appsRes = { data: { applications: [] } };
      if (currentUser.role === 'admin') {
        try {
          appsRes = await axios.get(`${BACKEND_URL}/api/admin/applications`, { headers });
        } catch (err) {
          console.error('Error fetching applications:', err);
        }
      }

      // Dynamic locations — admins & moderators (independent of applications)
      try {
        const locationsRes = await axios.get(`${BACKEND_URL}/api/locations`, { headers });
        setLocations(locationsRes.data || []);
      } catch (err) {
        console.error('Error fetching locations:', err);
      }

      // Users — admins & moderators
      const usersRes = await axios.get(`${BACKEND_URL}/api/admin/users`, { headers });

      setApplications(appsRes.data?.applications || []);
      setUsers(usersRes.data?.users || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error(error.response?.data?.detail || 'Failed to load data');
      if (error.response?.status === 401 || error.response?.status === 403) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  }, [currentUser, navigate]);

  // Lazy-load just the chosen nation's cities (lightweight endpoint, no
  // image_url blobs) whenever the Create-Location modal is open and a
  // nation is entered. Cached on the modalCities state until the modal
  // closes or the nation changes.
  const modalNation = locationModal.open && locationModal.mode === 'create'
    ? (locationModal.location?.nation || '').trim().toLowerCase()
    : '';
  useEffect(() => {
    if (!modalNation) {
      setModalCities([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${BACKEND_URL}/api/cities/${modalNation}`);
        if (!cancelled) setModalCities(r.data || []);
      } catch (err) {
        console.error('Error fetching cities for nation', modalNation, err);
        if (!cancelled) setModalCities([]);
      }
    })();
    return () => { cancelled = true; };
  }, [modalNation]);

  // Fetch IP bans
  const fetchIpBans = useCallback(async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/admin/ip-bans`, {});
      setIpBans(response.data || []);
    } catch (error) {
      console.error('Error fetching IP bans:', error);
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      if (currentUser.role !== 'admin' && currentUser.role !== 'moderator') {
        toast.error('Access denied: Admin or Moderator only');
        navigate('/dashboard');
        return;
      }
      fetchData();
      if (currentUser.role === 'admin') {
        fetchIpBans();
      }
    }
  }, [currentUser, navigate, fetchData, fetchIpBans]);

  // Fetch database status
  const fetchDbStatus = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/admin/database-status`, {});
      setDbStatus(response.data);
    } catch (error) {
      console.error('Error fetching database status:', error);
    }
  };

  // Seed the database (background task with polling)
  const [prevSeedStatus, setPrevSeedStatus] = useState(null);

  const fetchSeedStatus = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/admin/seed-status`, {});
      setSeedStatus(res.data);
      return res.data;
    } catch (error) {
      console.error('Error fetching seed status:', error);
      return null;
    }
  };

  const handleSeedDatabase = async () => {
    if (!window.confirm('This will populate the database with all nations, cities, and locations in the background. Continue?')) {
      return;
    }
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/admin/start-full-seed?with_images=${withImages}`,
        {},
        {}
      );
      setSeedStatus(res.data);
      setPrevSeedStatus('running');
      if (res.data.already_running) {
        toast.info('A seeding task is already running. Tracking progress…');
      } else {
        toast.success('Seeding started in background.');
      }
    } catch (error) {
      console.error('Error starting seed:', error);
      toast.error(error.response?.data?.detail || 'Failed to start seeding');
    }
  };

  // Initial fetch to recover any in-flight task on mount
  useEffect(() => {
    if (currentUser?.role !== 'admin') return;
    fetchSeedStatus();
  }, [currentUser]);

  // Toast + status refresh only when transitioning OUT of running
  useEffect(() => {
    if (!seedStatus) return;
    if (prevSeedStatus === 'running' && seedStatus.status === 'completed') {
      fetchDbStatus();
      toast.success(seedStatus.message || 'Seeding completed');
    } else if (prevSeedStatus === 'running' && seedStatus.status === 'failed') {
      toast.error(seedStatus.message || 'Seeding failed');
    }
    setPrevSeedStatus(seedStatus.status);
  }, [seedStatus, prevSeedStatus]);

  // Poll while running
  useEffect(() => {
    if (seedStatus?.status !== 'running') return;
    const interval = setInterval(fetchSeedStatus, 2500);
    return () => clearInterval(interval);
  }, [seedStatus?.status]);

  // Fetch db status when user is admin
  useEffect(() => {
    if (currentUser?.role === 'admin') {
      fetchDbStatus();
    }
  }, [currentUser]);

  const handleApprove = async (userId, username) => {
    setActionLoading({ ...actionLoading, [userId]: true });
    try {
      await axios.post(`${BACKEND_URL}/api/admin/applications/${userId}/approve`, {}, {});
      toast.success(`${username} approved!`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    } finally {
      setActionLoading({ ...actionLoading, [userId]: false });
    }
  };

  const handleReject = (userId, username) => {
    setModalState({ 
      open: true, 
      type: 'reject', 
      userId, 
      username,
      suspendDays: '7',
      reason: '' 
    });
  };

  const handleBan = (userId, username) => {
    setModalState({ 
      open: true, 
      type: 'ban', 
      userId, 
      username,
      suspendDays: '7',
      reason: '' 
    });
  };

  const handleUnban = async (userId, username) => {
    setActionLoading({ ...actionLoading, [userId]: true });
    try {
      await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/unban`, {}, {});
      toast.success(`${username} unbanned`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unban');
    } finally {
      setActionLoading({ ...actionLoading, [userId]: false });
    }
  };

  const handleSuspend = (userId, username) => {
    setModalState({ 
      open: true, 
      type: 'suspend', 
      userId, 
      username,
      suspendDays: '7',
      reason: '' 
    });
  };

  const handleUnsuspend = async (userId, username) => {
    setActionLoading({ ...actionLoading, [userId]: true });
    try {
      await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/unsuspend`, {}, {});
      toast.success(`${username} unsuspended`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unsuspend');
    } finally {
      setActionLoading({ ...actionLoading, [userId]: false });
    }
  };

  const handlePromoteModerator = (userId, username) => {
    setModalState({ 
      open: true, 
      type: 'promote', 
      userId, 
      username,
      suspendDays: '7',
      reason: '' 
    });
  };

  const handleDemoteModerator = (userId, username) => {
    setModalState({ 
      open: true, 
      type: 'demote', 
      userId, 
      username,
      suspendDays: '7',
      reason: '' 
    });
  };

  const handleResetPassword = (userId, username, email) => {
    setModalState({ 
      open: true, 
      type: 'resetPassword', 
      userId, 
      username,
      email,
      suspendDays: '7',
      reason: '',
      newPassword: ''
    });
  };

  const handleRemoveAccount = (userId, username, email) => {
    setModalState({ 
      open: true, 
      type: 'removeAccount', 
      userId, 
      username,
      email,
      suspendDays: '7',
      reason: '',
      newPassword: '',
      banIp: false
    });
  };

  const handleViewUser = async (userId) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/admin/users/${userId}/details`, {});
      setModalState({ 
        open: true, 
        type: 'viewUser', 
        userId,
        userDetails: response.data
      });
    } catch (_error) {
      toast.error('Failed to fetch user details');
    }
  };

  const handleAddIpBan = () => {
    setModalState({ 
      open: true, 
      type: 'addIpBan', 
      ipAddress: '',
      reason: ''
    });
  };

  const handleRemoveIpBan = async (banId) => {
    try {
      await axios.delete(`${BACKEND_URL}/api/admin/ip-bans/${banId}`, {});
      toast.success('IP ban removed');
      fetchIpBans();
    } catch (_error) {
      toast.error('Failed to remove IP ban');
    }
  };

  const confirmAction = async () => {
    const { type, userId, username, suspendDays, reason, newPassword, banIp, ipAddress } = modalState;
    
    setModalState({ ...modalState, open: false });
    if (userId) {
      setActionLoading({ ...actionLoading, [userId]: true });
    }

    try {
      const headers = {};

      switch (type) {
        case 'reject':
          await axios.post(`${BACKEND_URL}/api/admin/applications/${userId}/reject`, null, {
            params: { reason: 'Application rejected' },
            headers
          });
          toast.success(`${username}'s application rejected`);
          break;

        case 'ban':
          await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/ban`, null, {
            params: { reason: reason || 'No reason provided' },
            headers
          });
          toast.success(`${username} banned`);
          break;

        case 'suspend':
          await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/suspend`, null, {
            params: { days: parseInt(suspendDays) || 7, reason: reason || 'No reason provided' },
            headers
          });
          toast.success(`${username} suspended for ${suspendDays} days`);
          break;

        case 'promote':
          await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/promote-moderator`, {}, { headers });
          toast.success(`${username} promoted to Moderator!`);
          break;

        case 'demote':
          await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/demote-moderator`, {}, { headers });
          toast.success(`${username} demoted to Member`);
          break;

        case 'resetPassword':
          if (!newPassword || newPassword.length < 6) {
            toast.error('Password must be at least 6 characters');
            return;
          }
          await axios.post(`${BACKEND_URL}/api/admin/users/${userId}/reset-password`, 
            { new_password: newPassword },
            { headers }
          );
          toast.success(`Password reset for ${username}`);
          break;

        case 'removeAccount':
          await axios.delete(`${BACKEND_URL}/api/admin/users/${userId}/remove`, {
            params: { ban_ip: banIp },
            headers
          });
          toast.success(`${username}'s account permanently removed${banIp ? ' and IP banned' : ''}`);
          break;

        case 'addIpBan':
          if (!ipAddress) {
            toast.error('Please enter an IP address');
            return;
          }
          await axios.post(`${BACKEND_URL}/api/admin/ip-bans`, 
            { ip_address: ipAddress, reason: reason || 'Manual ban' },
            { headers }
          );
          toast.success(`IP ${ipAddress} has been banned`);
          fetchIpBans();
          break;

        default:
          break;
      }

      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${type}`);
    } finally {
      if (userId) {
        setActionLoading({ ...actionLoading, [userId]: false });
      }
    }
  };

  const getStatusBadge = (rawStatus) => {
    const status = rawStatus || 'active';
    const styles = {
      active: 'bg-green-600/20 text-green-400 border-green-600/30',
      suspended: 'bg-yellow-600/20 text-yellow-400 border-yellow-600/30',
      banned: 'bg-red-600/20 text-red-400 border-red-600/30',
      pending: 'bg-blue-600/20 text-blue-400 border-blue-600/30'
    };
    return (
      <span className={`text-xs px-2 py-1 rounded border ${styles[status] || ''}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const getRoleBadge = (rawRole) => {
    const role = rawRole || 'member';
    const styles = {
      admin: 'bg-purple-600/20 text-purple-400 border-purple-600/30',
      moderator: 'bg-blue-600/20 text-blue-400 border-blue-600/30',
      member: 'bg-gray-600/20 text-gray-400 border-gray-600/30'
    };
    return (
      <span className={`text-xs px-2 py-1 rounded border ${styles[role] || ''}`}>
        {role.toUpperCase()}
      </span>
    );
  };

  const handleEditLocation = (location) => {
    setLocationModal({ open: true, mode: 'edit', location });
  };

  const handleNewLocation = () => {
    setLocationModal({
      open: true,
      mode: 'create',
      location: {
        nation: 'ammeonon',
        // city must exist as a key so the controlled <select>'s value reads
        // a defined string ('') instead of undefined. The picker's onChange
        // writes the chosen city slug into this field.
        city: null,
        slug: '',
        name: '',
        location_type: '',
        description: '',
        is_active: true,
        is_rp_enabled: true,
      },
    });
  };

  const saveLocation = async () => {
    if (!locationModal.open) return;
    const headers = {};
    const loc = locationModal.location || {
      nation: 'ammeonon',
      city: null,
      slug: '',
      name: '',
      location_type: '',
      description: '',
      is_active: true,
      is_rp_enabled: true,
    };

    try {
      if (locationModal.mode === 'create') {
        const payload = {
          nation: loc.nation || 'ammeonon',
          // City is optional — empty/null means "nation-level location".
          // Anything else attaches the location to that city so it appears
          // on the CityDetail page. (Bug: dropping this field made every
          // newly-created location a nation-level orphan.)
          city: loc.city || null,
          slug: loc.slug || '',
          name: loc.name || '',
          location_type: loc.location_type || '',
          description: loc.description || '',
          is_active: loc.is_active !== false,
          is_rp_enabled: loc.is_rp_enabled !== false,
        };
        await axios.post(`${BACKEND_URL}/api/admin/locations`, payload, { headers });
        toast.success('Location created');
      } else if (locationModal.mode === 'edit' && loc.id) {
        const updates = {
          name: loc.name,
          location_type: loc.location_type,
          description: loc.description,
          is_active: loc.is_active,
          is_rp_enabled: loc.is_rp_enabled,
        };
        await axios.put(`${BACKEND_URL}/api/admin/locations/${loc.id}`, updates, { headers });
        toast.success('Location updated');
      }
      setLocationModal({ ...locationModal, open: false });
      fetchData();
    } catch (error) {
      console.error('Error saving location:', error);
      toast.error(error.response?.data?.detail || 'Failed to save location');
    }
  };

  const toggleLocationActive = async (loc) => {
    const headers = {};
    try {
      await axios.post(`${BACKEND_URL}/api/admin/locations/${loc.id}/toggle-active`, {}, { headers });
      toast.success(`Location ${loc.is_active ? 'disabled' : 'enabled'}`);
      fetchData();
    } catch (error) {
      console.error('Error toggling location:', error);
      toast.error(error.response?.data?.detail || 'Failed to toggle location');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center text-white">
          Loading admin dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-10 h-10 text-purple-400" />
          <div>
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
              Admin Dashboard
            </h1>
            <p className="text-gray-400">{currentUser?.role === 'admin' ? 'Site Administrator' : 'Moderator'}</p>
          </div>
        </div>

        <Tabs defaultValue={currentUser?.role === 'admin' ? "applications" : "users"} className="space-y-6">
          <TabsList className="bg-gray-900/50 border border-purple-500/30">
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="applications" className="data-[state=active]:bg-purple-600">
                Applications ({applications.length})
              </TabsTrigger>
            )}
            <TabsTrigger value="users" className="data-[state=active]:bg-purple-600">
              Users ({users.length})
            </TabsTrigger>
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="ipbans" className="data-[state=active]:bg-red-600">
                <Globe className="w-3 h-3 mr-1" />
                IP Bans ({ipBans.length})
              </TabsTrigger>
            )}
            <TabsTrigger value="locations" className="data-[state=active]:bg-purple-600">
              RP Locations ({locations.length})
            </TabsTrigger>
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="npcs" className="data-[state=active]:bg-purple-600" data-testid="admin-tab-npcs">
                NPCs & Scenes
              </TabsTrigger>
            )}
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="world" className="data-[state=active]:bg-purple-600" data-testid="admin-tab-world">
                World Pulse
              </TabsTrigger>
            )}
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="law" className="data-[state=active]:bg-amber-600" data-testid="admin-tab-law">
                Law
              </TabsTrigger>
            )}
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="database" className="data-[state=active]:bg-purple-600">
                Database
              </TabsTrigger>
            )}
            {currentUser?.role === 'admin' && (
              <TabsTrigger value="charters" className="data-[state=active]:bg-amber-600" data-testid="admin-tab-charters">
                Charters
              </TabsTrigger>
            )}
          </TabsList>

          {/* Applications Tab (Admin Only) */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="applications" className="space-y-4">
              <ApplicationsTab
                applications={applications}
                actionLoading={actionLoading}
                onApprove={handleApprove}
                onReject={handleReject}
                getStatusBadge={getStatusBadge}
              />
            </TabsContent>
          )}

          {/* Users Tab */}
          <TabsContent value="users" className="space-y-4">
            <UsersTab
              users={users}
              currentUser={currentUser}
              actionLoading={actionLoading}
              onSuspend={handleSuspend}
              onUnsuspend={handleUnsuspend}
              onBan={handleBan}
              onUnban={handleUnban}
              onPromote={handlePromoteModerator}
              onDemote={handleDemoteModerator}
              onResetPassword={handleResetPassword}
              onViewUser={handleViewUser}
              onRemoveAccount={handleRemoveAccount}
              getRoleBadge={getRoleBadge}
              getStatusBadge={getStatusBadge}
            />
          </TabsContent>

          {/* IP Bans Tab - Admin only */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="ipbans" className="space-y-4">
              <IpBansTab
                ipBans={ipBans}
                onAddIpBan={handleAddIpBan}
                onRemoveIpBan={handleRemoveIpBan}
              />
            </TabsContent>
          )}

          {/* Locations Tab - Admins & Moderators */}
          <TabsContent value="locations" className="space-y-4">
            <LocationsTab
              locations={locations}
              onNewLocation={handleNewLocation}
              onEditLocation={handleEditLocation}
              onToggleActive={toggleLocationActive}
            />
          </TabsContent>

          {/* NPCs & Scenes Tab (Admin Only) */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="npcs" className="space-y-6">
              <AdminNPCManager />
            </TabsContent>
          )}

          {/* World Pulse Tab (Admin Only) */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="world" className="space-y-6">
              <AdminWorldPulse />
            </TabsContent>
          )}

          {/* Law Tab (Admin Only) */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="law" className="space-y-6">
              <AdminLawPanel />
            </TabsContent>
          )}

          {/* Database Tab (Admin Only) */}
          {currentUser?.role === 'admin' && (
            <TabsContent value="database" className="space-y-6">
              <DatabaseSeedPanel
                dbStatus={dbStatus}
                seedStatus={seedStatus}
                seeding={seeding}
                withImages={withImages}
                onToggleWithImages={setWithImages}
                onSeed={handleSeedDatabase}
              />
            </TabsContent>
          )}

          {currentUser?.role === 'admin' && (
            <TabsContent value="charters" className="space-y-6">
              <CharterReviewTab />
            </TabsContent>
          )}

      {/* Location Edit/Create Modal */}
      <Dialog open={locationModal.open} onOpenChange={(open) => setLocationModal({ ...locationModal, open })}>
        <DialogContent className="bg-gray-900 border-purple-500/30 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-2xl text-purple-300">
              {locationModal.mode === 'create' ? 'Create Location' : 'Edit Location'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label className="text-gray-300">Nation Slug (e.g. ammeonon)</Label>
              <Input
                value={locationModal.location?.nation || ''}
                onChange={(e) =>
                  setLocationModal({
                    ...locationModal,
                    location: { ...locationModal.location, nation: e.target.value.toLowerCase() },
                  })
                }
                className="bg-black/20 border-purple-500/30 text-white"
              />
            </div>
            {/* City picker — only relevant on create. Empty = nation-level
                location (no parent city). Filtered to cities of the chosen
                nation so admins can't accidentally attach a Wymroost
                location to a Selindori nation. Native <select> avoids the
                Radix-Dialog-inside-Radix-Select focus-trap fights. */}
            {locationModal.mode === 'create' && (
              <div>
                <Label className="text-gray-300">
                  Parent City <span className="text-gray-500 text-xs">(optional — leave blank for a nation-level location)</span>
                </Label>
                <select
                  value={locationModal.location?.city || ''}
                  onChange={(e) =>
                    setLocationModal({
                      ...locationModal,
                      location: { ...locationModal.location, city: e.target.value || null },
                    })
                  }
                  className="mt-1 w-full bg-black/20 border border-purple-500/30 text-white rounded-md px-3 py-2"
                  data-testid="admin-location-city-select"
                >
                  <option value="">— Nation-level (no parent city) —</option>
                  {modalCities.map((c) => (
                    <option key={c.id || c.slug} value={c.slug} className="bg-gray-900">
                      {c.name} ({c.slug})
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <Label className="text-gray-300">Location Slug (URL-safe)</Label>
              <Input
                value={locationModal.location?.slug || ''}
                onChange={(e) =>
                  setLocationModal({
                    ...locationModal,
                    location: { ...locationModal.location, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') },
                  })
                }
                className="bg-black/20 border-purple-500/30 text-white"
              />
            </div>
            <div>
              <Label className="text-gray-300">Display Name</Label>
              <Input
                value={locationModal.location?.name || ''}
                onChange={(e) =>
                  setLocationModal({
                    ...locationModal,
                    location: { ...locationModal.location, name: e.target.value },
                  })
                }
                className="bg-black/20 border-purple-500/30 text-white"
              />
            </div>
            <div>
              <Label className="text-gray-300">Type (e.g. Tavern, City Gate, Market)</Label>
              <Input
                value={locationModal.location?.location_type || ''}
                onChange={(e) =>
                  setLocationModal({
                    ...locationModal,
                    location: { ...locationModal.location, location_type: e.target.value },
                  })
                }
                className="bg-black/20 border-purple-500/30 text-white"
              />
            </div>
            <div>
              <Label className="text-gray-300">Description / Lore</Label>
              <Textarea
                value={locationModal.location?.description || ''}
                onChange={(e) =>
                  setLocationModal({
                    ...locationModal,
                    location: { ...locationModal.location, description: e.target.value },
                  })
                }
                rows={4}
                className="bg-black/20 border-purple-500/30 text-white resize-none"
              />
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={locationModal.location?.is_active ?? true}
                  onChange={(e) =>
                    setLocationModal({
                      ...locationModal,
                      location: { ...locationModal.location, is_active: e.target.checked },
                    })
                  }
                />
                Active
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={locationModal.location?.is_rp_enabled ?? true}
                  onChange={(e) =>
                    setLocationModal({
                      ...locationModal,
                      location: { ...locationModal.location, is_rp_enabled: e.target.checked },
                    })
                  }
                />
                RP Enabled
              </label>
            </div>
          </div>

          <DialogFooter className="flex gap-2">
            <Button
              onClick={() => setLocationModal({ ...locationModal, open: false })}
              className="bg-gray-600 hover:bg-gray-700"
            >
              Cancel
            </Button>
            <Button
              onClick={saveLocation}
              className="bg-purple-600 hover:bg-purple-700"
            >
              Save Location
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
        </Tabs>
      </div>

      {/* Action Confirmation Modal */}
      <Dialog open={modalState.open} onOpenChange={(open) => setModalState({ ...modalState, open })}>
        <DialogContent className="bg-gray-900 border-purple-500/30 text-white">
          <DialogHeader>
            <DialogTitle className="text-2xl text-purple-300">
              {modalState.type === 'reject' && `Reject Application`}
              {modalState.type === 'ban' && `Ban User`}
              {modalState.type === 'suspend' && `Suspend User`}
              {modalState.type === 'promote' && `Promote to Moderator`}
              {modalState.type === 'demote' && `Demote from Moderator`}
              {modalState.type === 'resetPassword' && `Reset Password`}
              {modalState.type === 'removeAccount' && `Remove Account`}
              {modalState.type === 'viewUser' && `User Details`}
              {modalState.type === 'addIpBan' && `Add IP Ban`}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* View User Details */}
            {modalState.type === 'viewUser' && modalState.userDetails && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-400">Username:</div>
                  <div className="text-white">{modalState.userDetails.username}</div>
                  <div className="text-gray-400">Email:</div>
                  <div className="text-white">{modalState.userDetails.email}</div>
                  <div className="text-gray-400">Role:</div>
                  <div className="text-white capitalize">{modalState.userDetails.role}</div>
                  <div className="text-gray-400">Status:</div>
                  <div className={`capitalize ${
                    modalState.userDetails.status === 'active' ? 'text-green-400' :
                    modalState.userDetails.status === 'banned' ? 'text-red-400' :
                    'text-yellow-400'
                  }`}>{modalState.userDetails.status}</div>
                  <div className="text-gray-400">Currency:</div>
                  <div className="text-yellow-400">{modalState.userDetails.currency}</div>
                  <div className="text-gray-400">Created:</div>
                  <div className="text-white">{new Date(modalState.userDetails.created_at).toLocaleDateString()}</div>
                </div>
                
                {modalState.userDetails.last_ip_address && (
                  <div className="bg-blue-900/30 p-3 rounded-lg border border-blue-500/30">
                    <p className="text-blue-300 text-sm">
                      <Globe className="w-4 h-4 inline mr-2" />
                      Last IP: <span className="font-mono">{modalState.userDetails.last_ip_address}</span>
                    </p>
                    {modalState.userDetails.registration_ip && modalState.userDetails.registration_ip !== modalState.userDetails.last_ip_address && (
                      <p className="text-blue-300/70 text-xs mt-1">
                        Registration IP: <span className="font-mono">{modalState.userDetails.registration_ip}</span>
                      </p>
                    )}
                  </div>
                )}

                {modalState.userDetails.data_counts && (
                  <div className="bg-purple-900/30 p-3 rounded-lg border border-purple-500/30">
                    <p className="text-purple-300 text-sm mb-2">Associated Data:</p>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="text-center">
                        <div className="text-lg text-white">{modalState.userDetails.data_counts.characters}</div>
                        <div className="text-gray-400">Characters</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg text-white">{modalState.userDetails.data_counts.forum_posts}</div>
                        <div className="text-gray-400">Forum Posts</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg text-white">{modalState.userDetails.data_counts.roleplay_posts}</div>
                        <div className="text-gray-400">RP Posts</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Add IP Ban */}
            {modalState.type === 'addIpBan' && (
              <div className="space-y-4">
                <div>
                  <Label htmlFor="ip-address" className="text-gray-300">IP Address</Label>
                  <Input
                    id="ip-address"
                    value={modalState.ipAddress || ''}
                    onChange={(e) => setModalState({ ...modalState, ipAddress: e.target.value })}
                    className="bg-black/20 border-purple-500/30 text-white font-mono"
                    placeholder="e.g., 192.168.1.1"
                  />
                </div>
                <div>
                  <Label htmlFor="ban-reason" className="text-gray-300">Reason</Label>
                  <Textarea
                    id="ban-reason"
                    value={modalState.reason || ''}
                    onChange={(e) => setModalState({ ...modalState, reason: e.target.value })}
                    rows="2"
                    className="bg-black/20 border-purple-500/30 text-white resize-none"
                    placeholder="Reason for banning this IP..."
                  />
                </div>
              </div>
            )}

            {/* Remove Account */}
            {modalState.type === 'removeAccount' && (
              <div className="space-y-4">
                <div className="bg-red-900/30 p-4 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold flex items-center gap-2">
                    <AlertCircle className="w-5 h-5" />
                    WARNING: This action cannot be undone!
                  </p>
                  <p className="text-gray-300 text-sm mt-2">
                    This will permanently delete {modalState.username}&apos;s account and ALL associated data:
                  </p>
                  <ul className="text-gray-400 text-sm mt-2 list-disc list-inside">
                    <li>All characters</li>
                    <li>All forum posts</li>
                    <li>All roleplay posts</li>
                    <li>All quest progress</li>
                    <li>All shop items</li>
                    <li>All transactions</li>
                  </ul>
                </div>
                
                <div className="flex items-center gap-3 bg-yellow-900/20 p-3 rounded-lg border border-yellow-500/30">
                  <input
                    type="checkbox"
                    id="ban-ip-checkbox"
                    checked={modalState.banIp || false}
                    onChange={(e) => setModalState({ ...modalState, banIp: e.target.checked })}
                    className="w-4 h-4 rounded border-yellow-500"
                  />
                  <Label htmlFor="ban-ip-checkbox" className="text-yellow-300 cursor-pointer">
                    Also ban their IP address (prevents re-registration)
                  </Label>
                </div>
              </div>
            )}

            {/* Standard confirmation messages */}
            {!['viewUser', 'addIpBan', 'removeAccount'].includes(modalState.type) && (
              <p className="text-gray-300">
                {modalState.type === 'reject' && `Reject application from ${modalState.username}? This will delete their account.`}
                {modalState.type === 'ban' && `Ban ${modalState.username} permanently?`}
                {modalState.type === 'suspend' && `Suspend ${modalState.username}?`}
                {modalState.type === 'promote' && `Promote ${modalState.username} to Moderator?`}
                {modalState.type === 'demote' && `Demote ${modalState.username} from Moderator?`}
                {modalState.type === 'resetPassword' && `Reset password for ${modalState.username} (${modalState.email})?`}
              </p>
            )}

            {modalState.type === 'suspend' && (
              <div>
                <Label htmlFor="suspend-days" className="text-gray-300">Days</Label>
                <Input
                  id="suspend-days"
                  type="number"
                  value={modalState.suspendDays}
                  onChange={(e) => setModalState({ ...modalState, suspendDays: e.target.value })}
                  min="1"
                  className="bg-black/20 border-purple-500/30 text-white"
                  placeholder="7"
                />
              </div>
            )}

            {(modalState.type === 'ban' || modalState.type === 'suspend') && (
              <div>
                <Label htmlFor="reason" className="text-gray-300">Reason</Label>
                <Textarea
                  id="reason"
                  value={modalState.reason}
                  onChange={(e) => setModalState({ ...modalState, reason: e.target.value })}
                  rows="3"
                  className="bg-black/20 border-purple-500/30 text-white resize-none"
                  placeholder="Enter reason..."
                />
              </div>
            )}

            {modalState.type === 'resetPassword' && (
              <div>
                <Label htmlFor="new-password" className="text-gray-300">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={modalState.newPassword || ''}
                  onChange={(e) => setModalState({ ...modalState, newPassword: e.target.value })}
                  className="bg-black/20 border-purple-500/30 text-white"
                  placeholder="Enter new password (min 6 characters)"
                  minLength={6}
                />
                <p className="text-xs text-gray-500 mt-1">
                  The user will need to use this password to log in. Share it with them securely.
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="flex gap-2">
            <Button
              onClick={() => setModalState({ ...modalState, open: false })}
              className="bg-gray-600 hover:bg-gray-700"
            >
              {modalState.type === 'viewUser' ? 'Close' : 'Cancel'}
            </Button>
            {modalState.type !== 'viewUser' && (
              <Button
                onClick={confirmAction}
                className={
                  modalState.type === 'reject' || modalState.type === 'ban' || modalState.type === 'removeAccount'
                    ? "bg-red-600 hover:bg-red-700"
                    : modalState.type === 'suspend'
                    ? "bg-yellow-600 hover:bg-yellow-700"
                    : modalState.type === 'resetPassword'
                    ? "bg-green-600 hover:bg-green-700"
                    : modalState.type === 'addIpBan'
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-blue-600 hover:bg-blue-700"
                }
              >
                {modalState.type === 'reject' && 'Reject'}
                {modalState.type === 'ban' && 'Ban'}
                {modalState.type === 'suspend' && 'Suspend'}
                {modalState.type === 'promote' && 'Promote'}
                {modalState.type === 'demote' && 'Demote'}
                {modalState.type === 'resetPassword' && 'Reset Password'}
                {modalState.type === 'removeAccount' && 'Remove Account'}
                {modalState.type === 'addIpBan' && 'Ban IP'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
