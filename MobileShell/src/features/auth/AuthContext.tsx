import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, configureApiAuth } from "../../shared/api/client";
import { clearStoredTokens, getStoredTokens, setStoredTokens } from "../../shared/storage/tokenStorage";
import { Tokens, UserProfile } from "../../shared/types";

type AuthContextValue = {
  loading: boolean;
  user: UserProfile | null;
  tokens: Tokens | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);

  const setTokensPersisted = async (newTokens: Tokens | null) => {
    setTokens(newTokens);
    if (newTokens) {
      await setStoredTokens(newTokens);
    } else {
      await clearStoredTokens();
    }
  };

  useEffect(() => {
    configureApiAuth({
      getTokens: () => tokens,
      setTokens: setTokensPersisted,
    });
  }, [tokens]);

  const fetchMe = async (accessToken?: string) => {
    const res = await api.get<UserProfile>("/auth/me/", {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    });
    setUser(res.data);
  };

  useEffect(() => {
    (async () => {
      try {
        const stored = await getStoredTokens();
        if (stored) {
          setTokens(stored);
          await fetchMe(stored.access);
        }
      } catch {
        setUser(null);
        await setTokensPersisted(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api.post<Tokens>("/auth/token/", { username, password });
    await setTokensPersisted(res.data);
    await fetchMe(res.data.access);
  };

  const logout = async () => {
    setUser(null);
    await setTokensPersisted(null);
  };

  const value = useMemo(
    () => ({
      loading,
      user,
      tokens,
      login,
      logout,
    }),
    [loading, user, tokens]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
