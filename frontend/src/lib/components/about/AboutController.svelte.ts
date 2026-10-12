import { api } from '$lib/api/client';
import type { EnvironmentInfo, SystemStatus, CloudAccountInfo, LicenseResponse, LicenseDetails } from '$lib/api/types';
import { copyToClipboard } from '$lib/utils/clipboardUtils';
import { licenseStore } from '$lib/stores/licenseStore';
import { get } from 'svelte/store';

export class AboutController {
  public version = $state('0.1.0');
  public gitHash = $state<string | null>(null);
  public proVersion = $state<string | null>(null);
  public environment = $state<EnvironmentInfo | null>(null);
  public systemStatus = $state<SystemStatus | null>(null);
  public cloudAccount = $state<CloudAccountInfo | null>(null);
  public licenseData = $state<LicenseResponse | null>(null);
  public loading = $state(false);
  public copied = $state(false);
  public hwidCopied = $state(false);
  private copyTimer: ReturnType<typeof setTimeout> | null = null;
  private hwidTimer: ReturnType<typeof setTimeout> | null = null;

  public get formattedVersion(): string {
    const clean = (this.version || '-.-.-').replace(/^v/, '');
    return `v${clean}`;
  }

  public get effectiveLicense(): LicenseDetails | null {
    return this.licenseData?.license || this.systemStatus?.license || get(licenseStore).licenseDetails || null;
  }

  public get isRegistered(): boolean {
    return Boolean(this.cloudAccount?.uid || this.systemStatus?.crockford_id);
  }

  public get effectiveEdition(): string {
    const customName = this.effectiveLicense?.display_name_full;
    if (customName && customName.trim()) {
      return customName.trim().toUpperCase();
    }
    const tier = (this.effectiveLicense?.tier || (this.isPro ? 'pro' : (this.isRegistered ? 'free' : 'core'))).toLowerCase();
    if (tier === 'free') {
      return 'FREE REGISTERED';
    }
    if (tier && tier !== 'core') {
      return tier.toUpperCase();
    }
    if (this.licenseData?.edition === 'pro' || this.systemStatus?.edition === 'pro' || get(licenseStore).isPro) {
      return 'PRO';
    }
    return 'CORE';
  }

  public get isPro(): boolean {
    return Boolean(this.licenseData?.pro_active || this.systemStatus?.pro_active || get(licenseStore).isPro);
  }

  public get licenseExpiryDate(): string | null {
    const lic = this.effectiveLicense;
    if (!lic?.expires_at) return null;
    try {
      return new Date(lic.expires_at * 1000).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return null;
    }
  }

  public get licenseDaysRemaining(): number | null {
    return this.effectiveLicense?.days_remaining ?? null;
  }

  public get webrtcStatus(): string {
    const storeState = get(licenseStore);
    if (storeState.webrtcStatus && storeState.webrtcStatus !== 'disabled') {
      return storeState.webrtcStatus;
    }
    if (this.systemStatus?.webrtc_status && this.systemStatus.webrtc_status !== 'disabled') {
      return this.systemStatus.webrtc_status;
    }
    if (this.isPro) {
      return 'standby';
    }
    return 'disabled';
  }

  public get deviceHash(): string | null {
    return this.systemStatus?.device_hash || this.cloudAccount?.device_hash || null;
  }

  public get shortDeviceHash(): string {
    const hash = this.deviceHash;
    if (!hash) return '----';
    return `${hash.slice(0, 8)}...`;
  }

  public async copyHwid(): Promise<void> {
    const hash = this.deviceHash;
    if (!hash) return;
    const success = await copyToClipboard(hash);
    if (success) {
      this.hwidCopied = true;
      if (this.hwidTimer) clearTimeout(this.hwidTimer);
      this.hwidTimer = setTimeout(() => {
        this.hwidCopied = false;
      }, 2000);
    }
  }

  public async copyDiagnosticsReport(): Promise<void> {
    const text = [
      '### Pluvira System Diagnostics',
      `- Core Version: ${this.formattedVersion} (${this.gitHash || 'release'})`,
      `- Pro Engine Version: ${this.proVersion ? 'v' + this.proVersion : 'Not Available (Core Edition)'}`,
      `- Runtime Edition: ${this.effectiveEdition} EDITION`,
      `- License Expiry: ${this.licenseExpiryDate ? this.licenseExpiryDate + (this.licenseDaysRemaining !== null ? ` (${this.licenseDaysRemaining}d remaining)` : '') : (this.isPro ? 'Active' : 'N/A (Core Edition)')}`,
      `- Task Runner State: ${this.systemStatus?.status || 'Idle'} (${this.systemStatus?.mode || 'idle'})`,
      ...(Boolean((import.meta as any).env?.DEV) ? [`- WebRTC Tunnel: ${this.webrtcStatus}`] : []),
      `- Anonymous UID: ${this.cloudAccount?.formatted_id || this.cloudAccount?.uid || this.systemStatus?.crockford_id || 'Unregistered'}`,
      `- Appliance Fingerprint: ${this.deviceHash ? this.deviceHash + ' (data/.instance_id)' : 'Not Available'}`,
      `- Config Path: ${this.environment?.config_path || 'config/config.yaml'}`,
      `- Data Path: ${this.environment?.data_dir || 'data/'}`,
      `- RAM Disk Path: ${this.environment?.temp_dir || '/dev/shm/pluvira'}`
    ].join('\n');

    const success = await copyToClipboard(text);
    if (success) {
      this.copied = true;
      if (this.copyTimer) clearTimeout(this.copyTimer);
      this.copyTimer = setTimeout(() => {
        this.copied = false;
      }, 2000);
    }
  }

  public async loadVersion(): Promise<void> {
    this.loading = true;
    try {
      const [health, status, cloud, lic] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getSystemStatus().catch(() => null),
        api.getCloudAccount().catch(() => null),
        api.getLicense().catch(() => null)
      ]);
      if (health?.version) {
        this.version = health.version;
      }
      if (health?.git_hash) {
        this.gitHash = health.git_hash;
      } else if (status?.environment?.git_hash) {
        this.gitHash = status.environment.git_hash;
      }
      const proVer = status?.pro_version || status?.license?.pro_version || lic?.license?.pro_version;
      if (proVer) {
        this.proVersion = String(proVer).replace(/^v/, '');
      } else if (status?.edition === 'pro' || status?.pro_active || lic?.pro_active) {
        this.proVersion = (this.version || '1.0.0').replace(/^v/, '');
      }
      if (status?.environment) {
        this.environment = status.environment;
      }
      if (status) {
        this.systemStatus = status;
      }
      if (cloud) {
        this.cloudAccount = cloud;
      }
      if (lic) {
        this.licenseData = lic;
      }
    } catch {
      // Retain fallback
    } finally {
      this.loading = false;
    }
  }
}
