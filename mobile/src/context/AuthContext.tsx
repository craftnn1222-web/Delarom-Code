// Auth session state for the whole app. Token is persisted in SecureStore
// under TOKEN_KEY; the API client reads the same key on every request. On cold
// start we hydrate the user from GET /auth/me if a token exists.

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { AuthApi, User } from "@/src/api";
import { TOKEN_KEY } from "@/src/api/client";
import { storage } from "@/src/utils/storage";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signIn: (token: string, user: User) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const hydrate = useCallback(async () => {
    const token = await storage.secureGet(TOKEN_KEY, "");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await AuthApi.me();
      setUser(me);
    } catch {
      await storage.secureRemove(TOKEN_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const signIn = useCallback(async (token: string, nextUser: User) => {
    await storage.secureSet(TOKEN_KEY, token);
    setUser(nextUser);
  }, []);

  const signOut = useCallback(async () => {
    await storage.secureRemove(TOKEN_KEY);
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const me = await AuthApi.me();
      setUser(me);
    } catch {
      // keep existing state on transient failures
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, signIn, signOut, refresh }),
    [user, loading, signIn, signOut, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
