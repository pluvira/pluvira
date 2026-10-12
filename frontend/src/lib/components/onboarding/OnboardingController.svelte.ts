import { api } from '$lib/api/client';
import { authStore } from '$lib/stores/authStore';
import { toastStore } from '$lib/stores/toastStore';
import type { CloudPairingStatus } from '$lib/api/types';
import { formatCrockfordId } from '$lib/utils/crockfordUtils';

export interface StreamPresetOption {
  key: string;
  label: string;
  name: string;
  m3uUrl: string;
  epgUrl: string;
}

export const STREAM_PRESETS: StreamPresetOption[] = [
  {
    key: 'none',
    label: 'Custom URL (None)',
    name: '',
    m3uUrl: '',
    epgUrl: ''
  },
  {
    key: 'us',
    label: 'United States (US)',
    name: 'Public Channels US',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/us.m3u',
    epgUrl: ''
  },
  {
    key: 'uk',
    label: 'United Kingdom (UK)',
    name: 'Public Channels UK',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/uk.m3u',
    epgUrl: ''
  },
  {
    key: 'de',
    label: 'Germany (DE)',
    name: 'Public Channels DE',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/de.m3u',
    epgUrl: ''
  },
  {
    key: 'fr',
    label: 'France (FR)',
    name: 'Public Channels FR',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/fr.m3u',
    epgUrl: ''
  },
  {
    key: 'es',
    label: 'Spain (ES)',
    name: 'Public Channels ES',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/es.m3u',
    epgUrl: ''
  },
  {
    key: 'it',
    label: 'Italy (IT)',
    name: 'Public Channels IT',
    m3uUrl: 'https://iptv-org.github.io/iptv/countries/it.m3u',
    epgUrl: ''
  },
  {
    key: 'all',
    label: 'International (All)',
    name: 'Public Channels All',
    m3uUrl: 'https://iptv-org.github.io/iptv/index.m3u',
    epgUrl: ''
  }
];

export interface EpgPresetOption {
  key: string;
  label: string;
  name: string;
  url: string;
}

export const EPG_PRESETS: EpgPresetOption[] = [
  {
    key: 'none',
    label: 'Custom URL (None)',
    name: '',
    url: ''
  },
  {
    key: 'us',
    label: 'United States (US) - epgshare01',
    name: 'EPG US (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz'
  },
  {
    key: 'uk',
    label: 'United Kingdom (UK) - epgshare01',
    name: 'EPG UK (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz'
  },
  {
    key: 'de',
    label: 'Germany (DE) - epgshare01',
    name: 'EPG DE (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz'
  },
  {
    key: 'fr',
    label: 'France (FR) - epgshare01',
    name: 'EPG FR (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz'
  },
  {
    key: 'es',
    label: 'Spain (ES) - epgshare01',
    name: 'EPG ES (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz'
  },
  {
    key: 'it',
    label: 'Italy (IT) - epgshare01',
    name: 'EPG IT (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz'
  },
  {
    key: 'all',
    label: 'International (All) - epgshare01',
    name: 'EPG All (epgshare01)',
    url: 'https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz'
  }
];

export class OnboardingController {
  public currentStep = $state(1);
  public loading = $state(false);
  public selectedPresetKey = $state('none');
  public sourceName = $state('');
  public m3uUrl = $state('');
  public epgUrl = $state('');
  public errorMessage = $state<string | null>(null);
  public pairingStatus = $state<CloudPairingStatus>('idle');
  public userCode = $state<string | null>(null);
  public verificationUriComplete = $state<string | null>(null);
  public cloudUid = $state<string | null>(null);
  public formattedCloudId = $state<string | null>(null);
  public pairingError = $state<string | null>(null);
  public isPairingPolling = $state(false);
  public authEnabled = $state(false);
  public adminPassword = $state('');
  public confirmPassword = $state('');
  public selectedEpgPresetKey = $state('none');
  public epgSourceName = $state('');
  public epgGuideUrl = $state('');
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  public reset(): void {
    this.stopPairingPolling();
    this.currentStep = 1;
    this.pairingStatus = 'idle';
    this.userCode = null;
    this.verificationUriComplete = null;
    this.cloudUid = null;
    this.formattedCloudId = null;
    this.pairingError = null;
    this.errorMessage = null;
    this.authEnabled = false;
    this.adminPassword = '';
    this.confirmPassword = '';
    this.selectedEpgPresetKey = 'none';
    this.epgSourceName = '';
    this.epgGuideUrl = '';
  }

  public setStep(step: number): void {
    if (step >= 1 && step <= 5) {
      this.currentStep = step;
      this.errorMessage = null;
    }
  }

  public nextStep(): void {
    if (this.currentStep < 5) {
      this.currentStep += 1;
      this.errorMessage = null;
    }
  }

  public prevStep(): void {
    if (this.currentStep > 1) {
      this.currentStep -= 1;
      this.errorMessage = null;
    }
  }

  public selectPreset(presetKey: string): void {
    this.selectedPresetKey = presetKey;
    const preset = STREAM_PRESETS.find((p) => p.key === presetKey);
    if (preset) {
      this.sourceName = preset.name;
      this.m3uUrl = preset.m3uUrl;
      this.epgUrl = preset.epgUrl;
    }
  }

  public skipSecurityStep(): void {
    this.errorMessage = null;
    this.nextStep();
  }

  public async saveSecurityAndContinue(): Promise<boolean> {
    if (!this.authEnabled) {
      this.skipSecurityStep();
      return true;
    }

    const trimmedPassword = this.adminPassword.trim();
    if (trimmedPassword.length < 6) {
      const msg = 'Password must be at least 6 characters long.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    }

    if (this.adminPassword !== this.confirmPassword) {
      const msg = 'Passwords do not match.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    }

    this.loading = true;
    this.errorMessage = null;

    try {
      const config = await api.getConfig();
      config.auth = config.auth || {};
      config.auth.enabled = true;
      config.auth.password = this.adminPassword;

      await api.updateConfig(config);

      const username = config.auth.username || 'admin';
      const loginRes = await api.login(username, this.adminPassword);
      authStore.login(loginRes.access_token, username);

      toastStore.success('Admin password configured successfully.');
      this.nextStep();
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to update security configuration.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }

  public skipSourceStep(): void {
    this.errorMessage = null;
    this.nextStep();
  }

  public async saveSourceAndContinue(): Promise<boolean> {
    const trimmedName = this.sourceName.trim();
    const trimmedM3u = this.m3uUrl.trim();
    const trimmedEpg = this.epgUrl.trim();

    if (!trimmedName || !trimmedM3u) {
      const msg = 'Please provide both a Source Name and a valid M3U Playlist URL.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    }

    this.loading = true;
    this.errorMessage = null;

    try {
      try {
        await api.createSource({
          name: trimmedName,
          m3u_url: trimmedM3u,
          enabled: true
        });
      } catch (srcErr: any) {
        if (srcErr?.message?.includes('already exists')) {
          await api.deleteSource(trimmedName).catch(() => {});
          await api.createSource({
            name: trimmedName,
            m3u_url: trimmedM3u,
            enabled: true
          });
        } else {
          throw srcErr;
        }
      }

      if (trimmedEpg) {
        const epgName = `${trimmedName}_EPG`;
        try {
          await api.createEpgSource({
            name: epgName,
            url: trimmedEpg,
            enabled: true
          });
        } catch (epgErr: any) {
          if (epgErr?.message?.includes('already exists')) {
            await api.deleteEpgSource(epgName).catch(() => {});
            await api.createEpgSource({
              name: epgName,
              url: trimmedEpg,
              enabled: true
            });
          } else {
            throw epgErr;
          }
        }
      }

      toastStore.success(`Playlist '${trimmedName}' added successfully.`);
      this.nextStep();
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to add media source. Please verify the URL.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }

  public selectEpgPreset(presetKey: string): void {
    this.selectedEpgPresetKey = presetKey;
    const preset = EPG_PRESETS.find((p) => p.key === presetKey);
    if (preset) {
      this.epgSourceName = preset.name;
      this.epgGuideUrl = preset.url;
    }
  }

  public skipEpgStep(): void {
    this.errorMessage = null;
    this.nextStep();
  }

  public async saveEpgAndContinue(): Promise<boolean> {
    const trimmedName = this.epgSourceName.trim();
    const trimmedUrl = this.epgGuideUrl.trim();

    if (!trimmedName || !trimmedUrl) {
      const msg = 'Please provide both an EPG Source Name and a valid Guide URL.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    }

    this.loading = true;
    this.errorMessage = null;

    try {
      try {
        await api.createEpgSource({
          name: trimmedName,
          url: trimmedUrl,
          enabled: true
        });
      } catch (epgErr: any) {
        if (epgErr?.message?.includes('already exists')) {
          await api.deleteEpgSource(trimmedName).catch(() => {});
          await api.createEpgSource({
            name: trimmedName,
            url: trimmedUrl,
            enabled: true
          });
        } else {
          throw epgErr;
        }
      }

      toastStore.success(`EPG Guide '${trimmedName}' added successfully.`);
      this.nextStep();
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to add EPG guide source. Please verify the URL.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }

  public stopPairingPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.isPairingPolling = false;
  }

  public async startCloudPairing(): Promise<boolean> {
    this.loading = true;
    this.pairingError = null;
    this.stopPairingPolling();

    try {
      const res = await api.startCloudPairing();
      this.userCode = res.user_code;
      this.verificationUriComplete = res.verification_uri_complete;
      this.pairingStatus = 'pending';

      if (typeof window !== 'undefined' && res.verification_uri_complete) {
        window.open(res.verification_uri_complete, '_blank');
      }

      this.startPairingPolling(res.interval || 5);
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to start device pairing with Pluvira Cloud.';
      this.pairingError = msg;
      this.pairingStatus = 'failed';
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }

  public startPairingPolling(intervalSec = 5): void {
    this.stopPairingPolling();
    this.isPairingPolling = true;

    const intervalMs = Math.max(3000, intervalSec * 1000);
    this.pollTimer = setInterval(async () => {
      await this.checkPairingStatus();
    }, intervalMs);
  }

  public async checkPairingStatus(): Promise<void> {
    try {
      const res = await api.getCloudPairingStatus();
      if (res.status === 'success') {
        this.pairingStatus = 'success';
        this.cloudUid = res.uid || null;
        this.formattedCloudId = res.formatted_id || (res.uid ? formatCrockfordId(res.uid) : null);
        this.stopPairingPolling();
        toastStore.success(`Device paired successfully! UID: ${this.formattedCloudId || this.cloudUid}`);
      } else if (res.status === 'expired' || res.status === 'denied' || res.status === 'failed') {
        this.pairingStatus = res.status;
        this.pairingError = res.error_message || `Device pairing ${res.status}.`;
        this.stopPairingPolling();
      }
    } catch {
      // Retry on transient poll error
    }
  }

  public async cancelCloudPairing(): Promise<void> {
    this.stopPairingPolling();
    try {
      await api.cancelCloudPairing();
    } catch {
      // Ignore network cancellation error
    }
    this.pairingStatus = 'idle';
    this.userCode = null;
    this.verificationUriComplete = null;
    this.pairingError = null;
  }

  public async completeOnboarding(onSuccess?: () => void): Promise<boolean> {
    this.stopPairingPolling();
    this.loading = true;
    this.errorMessage = null;

    try {
      const config = await api.getConfig();
      config.settings = config.settings || {};
      config.settings.onboarding_completed = true;

      await api.updateConfig(config);
      toastStore.success('Welcome to Pluvira! Configuration completed successfully.');

      try {
        const sources = await api.getSources();
        if (sources && sources.length > 0) {
          await api.triggerUpdate('full').catch(() => {});
        }
      } catch {
        // Non-blocking background sync
      }

      if (onSuccess) {
        onSuccess();
      }
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to save onboarding configuration state.';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }
}
