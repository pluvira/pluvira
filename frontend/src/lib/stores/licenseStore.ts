import { writable, get } from 'svelte/store';
import type { EditionType, LicenseDetails, SystemStatus, LicenseResponse } from '$lib/api/types';

export interface LicenseState {
  edition: EditionType;
  tier: string;
  tierDisplayName: string;
  compactName: string;
  badgeIcon: string;
  badgeColor: string | null;
  badgeTextColor: string | null;
  maxIps: number;
  isPro: boolean;
  licenseDetails: LicenseDetails | null;
  webrtcActive: boolean;
  webrtcStatus: 'connected' | 'standby' | 'disabled' | 'error';
  supportedCommands: string[];
  supportedModules: string[];
  isLoaded: boolean;
}

const defaultState: LicenseState = {
  edition: 'core',
  tier: 'core',
  tierDisplayName: 'Core Free',
  compactName: 'CORE',
  badgeIcon: 'sparkles',
  badgeColor: null,
  badgeTextColor: null,
  maxIps: 2,
  isPro: false,
  licenseDetails: null,
  webrtcActive: false,
  webrtcStatus: 'disabled',
  supportedCommands: [],
  supportedModules: [],
  isLoaded: false
};

function resolveTierDisplayName(tier?: string | null, customDisplay?: string | null): string {
  if (customDisplay && customDisplay.trim()) return customDisplay.trim();
  const clean = (tier || '').trim().toLowerCase();
  if (!clean || clean === 'core') return 'Core Free';
  if (clean === 'free') return 'Free Registered';
  if (clean === 'pro') return 'Pro Edition';
  if (clean === 'trial') return '14-Day Trial';
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

function resolveCompactName(tier?: string | null, customCompact?: string | null): string {
  if (customCompact && customCompact.trim()) return customCompact.trim();
  const clean = (tier || '').trim().toLowerCase();
  if (!clean || clean === 'core') return 'CORE';
  if (clean === 'free') return 'FREE';
  if (clean === 'pro') return 'PRO';
  if (clean === 'trial') return 'TRIAL';
  return clean.toUpperCase();
}

function createLicenseStore() {
  const store = writable<LicenseState>(defaultState);
  const { subscribe, set, update } = store;

  return {
    subscribe,
    setLicense: (edition: EditionType, licenseDetails: LicenseDetails | null, isPro: boolean, supportedCommands: string[] = [], supportedModules: string[] = []) => {
      const tier = (licenseDetails?.tier || (isPro ? 'pro' : 'core')).toLowerCase();
      const tierDisplayName = resolveTierDisplayName(tier, licenseDetails?.display_name_full);
      const compactName = resolveCompactName(tier, licenseDetails?.compact_name);
      const badgeIcon = licenseDetails?.badge_icon || (tier === 'free' ? 'user-check' : 'sparkles');
      const badgeColor = licenseDetails?.badge_color || (tier === 'free' ? '#0ea5e9' : null);
      const badgeTextColor = licenseDetails?.badge_text_color || (tier === 'free' ? '#ffffff' : null);
      const maxIps = licenseDetails?.max_ips || (isPro ? 20 : 2);
      set({
        edition,
        tier,
        tierDisplayName,
        compactName,
        badgeIcon,
        badgeColor,
        badgeTextColor,
        maxIps,
        isPro,
        licenseDetails,
        webrtcActive: Boolean(isPro),
        webrtcStatus: isPro ? 'standby' : 'disabled',
        supportedCommands,
        supportedModules,
        isLoaded: true
      });
    },
    updateFromSystemStatus: (status: SystemStatus) => {
      const isPro = Boolean(status.pro_active || status.edition === 'pro');
      const edition: EditionType = status.edition || (isPro ? 'pro' : 'core');
      const licenseDetails = status.license || null;
      const tier = (licenseDetails?.tier || status.tier || (isPro ? 'pro' : 'core')).toLowerCase();
      const tierDisplayName = resolveTierDisplayName(
        tier,
        licenseDetails?.display_name_full || status.display_name_full
      );
      const compactName = resolveCompactName(tier, licenseDetails?.compact_name || status.compact_name);
      const badgeIcon = licenseDetails?.badge_icon || status.badge_icon || (tier === 'free' ? 'user-check' : 'sparkles');
      const badgeColor = licenseDetails?.badge_color || status.badge_color || (tier === 'free' ? '#0ea5e9' : null);
      const badgeTextColor = licenseDetails?.badge_text_color || status.badge_text_color || (tier === 'free' ? '#ffffff' : null);
      const maxIps = licenseDetails?.max_ips || status.max_ips || (isPro ? 20 : 2);
      const webrtcActive = Boolean(status.webrtc_active && isPro);
      const webrtcStatus = (isPro && status.webrtc_status) ? status.webrtc_status : (isPro ? 'standby' : 'disabled');
      const supportedCommands = status.supported_commands || [];
      const supportedModules = status.supported_modules || [];
      set({
        edition,
        tier,
        tierDisplayName,
        compactName,
        badgeIcon,
        badgeColor,
        badgeTextColor,
        maxIps,
        isPro,
        licenseDetails,
        webrtcActive,
        webrtcStatus,
        supportedCommands,
        supportedModules,
        isLoaded: true
      });
    },
    updateFromLicenseResponse: (res: LicenseResponse) => {
      const isPro = Boolean(res.pro_active);
      const tier = (res.license?.tier || res.tier || (isPro ? 'pro' : 'core')).toLowerCase();
      const tierDisplayName = resolveTierDisplayName(tier, res.license?.display_name_full);
      const compactName = resolveCompactName(tier, res.license?.compact_name);
      const badgeIcon = res.license?.badge_icon || (tier === 'free' ? 'user-check' : 'sparkles');
      const badgeColor = res.license?.badge_color || (tier === 'free' ? '#0ea5e9' : null);
      const badgeTextColor = res.license?.badge_text_color || (tier === 'free' ? '#ffffff' : null);
      const maxIps = res.license?.max_ips || (isPro ? 20 : 2);
      update((state) => ({
        ...state,
        edition: res.edition,
        tier,
        tierDisplayName,
        compactName,
        badgeIcon,
        badgeColor,
        badgeTextColor,
        maxIps,
        isPro,
        licenseDetails: res.license,
        webrtcActive: Boolean(res.pro_active),
        webrtcStatus: res.pro_active ? 'standby' : 'disabled',
        isLoaded: true
      }));
    },
    hasModule: (moduleSlug: string): boolean => {
      const state = get(store);
      const target = moduleSlug.toLowerCase().replace(/-/g, '_');
      const activeModules = (state.licenseDetails?.modules || state.supportedModules || []).map((m) =>
        m.toLowerCase().replace(/-/g, '_')
      );
      return activeModules.includes(target);
    },
    reset: () => {
      set(defaultState);
    }
  };
}

export const licenseStore = createLicenseStore();
