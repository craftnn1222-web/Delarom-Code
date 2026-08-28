import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getMe, logout as apiLogout, setAuthToken, getAuthToken } from '../utils/api';

/**
 * AuthContext — Bearer-token-driven session state.
 *
 * Token transport: `Authorization: Bearer <token>` header. Stored in
 * localStorage so it survives a refresh and works across cross-origin
 * deployments. The cookie path (httpOnly) is no longer used because
 * production's CORS proxy refuses credentials-include responses.
 *
 * States:
 *   loading=true                 — checking session
 *   loading=false, user=null     — anonymous
 *   loading=false, user={...}    — authenticated
 */

const AuthContext = createContext();

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = useCallback(async () => {
    // Skip the round-trip if no token AND no cookie is plausible (anonymous mount).
    if (!getAuthToken()) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }
    try {
      const response = await getMe();
      setCurrentUser(response.data);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        // Token genuinely expired/invalid — clear the local copy.
        setAuthToken(null);
        setCurrentUser(null);
      } else {
        // Network error / timeout / 5xx (e.g. backend momentarily overloaded).
        // Do NOT wipe the token — that would spuriously log the user out. Keep
        // it so the next request or a refresh recovers the session.
        setCurrentUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  // Called by Login.js after a successful POST /auth/login.
  // Token is persisted so subsequent requests carry the Authorization header.
  const login = (token, user) => {
    if (token) setAuthToken(token);
    setCurrentUser(user);
  };

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (_e) {
      // even if the network call fails, clear local state
    }
    setAuthToken(null);
    setCurrentUser(null);
  }, []);

  const value = {
    currentUser,
    login,
    logout,
    loading,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
