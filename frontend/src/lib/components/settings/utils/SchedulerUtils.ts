/**
 * Utility functions and taxonomy definitions for background scheduler jobs and triggers.
 */

export interface DayOfWeekOption {
  key: string;
  label: string;
  shortLabel: string;
  cronValue: string;
}

export const DAYS_OF_WEEK: DayOfWeekOption[] = [
  { key: 'mon', label: 'Monday', shortLabel: 'Mon', cronValue: '1' },
  { key: 'tue', label: 'Tuesday', shortLabel: 'Tue', cronValue: '2' },
  { key: 'wed', label: 'Wednesday', shortLabel: 'Wed', cronValue: '3' },
  { key: 'thu', label: 'Thursday', shortLabel: 'Thu', cronValue: '4' },
  { key: 'fri', label: 'Friday', shortLabel: 'Fri', cronValue: '5' },
  { key: 'sat', label: 'Saturday', shortLabel: 'Sat', cronValue: '6' },
  { key: 'sun', label: 'Sunday', shortLabel: 'Sun', cronValue: '0' }
];

export interface DayPreset {
  key: string;
  label: string;
  cronValue: string;
}

export const DAY_PRESETS: DayPreset[] = [
  { key: 'everyday', label: 'Every Day (Daily)', cronValue: '*' },
  { key: 'weekdays', label: 'Weekdays (Mon - Fri)', cronValue: '1-5' },
  { key: 'weekends', label: 'Weekends Only (Sat - Sun)', cronValue: '6,0' },
  { key: 'weekly_sun', label: 'Weekly on Sunday', cronValue: '0' },
  { key: 'weekly_mon', label: 'Weekly on Monday', cronValue: '1' },
  { key: 'custom', label: 'Custom (Selected Days)', cronValue: '' }
];

import type { ScheduledJob } from '$lib/api/types';

export interface SchedulerModeOption {
  value: string;
  label: string;
  description: string;
  is_system?: boolean;
  is_recommended?: boolean;
}

export const SCHEDULER_MODE_OPTIONS: SchedulerModeOption[] = [
  {
    value: 'tv_sync_full',
    label: 'Full TV & EPG Sync',
    description: 'Complete synchronization of M3U playlist channels, XMLTV guide programmes, and cache generation.',
    is_recommended: true
  },
  {
    value: 'tv_sync_channels',
    label: 'Channels Playlist Sync',
    description: 'Downloads and parses M3U playlist channels with allow/deny filters and metadata rewrites.',
    is_recommended: false
  },
  {
    value: 'epg_sync_guides',
    label: 'EPG Guides Sync',
    description: 'Downloads and parses XMLTV guide schedules into database with channel mapping resolution.',
    is_recommended: true
  },
  {
    value: 'stream_health_scan',
    label: 'Stream Link Health Scan',
    description: 'Executes background polite link testing to verify stream reachability and compute health scores.',
    is_recommended: true
  },
  {
    value: 'license_auto_renewal',
    label: 'License Sync & Auto-Renewal',
    description: 'Periodic cloud synchronization for license feature updates and automated renewals.',
    is_system: true,
    is_recommended: false
  },
  {
    value: 'cloud_backup',
    label: 'Cloud Backup Vault Sync',
    description: 'Automated E2EE cloud backup snapshot synchronization for Pro and Ultra subscribers.',
    is_system: false,
    is_recommended: true
  }
];

export function isSystemJob(job?: ScheduledJob | null): boolean {
  if (!job) return false;
  return Boolean(job.is_system || job.mode === 'license_auto_renewal');
}

export function isRecommendedJob(job?: ScheduledJob | null): boolean {
  if (!job) return false;
  return Boolean(job.is_recommended);
}

export function parseCronDays(cronStr?: string): string[] {
  const clean = (cronStr || '*').trim().toLowerCase();
  if (clean === '*' || clean === '') {
    return DAYS_OF_WEEK.map((d) => d.key);
  }
  if (clean === '1-5' || clean === 'mon-fri') {
    return ['mon', 'tue', 'wed', 'thu', 'fri'];
  }
  if (clean === '6,0' || clean === '6,7' || clean === 'sat,sun') {
    return ['sat', 'sun'];
  }
  const parts = clean.split(',').map((p) => p.trim());
  const selected: string[] = [];
  for (const d of DAYS_OF_WEEK) {
    if (parts.includes(d.cronValue) || parts.includes(d.key) || parts.includes(d.shortLabel.toLowerCase())) {
      selected.push(d.key);
    }
  }
  return selected.length > 0 ? selected : DAYS_OF_WEEK.map((d) => d.key);
}

export function formatCronDays(activeKeys: string[]): string {
  if (!activeKeys || activeKeys.length === 0 || activeKeys.length === 7) {
    return '*';
  }
  const isWeekdays = activeKeys.length === 5 && ['mon', 'tue', 'wed', 'thu', 'fri'].every((k) => activeKeys.includes(k));
  if (isWeekdays) return '1-5';

  const isWeekends = activeKeys.length === 2 && ['sat', 'sun'].every((k) => activeKeys.includes(k));
  if (isWeekends) return '6,0';

  const values = activeKeys
    .map((k) => DAYS_OF_WEEK.find((d) => d.key === k)?.cronValue)
    .filter((v): v is string => Boolean(v));
  return values.join(',');
}

export function matchDayPreset(cronStr?: string): string {
  const clean = (cronStr || '*').trim().toLowerCase();
  if (clean === '*' || clean === '') return 'everyday';
  if (clean === '1-5' || clean === 'mon-fri') return 'weekdays';
  if (clean === '6,0' || clean === '6,7' || clean === 'sat,sun') return 'weekends';
  if (clean === '0' || clean === 'sun') return 'weekly_sun';
  if (clean === '1' || clean === 'mon') return 'weekly_mon';
  return 'custom';
}
