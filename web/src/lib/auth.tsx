"use client";

import React, { createContext, useContext, useState, useEffect, useTransition } from "react";

export type UserRole = "official" | "admin";

export interface UserProfile {
  username: string;
  name: string;
  email?: string;
  department?: string;
  badge_id?: string;
  role: UserRole;
  token?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoaded: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isOfficial: boolean;
  notification: string | null;
  clearNotification: () => void;
  login: (username: string, password?: string) => Promise<{ success: boolean; error?: string }>;
  loginAs: (role: UserRole) => Promise<boolean>;
  register: (profileData: {
    username: string;
    password: string;
    name?: string;
    email?: string;
    department?: string;
    badge_id?: string;
    role: UserRole;
    admin_passkey?: string;
  }) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

export const DEFAULT_OFFICIAL: UserProfile = {
  username: "official",
  name: "Shri A. K. Sharma",
  email: "official@pmksy.gov.in",
  department: "WDC-PMKSY Technical Field Operations",
  badge_id: "OFF-8821",
  role: "official",
};

export const DEFAULT_ADMIN: UserProfile = {
  username: "admin",
  name: "Dr. Sunita Deshmukh",
  email: "auditor.general@watershed.gov.in",
  department: "Directorate of Watershed Development & Statutory Audit",
  badge_id: "DIR-0001",
  role: "admin",
};

const STORAGE_KEY = "ws_auth_session";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Start with null on both server and client to guarantee zero hydration mismatch
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const [, startTransition] = useTransition();

  // Load session strictly on client mount to prevent hydration discrepancy
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed?.user) {
          setUser(parsed.user);
          setToken(parsed.token || null);
        }
      }
    } catch {
      // ignore
    } finally {
      setIsLoaded(true);
    }
  }, []);

  // Automatically clear notifications after 5 seconds
  useEffect(() => {
    if (!notification) return;
    const timer = setTimeout(() => {
      setNotification(null);
    }, 5000);
    return () => clearTimeout(timer);
  }, [notification]);

  function clearNotification() {
    setNotification(null);
  }

  // Save or clear session
  function persistSession(nextUser: UserProfile | null, nextToken: string | null) {
    const prevUser = user;
    setUser(nextUser);
    setToken(nextToken);

    if (nextUser && prevUser && prevUser.username !== nextUser.username) {
      setNotification(`Switched active session: ${prevUser.name} → ${nextUser.name} (${nextUser.role.toUpperCase()})`);
    } else if (nextUser && !prevUser) {
      setNotification(`Authenticated as ${nextUser.name} (${nextUser.role.toUpperCase()})`);
    } else if (!nextUser && prevUser) {
      setNotification(`Logged out: Ended session for ${prevUser.name}`);
    }

    try {
      if (nextUser && nextToken) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: nextUser, token: nextToken }));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }

  async function login(username: string, password?: string): Promise<{ success: boolean; error?: string }> {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok || !data.user) {
        return { success: false, error: data.error || "Authentication failed" };
      }
      startTransition(() => {
        persistSession(data.user, data.token || null);
      });
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  }

  async function loginAs(role: UserRole): Promise<boolean> {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.user) {
          startTransition(() => {
            persistSession(data.user, data.token || null);
          });
          return true;
        }
      }
    } catch {
      // Offline fallback: switch local role directly
    }

    // Client-side fallback if server unreachable
    const fallbackUser = role === "admin" ? DEFAULT_ADMIN : DEFAULT_OFFICIAL;
    startTransition(() => {
      persistSession(fallbackUser, `session_${role}_${Date.now()}`);
    });
    return true;
  }

  async function register(profileData: {
    username: string;
    password: string;
    name?: string;
    email?: string;
    department?: string;
    badge_id?: string;
    role: UserRole;
    admin_passkey?: string;
  }): Promise<{ success: boolean; error?: string }> {
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileData),
      });
      const data = await res.json();
      if (!res.ok || !data.user) {
        return { success: false, error: data.error || "Profile registration failed" };
      }
      startTransition(() => {
        persistSession(data.user, data.token || null);
      });
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  }

  function logout() {
    startTransition(() => {
      persistSession(null, null);
    });
  }

  const isAuthenticated = user !== null;
  const isAdmin = user?.role === "admin";
  const isOfficial = user?.role === "official";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoaded,
        isAuthenticated,
        isAdmin,
        isOfficial,
        notification,
        clearNotification,
        login,
        loginAs,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
