import { create } from 'zustand';
import type { Language, User } from '../types';
import { api, clearTokens, getStoredTokens } from '../services/api';

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  fetchMe: () => Promise<User | null>;
  setUser: (user: User | null) => void;
  logout: () => Promise<void>;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  initialized: false,

  isAuthenticated: () => Boolean(getStoredTokens()),

  fetchMe: async () => {
    if (!getStoredTokens()) {
      set({ user: null, initialized: true, loading: false });
      return null;
    }
    set({ loading: true });
    try {
      const resp = await api.get<User>('/users/me');
      set({ user: resp.data, initialized: true, loading: false });
      return resp.data;
    } catch {
      // /auth/me works even with must_change_password; /users/me does not
      try {
        const resp = await api.get<User>('/auth/me');
        set({ user: resp.data, initialized: true, loading: false });
        return resp.data;
      } catch {
        set({ user: null, initialized: true, loading: false });
        return null;
      }
    }
  },

  setUser: (user) => set({ user }),

  logout: async () => {
    const refresh = getStoredTokens()?.refresh_token;
    try {
      if (refresh) await api.post('/auth/logout', { refresh_token: refresh });
    } catch {
      // ignore: local logout must always succeed
    }
    clearTokens();
    set({ user: null });
  },
}));

export function preferredLanguage(user: User | null): Language {
  return user?.preferred_language || 'uz-Latn';
}
