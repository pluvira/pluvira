import { writable } from 'svelte/store';
import { hasAuthToken, setAuthToken, clearAuthToken } from '$lib/utils/preferences';

export interface AuthState {
  isAuthenticated: boolean;
  username: string;
  role: 'admin' | 'user';
  authEnabled: boolean;
  isBootstrapped: boolean;
}

const hasToken = typeof window !== 'undefined' && hasAuthToken();

const defaultState: AuthState = {
  isAuthenticated: hasToken,
  username: hasToken ? 'admin' : '',
  role: 'admin',
  authEnabled: true,
  isBootstrapped: false
};

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>(defaultState);

  function clearSession() {
    clearAuthToken();
    update((state) => ({
      ...state,
      isAuthenticated: !state.authEnabled,
      username: state.authEnabled ? '' : 'admin',
      role: state.authEnabled ? 'user' : 'admin'
    }));
  }

  return {
    subscribe,
    bootstrap: (isAuthenticated: boolean, authEnabled: boolean, username = 'guest') => {
      set({
        isAuthenticated: !authEnabled || isAuthenticated,
        username: authEnabled && isAuthenticated ? username : (authEnabled ? '' : 'admin'),
        role: 'admin',
        authEnabled,
        isBootstrapped: true
      });
    },
    login: (token: string, userOrUsername: string | { username?: string; role?: 'admin' | 'user' | string } = 'admin') => {
      setAuthToken(token);
      const username = typeof userOrUsername === 'string' ? userOrUsername : (userOrUsername.username || 'admin');
      const role = (typeof userOrUsername === 'object' && userOrUsername.role ? userOrUsername.role : 'admin') as 'admin' | 'user';
      update((state) => ({
        ...state,
        isAuthenticated: true,
        username,
        role
      }));
    },
    logout: clearSession,
    reset: clearSession
  };
}

export const authStore = createAuthStore();
