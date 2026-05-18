import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const DEFAULT_TOKEN_TTL_SECONDS = 8 * 60 * 60;
const configuredTtlSeconds = Number(import.meta.env.VITE_AUTH_TOKEN_TTL_SECONDS ?? DEFAULT_TOKEN_TTL_SECONDS);
const TOKEN_TTL_MS = Number.isFinite(configuredTtlSeconds) && configuredTtlSeconds > 0
  ? configuredTtlSeconds * 1000
  : DEFAULT_TOKEN_TTL_SECONDS * 1000;

interface User {
  user_id: number;
  user_name: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  tokenExpiresAt: number | null;
  login: (user: User, token: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      tokenExpiresAt: null,
      login: (user, token) =>
        set({
          user,
          token,
          tokenExpiresAt: Date.now() + TOKEN_TTL_MS,
        }),
      logout: () => set({ user: null, token: null, tokenExpiresAt: null }),
      isAuthenticated: () => {
        const { token, tokenExpiresAt } = get();
        return Boolean(token && tokenExpiresAt && Date.now() < tokenExpiresAt);
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        if (!state?.token || !state.tokenExpiresAt || Date.now() >= state.tokenExpiresAt) {
          state?.logout();
        }
      },
    }
  )
);
