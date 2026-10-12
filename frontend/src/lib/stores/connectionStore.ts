import { writable } from 'svelte/store';
import { toastStore } from './toastStore';

export interface ConnectionState {
  isConnected: boolean;
  isDegraded: boolean;
  lastChecked: number | null;
  consecutiveFailures: number;
  lastErrorMessage: string | null;
  lastStatusCode: number | null;
  lastFailedUrl: string | null;
  failedAt: number | null;
  troubleshootingTips: string[];
}

const defaultState: ConnectionState = {
  isConnected: true,
  isDegraded: false,
  lastChecked: null,
  consecutiveFailures: 0,
  lastErrorMessage: null,
  lastStatusCode: null,
  lastFailedUrl: null,
  failedAt: null,
  troubleshootingTips: []
};

function getTroubleshootingTips(statusCode: number | null): string[] {
  const tips: string[] = [];

  if (!statusCode || statusCode === 0) {
    tips.push('Verify that the Pluvira backend container or Python daemon is running.');
    tips.push('Check that port 8000 (or configured API port) is accessible and not blocked by firewall.');
    tips.push('Ensure reverse proxy (e.g. Nginx, Traefik) is correctly forwarding /api/v1 routes.');
  } else if (statusCode >= 500) {
    tips.push(`Backend returned internal server error (HTTP ${statusCode}). Inspect Docker or system logs.`);
    tips.push('Verify SQLite database file permissions and RAM disk directory /dev/shm/pluvira availability.');
  } else if (statusCode === 401 || statusCode === 403) {
    tips.push('Authentication or session issue. Try logging in again.');
  } else {
    tips.push(`HTTP ${statusCode} response received. Check endpoint configuration.`);
  }

  return tips;
}

function createConnectionStore() {
  const { subscribe, set, update } = writable<ConnectionState>(defaultState);

  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  return {
    subscribe,
    setConnected: (
      connected: boolean,
      diagnostic?: {
        errorMessage?: string | null;
        statusCode?: number | null;
        failedUrl?: string | null;
      }
    ) => {
      update((state) => {
        const wasConnected = state.isConnected;
        const now = Date.now();

        if (connected) {
          if (!wasConnected) {
            toastStore.success('Server connection restored');
          }
          return {
            isConnected: true,
            isDegraded: false,
            lastChecked: now,
            consecutiveFailures: 0,
            lastErrorMessage: null,
            lastStatusCode: null,
            lastFailedUrl: null,
            failedAt: null,
            troubleshootingTips: []
          };
        } else {
          const newFailures = state.consecutiveFailures + 1;
          const errorMsg = diagnostic?.errorMessage || 'Backend service is unreachable';
          const statusCode = diagnostic?.statusCode ?? null;
          const failedUrl = diagnostic?.failedUrl || null;
          const tips = getTroubleshootingTips(statusCode);

          if (wasConnected) {
            toastStore.error('Backend connection lost. Check server status.');
          }
          return {
            isConnected: false,
            isDegraded: true,
            lastChecked: now,
            consecutiveFailures: newFailures,
            lastErrorMessage: errorMsg,
            lastStatusCode: statusCode,
            lastFailedUrl: failedUrl,
            failedAt: state.failedAt || now,
            troubleshootingTips: tips
          };
        }
      });
    },
    checkHeartbeat: async (healthCheckUrl = '/api/v1/health') => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const res = await fetch(healthCheckUrl, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (res.ok) {
          connectionStore.setConnected(true);
          return true;
        } else {
          connectionStore.setConnected(false, {
            errorMessage: `Health check responded with HTTP ${res.status}`,
            statusCode: res.status,
            failedUrl: healthCheckUrl
          });
          return false;
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Network request failed';
        connectionStore.setConnected(false, {
          errorMessage: `Network failure reaching ${healthCheckUrl}: ${errorMsg}`,
          statusCode: 0,
          failedUrl: healthCheckUrl
        });
        return false;
      }
    },
    startHeartbeat: (intervalMs = 15000, healthCheckUrl = '/api/v1/health') => {
      if (typeof window === 'undefined') return;
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      connectionStore.checkHeartbeat(healthCheckUrl);
      heartbeatTimer = setInterval(() => {
        connectionStore.checkHeartbeat(healthCheckUrl);
      }, intervalMs);
    },
    stopHeartbeat: () => {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    },
    reset: () => {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
      set(defaultState);
    }
  };
}

export const connectionStore = createConnectionStore();
