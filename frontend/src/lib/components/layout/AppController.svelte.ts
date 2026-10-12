import { api } from '$lib/api/client';
import { authStore } from '$lib/stores/authStore';
import { licenseStore } from '$lib/stores/licenseStore';
import { initTheme } from '$lib/utils/themeUtils';
import type { EditionType, LicenseDetails } from '$lib/api/types';

export class AppController {
  public currentPath = $state(typeof window !== 'undefined' ? window.location.hash || '#/live' : '#/live');
  public isRunning = $state(false);
  public isAuthenticated = $state(false);
  public isBootstrapped = $state(false);
  public authEnabled = $state(false);
  public isPro = $state(false);
  public edition = $state<EditionType>('core');
  public licenseDetails = $state<LicenseDetails | null>(null);
  public supportedCommands = $state<string[]>([]);
  public supportedModules = $state<string[]>([]);
  public showOnboarding = $state(false);
  public onboardingCompleted = $state(true);

  public isAuthorized = $derived(!this.authEnabled || this.isAuthenticated);

  private unsubscribeAuth: (() => void) | null = null;
  private statusPollTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.unsubscribeAuth = authStore.subscribe((state) => {
      this.isAuthenticated = state.isAuthenticated;
    });
  }

  public init(): void {
    initTheme();
    this.handleHashChange();
    this.bootstrapSession();
  }

  public destroy(): void {
    this.stopRunningPoll();
    if (this.unsubscribeAuth) {
      this.unsubscribeAuth();
      this.unsubscribeAuth = null;
    }
  }

  public handleHashChange = (): void => {
    if (typeof window === 'undefined') return;
    let rawPath = window.location.hash || '#/live';
    if (rawPath === '#/' || rawPath === '') {
      window.history.replaceState(null, '', '#/live');
      rawPath = '#/live';
    }

    this.currentPath = rawPath;
    if (this.currentPath === '#/login') {
      this.authEnabled = true;
      this.isAuthenticated = false;
      authStore.logout();
    }
  };

  public refreshStatus = async (): Promise<void> => {
    try {
      const sysStatus = await api.getSystemStatus();
      if (sysStatus) {
        this.isPro = Boolean(sysStatus.pro_active);
        this.isRunning = Boolean(sysStatus.is_running);
        this.edition = sysStatus.edition || (sysStatus.pro_active ? 'pro' : 'core');
        this.licenseDetails = sysStatus.license || null;
        this.supportedCommands = sysStatus.supported_commands || [];
        this.supportedModules = sysStatus.supported_modules || [];
        licenseStore.updateFromSystemStatus(sysStatus);
      }
    } catch {
      // Ignored
    }
  };

  public startRunningPoll = (): void => {
    if (this.statusPollTimer) return;
    this.statusPollTimer = setInterval(async () => {
      try {
        const sysStatus = await api.getSystemStatus();
        if (sysStatus) {
          this.isRunning = Boolean(sysStatus.is_running);
          this.edition = sysStatus.edition || (sysStatus.pro_active ? 'pro' : 'core');
          this.isPro = Boolean(sysStatus.pro_active);
          this.licenseDetails = sysStatus.license || null;
          licenseStore.updateFromSystemStatus(sysStatus);
          if (!this.isRunning) {
            this.stopRunningPoll();
          }
        }
      } catch {
        // Ignored
      }
    }, 2000);
  };

  public stopRunningPoll = (): void => {
    if (this.statusPollTimer) {
      clearInterval(this.statusPollTimer);
      this.statusPollTimer = null;
    }
  };

  public handleTriggerUpdate = async (mode: string): Promise<void> => {
    this.isRunning = true;
    this.startRunningPoll();
    try {
      await api.triggerUpdate(mode);
    } catch {
      setTimeout(async () => {
        const st = await api.getSystemStatus().catch(() => null);
        if (st) {
          this.isRunning = Boolean(st.is_running);
          this.edition = st.edition || (st.pro_active ? 'pro' : 'core');
          this.isPro = Boolean(st.pro_active);
          this.licenseDetails = st.license || null;
          licenseStore.updateFromSystemStatus(st);
        }
        if (!this.isRunning) this.stopRunningPoll();
      }, 1000);
    }
  };

  public handleLogout = (): void => {
    authStore.logout();
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  public handleOnboardingComplete = (): void => {
    this.onboardingCompleted = true;
    this.showOnboarding = false;
  };

  public bootstrapSession = async (): Promise<void> => {
    try {
      const [status, sysStatus, config] = await Promise.all([
        api.getAuthStatus(),
        api.getSystemStatus().catch(() => null),
        api.getConfig().catch(() => null)
      ]);
      if (sysStatus) {
        this.isPro = Boolean(sysStatus.pro_active);
        this.isRunning = Boolean(sysStatus.is_running);
        this.edition = sysStatus.edition || (sysStatus.pro_active ? 'pro' : 'core');
        this.licenseDetails = sysStatus.license || null;
        this.supportedCommands = sysStatus.supported_commands || [];
        this.supportedModules = sysStatus.supported_modules || [];
        licenseStore.updateFromSystemStatus(sysStatus);
        if (this.isRunning) {
          this.startRunningPoll();
        }
      }
      if (config?.settings?.onboarding_completed === true) {
        this.onboardingCompleted = true;
        this.showOnboarding = false;
      } else {
        this.onboardingCompleted = false;
        this.showOnboarding = true;
      }
      const isAuth = Boolean(status.authenticated);
      const isEnabled = Boolean(status.auth_enabled);
      this.authEnabled = isEnabled;
      authStore.bootstrap(isAuth, isEnabled, status.username || 'guest');
    } catch (err: any) {
      console.warn('Auth check failed:', err);
      if (err?.message?.includes('401') || err?.status === 401) {
        this.authEnabled = true;
        authStore.bootstrap(false, true, 'guest');
        if (typeof window !== 'undefined' && window.location.hash !== '#/login') {
          window.location.hash = '#/login';
        }
      } else {
        this.authEnabled = false;
        authStore.bootstrap(true, false, 'admin');
      }
    } finally {
      this.isBootstrapped = true;
    }
  };
}
