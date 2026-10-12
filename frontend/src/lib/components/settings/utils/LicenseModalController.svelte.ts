import { api, ApiError } from '$lib/api/client';
import type { LicenseResponse, LicenseDetails, CloudPairingStatus } from '$lib/api/types';
import { copyToClipboard } from '$lib/utils/clipboardUtils';
import { licenseStore } from '$lib/stores/licenseStore';
import { toastStore } from '$lib/stores/toastStore';
import { getCloudUrl } from '$lib/utils/cloudUrls';

export type LicenseModalTab = 'status' | 'manual' | 'sync' | 'trial';

export class LicenseModalController {
  public activeTab = $state<LicenseModalTab>('status');
  public manualToken = $state('');
  public loading = $state(false);
  public actionLoading = $state(false);
  public errorMessage = $state<string | null>(null);
  public licenseData = $state<LicenseResponse | null>(null);
  public hasClaimedTrial = $state(false);
  public pairingStatus = $state<CloudPairingStatus>('idle');
  public userCode = $state<string | null>(null);
  public verificationUriComplete = $state<string | null>(null);
  public pairingError = $state<string | null>(null);
  public isPairingPolling = $state(false);
  public uuidError = $state(false);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  public licenseDetails = $derived<LicenseDetails | null>(this.licenseData?.license ?? null);
  public isPro = $derived(this.licenseData?.pro_active ?? false);
  public isTrial = $derived(Boolean(this.licenseDetails?.is_trial));
  public isExpiringSoon = $derived(this.licenseDetails?.license_status === 'expiring_soon');
  public isExpired = $derived(
    this.licenseDetails?.license_status === 'expired' ||
    this.licenseDetails?.error_code === 'LICENSE_EXPIRED'
  );
  public isTrialClaimed = $derived(this.hasClaimedTrial || Boolean(this.licenseDetails?.has_claimed_trial) || (this.isTrial && this.isExpired));
  public daysRemaining = $derived(this.licenseDetails?.days_remaining ?? 0);
  public managedByEnv = $derived(Boolean(this.licenseDetails?.managed_by_env));
  public crockfordId = $derived(this.licenseDetails?.crockford_id || '');
  public modules = $derived(this.licenseDetails?.modules || []);
  public proVersion = $derived(this.licenseDetails?.pro_version || '');
  public isCloudLinked = $derived(
    Boolean(this.licenseDetails?.cloud_account_linked) || Boolean(this.licenseDetails?.crockford_id)
  );
  public tier = $derived((this.licenseDetails?.tier || (this.isPro ? 'pro' : 'core')).toLowerCase());
  public compactName = $derived(
    this.licenseDetails?.compact_name ||
    (this.isTrial ? 'TRIAL' : (this.tier === 'pro' ? 'PRO' : (this.tier === 'free' ? 'FREE' : (this.tier === 'core' ? 'CORE' : this.tier.toUpperCase()))))
  );
  public tierDisplayName = $derived(
    this.licenseDetails?.display_name_full ||
    (this.isTrial ? '14-Day Pro Trial' : (this.tier === 'pro' ? 'Pro Edition' : (this.tier === 'free' ? 'Free Registered' : (this.tier === 'core' ? 'Core Free' : this.tier.charAt(0).toUpperCase() + this.tier.slice(1)))))
  );
  public badgeIcon = $derived(this.licenseDetails?.badge_icon || (this.tier === 'free' ? 'user-check' : 'sparkles'));
  public badgeTextColor = $derived(this.licenseDetails?.badge_text_color || (this.tier === 'free' ? '#ffffff' : null));
  public badgeColor = $derived(this.licenseDetails?.badge_color || null);
  public maxIps = $derived(this.licenseDetails?.max_ips || (this.isPro ? 20 : 2));
  public maxSlots = $derived(this.licenseDetails?.max_slots || (this.isPro ? 7 : 2));
  public backupMaxSlots = $derived(this.licenseDetails?.backup_max_slots ?? null);

  public setTab(tab: LicenseModalTab): void {
    if (tab !== 'sync') {
      this.stopPairingPolling();
    }
    this.activeTab = tab;
    this.errorMessage = null;
  }

  public async loadLicenseDetails(): Promise<void> {
    this.loading = true;
    this.errorMessage = null;
    try {
      const res = await api.getLicense();
      this.licenseData = res;
      licenseStore.updateFromLicenseResponse(res);
      if (res.license?.has_claimed_trial || (res.license?.is_trial && res.license?.license_status === 'expired')) {
        this.hasClaimedTrial = true;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load license details';
      this.errorMessage = msg;
    } finally {
      this.loading = false;
    }
  }

  public async activateToken(): Promise<boolean> {
    const token = this.manualToken.trim();
    if (!token) {
      this.errorMessage = 'Please enter a valid Ed25519 license token.';
      return false;
    }

    this.actionLoading = true;
    this.errorMessage = null;
    this.uuidError = false;
    try {
      const res = await api.activateLicenseToken(token);
      if (res.success || res.license?.valid) {
        toastStore.success('License activated successfully! Pro capabilities unlocked.');
        this.manualToken = '';
        await this.loadLicenseDetails();
        this.activeTab = 'status';
        return true;
      } else {
        this.errorMessage = res.message || 'Invalid or expired license token.';
        toastStore.error(this.errorMessage);
        return false;
      }
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === 'LICENSE_KEY_INSERTED_INSTEAD_OF_TOKEN') {
        this.uuidError = true;
        this.errorMessage = "You entered a License Key (UUID). Please paste the cryptographic Ed25519 Token (starts with 'eyJhbGciOi...').";
      } else if (err instanceof ApiError && err.status === 403) {
        this.errorMessage = 'License verification rejected by server or cloud authority.';
      } else {
        this.errorMessage = err instanceof Error ? err.message : 'Failed to activate license.';
      }
      toastStore.error(this.errorMessage);
      return false;
    } finally {
      this.actionLoading = false;
    }
  }

  public async claimTrial(): Promise<boolean> {
    this.actionLoading = true;
    this.errorMessage = null;
    try {
      const res = await api.activateTrial();
      if (res.success || res.license?.valid) {
        toastStore.success('14-day Pro trial activated! Enjoy unlimited channels & failover.');
        await this.loadLicenseDetails();
        this.activeTab = 'status';
        return true;
      } else {
        this.errorMessage = res.message || 'Unable to activate trial.';
        toastStore.error(this.errorMessage);
        return false;
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        this.hasClaimedTrial = true;
        this.errorMessage = 'The 14-day Pro trial has already been claimed on this system.';
      } else {
        this.errorMessage = err instanceof Error ? err.message : 'Trial activation failed.';
      }
      toastStore.error(this.errorMessage);
      return false;
    } finally {
      this.actionLoading = false;
    }
  }

  public async refreshHandshake(): Promise<void> {
    this.actionLoading = true;
    try {
      const res = await api.refreshLicenseStatus();
      this.licenseData = res;
      licenseStore.updateFromLicenseResponse(res);
      toastStore.success('License handshake refreshed.');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh handshake.';
      toastStore.error(msg);
    } finally {
      this.actionLoading = false;
    }
  }

  public async copyCrockfordId(): Promise<void> {
    if (!this.crockfordId) return;
    const success = await copyToClipboard(this.crockfordId);
    if (success) {
      toastStore.info(`Copied UID ${this.crockfordId} to clipboard.`);
    }
  }

  public async syncFromCloud(): Promise<boolean> {
    this.actionLoading = true;
    this.errorMessage = null;
    try {
      const res = await api.syncCloudLicense();
      if (res.license || res.success) {
        await this.loadLicenseDetails();
        toastStore.success(res.message || 'License synchronized successfully.');
        return true;
      }
      const msg = res.message || 'No active Pro license found for this account.';
      this.errorMessage = msg;
      toastStore.info(msg);
      return false;
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === 'NO_ACTIVE_LICENSE_FOUND') {
        const msg = err.message || 'No active Pro license found for this account.';
        this.errorMessage = msg;
        toastStore.info(msg);
      } else if (err instanceof ApiError && err.errorCode === 'DEVICE_REVOKED') {
        const msg = 'Device authorization was revoked from the cloud portal. Please repeat pairing.';
        this.errorMessage = msg;
        toastStore.error(msg);
        await this.loadLicenseDetails();
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to synchronize license from cloud.';
        this.errorMessage = msg;
        toastStore.error(msg);
      }
      return false;
    } finally {
      this.actionLoading = false;
    }
  }

  public stopPairingPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.isPairingPolling = false;
  }

  public async startPairingFlow(): Promise<boolean> {
    this.actionLoading = true;
    this.pairingError = null;
    this.stopPairingPolling();

    try {
      const res = await api.startCloudPairing();
      this.userCode = res.user_code;
      this.verificationUriComplete = res.verification_uri_complete;
      this.pairingStatus = 'pending';

      if (typeof window !== 'undefined' && res.verification_uri_complete) {
        window.open(res.verification_uri_complete, '_blank', 'noopener,noreferrer');
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
      this.actionLoading = false;
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
        this.stopPairingPolling();
        await this.loadLicenseDetails();
        toastStore.success(`Cloud account linked! UID: ${res.formatted_id || res.uid || ''}`);
      } else if (res.status === 'expired' || res.status === 'denied' || res.status === 'failed') {
        this.pairingStatus = res.status;
        this.pairingError = res.error_message || `Device pairing ${res.status}.`;
        this.stopPairingPolling();
      }
    } catch {
      // Retry on next interval tick
    }
  }

  public async cancelPairingFlow(): Promise<void> {
    this.stopPairingPolling();
    try {
      await api.cancelCloudPairing();
    } catch {
      // Ignore network error on cancel
    }
    this.pairingStatus = 'idle';
    this.userCode = null;
    this.verificationUriComplete = null;
    this.pairingError = null;
  }

  public async unlinkAccount(): Promise<boolean> {
    this.actionLoading = true;
    try {
      await api.unlinkCloudAccount();
      toastStore.success('Cloud account unlinked successfully.');
      await this.loadLicenseDetails();
      this.pairingStatus = 'idle';
      return true;
    } catch (err: any) {
      const msg = err?.message || 'Failed to unlink cloud account.';
      toastStore.error(msg);
      return false;
    } finally {
      this.actionLoading = false;
    }
  }

  public openPortalSync(): void {
    if (typeof window !== 'undefined') {
      window.open(getCloudUrl('portal'), '_blank', 'noopener,noreferrer');
    }
  }
}
