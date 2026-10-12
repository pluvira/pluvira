import type { GlobalConfig, SchedulePayload, ScheduledJob, RewriteRule } from '$lib/api/types';
import { getPreference, setPreference } from '$lib/utils/preferences';
import { Settings, Tv, Clock, Archive } from '@lucide/svelte';
import type { Component } from 'svelte';

export type MacroSettingsTabKey = 'general' | 'sources' | 'updates' | 'backup';

export type GeneralSubTabKey = 'system' | 'advanced' | 'theme';
export type SourcesSubTabKey = 'playlists' | 'iptv' | 'epg' | 'rewrites';
export type UpdatesSubTabKey = 'scheduler' | 'notifications';
export type BackupSubTabKey = 'backup' | 'history';

export interface NotificationSectionsState {
  runner: boolean;
  scanner: boolean;
  hardware: boolean;
}

export const DEFAULT_NOTIFICATION_SECTIONS: NotificationSectionsState = {
  runner: false,
  scanner: false,
  hardware: false
};

export interface NotificationPresetOption {
  label: string;
  value: string;
}

export const NOTIFICATION_PRESETS: NotificationPresetOption[] = [
  { label: 'ALL', value: 'all' },
  { label: 'NONE', value: 'none' },
  { label: 'SIMPLE', value: 'simple' },
  { label: 'BALANCED', value: 'balanced' },
  { label: 'ADVANCED', value: 'advanced' },
  { label: 'HARDWARE', value: 'hardware' },
  { label: 'CONTENT', value: 'content' }
];

/**
 * Retrieves the stored open index for an accordion section.
 *
 * @param key Storage identifier prefix.
 * @returns Stored index number or null.
 */
export function getAccordionOpenIndex(key: string): number | null {
  return getPreference<number | null>(`${key}_open_idx`, null);
}

/**
 * Persists the open index for an accordion section.
 *
 * @param key Storage identifier prefix.
 * @param idx Target index to persist.
 */
export function setAccordionOpenIndex(key: string, idx: number | null): void {
  setPreference(`${key}_open_idx`, idx);
}


export interface MacroTabItem {
  key: MacroSettingsTabKey;
  label: string;
  icon: Component;
}

export const MACRO_SETTINGS_TABS: MacroTabItem[] = [
  { key: 'general', label: 'General', icon: Settings },
  { key: 'sources', label: 'Sources', icon: Tv },
  { key: 'updates', label: 'Updates', icon: Clock },
  { key: 'backup', label: 'Backup', icon: Archive }
];

/**
 * Creates a default empty rewrite rule object.
 *
 * @returns Initialized RewriteRule object.
 */
export function createDefaultRewriteRule(): RewriteRule {
  return {
    field: 'name',
    pattern: '',
    replacement: '',
    mode: 'regex',
    enabled: true,
    description: ''
  };
}


/**
 * Normalizes raw config object ensuring required nested objects exist with defaults.
 *
 * @param config Raw GlobalConfig model.
 * @returns Normalized GlobalConfig object.
 */
export function normalizeConfig(config?: Partial<GlobalConfig>): GlobalConfig {
  return {
    settings: {
      output_m3u: config?.settings?.output_m3u || 'data/iptv.m3u',
      output_epg: config?.settings?.output_epg || 'data/epg.xml',
      temp_dir: config?.settings?.temp_dir || '/dev/shm/pluvira',
      device_name: config?.settings?.device_name || 'Pluvira',
      mdns: config?.settings?.mdns || {
        enabled: true,
        service_type: '_pluvira._tcp.local.'
      },
      user_agent: config?.settings?.user_agent || 'Mozilla/5.0',
      epg_retention_days: config?.settings?.epg_retention_days || 7,
      cache_driver: config?.settings?.cache_driver || 'memory',
      cache_ttl_seconds: config?.settings?.cache_ttl_seconds || 3600,
      search_debounce_ms: config?.settings?.search_debounce_ms || 300,
      language: config?.settings?.language || 'it',
      custom_stopwords: config?.settings?.custom_stopwords || [],
      search_methods: config?.settings?.search_methods || {
        method_a: true,
        method_b: true,
        method_c: true,
        method_d: true
      },
      force_proxy: config?.settings?.force_proxy ?? false,
      notification_urls: config?.settings?.notification_urls || [],
      allow_channels: config?.settings?.allow_channels || [],
      deny_channels: config?.settings?.deny_channels || [],
      rewrites: config?.settings?.rewrites || [],
      mapping_overrides: config?.settings?.mapping_overrides || {},
      link_test_settings: config?.settings?.link_test_settings || { min_delay: 1.5, max_delay: 3.5 },
      notifications: {
        enabled: config?.settings?.notifications?.enabled ?? false,
        urls: config?.settings?.notifications?.urls || config?.settings?.notification_urls || [],
        events: config?.settings?.notifications?.events || {
          update_success: true,
          update_failure: true,
          link_test_report: true,
          link_ko_detected: true,
          disk_space_warning: true
        }
      }
    },
    auth: {
      enabled: config?.auth?.enabled ?? false,
      username: config?.auth?.username || 'admin',
      password: config?.auth?.password || 'admin',
      token_expire_minutes: config?.auth?.token_expire_minutes || 1440
    },
    sources: config?.sources || [],
    epg_sources: config?.epg_sources || [],
    channel_merges: config?.channel_merges || {},
    individual_rewrites: config?.individual_rewrites || {}
  };
}

/**
 * Normalizes raw scheduler payload ensuring jobs array and default fields exist defensively.
 *
 * @param schedule Raw SchedulePayload model.
 * @returns Normalized SchedulePayload object.
 */
export function normalizeSchedule(schedule?: Partial<SchedulePayload>): SchedulePayload {
  const jobs = Array.isArray(schedule?.jobs)
    ? schedule.jobs.map((job: Partial<ScheduledJob>) => {
        if (!job) return {};
        const base: ScheduledJob = {
          id: job.id ?? '',
          enabled: job.enabled ?? true,
          mode: job.mode || 'full',
          trigger: job.trigger || 'cron',
          hour: job.hour ?? 4,
          minute: job.minute ?? 0,
          day_of_week: job.day_of_week || '*',
          hours: job.hours ?? 0,
          minutes: job.minutes ?? 0,
          description: job.description || ''
        };
        if (base.mode === 'link_test') {
          const filters = job.link_test_filters || {};
          return {
            ...base,
            link_test_filters: {
              inclusion: filters.inclusion || 'included_only',
              status_filter: filters.status_filter || 'all',
              max_channels: filters.max_channels ?? 50,
              sources: Array.isArray(filters.sources) ? filters.sources : [],
              groups: Array.isArray(filters.groups) ? filters.groups : [],
              name_regex: filters.name_regex || ''
            }
          };
        }
        return base;
      })
    : [];

  return {
    enabled: schedule?.enabled ?? true,
    jobs
  };
}

/**
 * Compares two GlobalConfig instances for structural equality.
 *
 * @param initial Initial snapshot configuration.
 * @param current Current working configuration.
 * @returns True if configuration has changed, false otherwise.
 */
export function isConfigDirty(
  initial?: GlobalConfig | null,
  current?: GlobalConfig | null
): boolean {
  if (!initial || !current) return false;
  return JSON.stringify(initial) !== JSON.stringify(current);
}

/**
 * Compares two SchedulePayload instances for structural equality.
 *
 * @param initial Initial snapshot schedule.
 * @param current Current working schedule.
 * @returns True if schedule has changed, false otherwise.
 */
export function isScheduleDirty(
  initial?: SchedulePayload | null,
  current?: SchedulePayload | null
): boolean {
  if (!initial || !current) return false;
  return JSON.stringify(initial) !== JSON.stringify(current);
}


