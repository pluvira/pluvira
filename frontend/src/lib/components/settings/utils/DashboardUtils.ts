export interface FormattedAnalytics {
  totalChannels: number;
  totalIncluded: number;
  totalExcluded: number;
  epgCoveragePct: number;
  linkHealthPct: number;
  onlineCount: number;
  offlineCount: number;
  uncheckedCount: number;
  topGroups: Array<[string, number]>;
}

/**
 * Normalizes raw dashboard analytics payload into a safe structured object with fallback defaults.
 *
 * @param raw Payload from API getDashboardAnalytics().
 * @returns Safe FormattedAnalytics object.
 */
export function formatGlobalStats(raw?: Record<string, unknown>): FormattedAnalytics {
  if (!raw) {
    return {
      totalChannels: 0,
      totalIncluded: 0,
      totalExcluded: 0,
      epgCoveragePct: 0.0,
      linkHealthPct: 0.0,
      onlineCount: 0,
      offlineCount: 0,
      uncheckedCount: 0,
      topGroups: []
    };
  }

  return {
    totalChannels: Number(raw.total_channels || 0),
    totalIncluded: Number(raw.total_included || 0),
    totalExcluded: Number(raw.total_excluded || 0),
    epgCoveragePct: Number(raw.epg_coverage_included_pct || 0.0),
    linkHealthPct: Number(raw.link_health_pct || 0.0),
    onlineCount: Number(raw.link_online_count || 0),
    offlineCount: Number(raw.link_offline_count || 0),
    uncheckedCount: Number(raw.link_unchecked_count || 0),
    topGroups: Array.isArray(raw.top_groups) ? (raw.top_groups as Array<[string, number]>) : []
  };
}

/**
 * Formats a duration in seconds into a human readable string (e.g., "12.5s" or "2m 10s").
 *
 * @param seconds Duration in seconds.
 * @returns Formatted duration string.
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

/**
 * Formats sync summary statistics into a compact label (e.g. "4,250 progs (0.8s)" or "0.8s").
 *
 * @param progs Number of parsed programmes in last sync.
 * @param duration_s Duration of sync in seconds.
 * @returns Formatted summary string.
 */
export function formatSyncStats(progs?: number, duration_s?: number): string {
  const formattedDur = duration_s !== undefined && duration_s !== null ? formatDuration(duration_s) : '';
  if (progs !== undefined && progs !== null && progs > 0) {
    const formattedProgs = Number(progs).toLocaleString('en-US');
    return formattedDur ? `${formattedProgs} progs (${formattedDur})` : `${formattedProgs} progs`;
  }
  return formattedDur || '—';
}

/**
 * Formats detailed EPG sync timing with engine mode indicator.
 *
 * @param progs Number of parsed programmes in last sync.
 * @param duration_s Duration of sync in seconds.
 * @param is_turbo Whether Turbo Rust engine was used.
 * @returns Formatted timing string or empty string if no duration.
 */
export function formatEpgSyncTiming(progs?: number, duration_s?: number, is_turbo?: boolean): string {
  if (duration_s === undefined || duration_s === null) {
    return '';
  }
  const formattedProgs = progs !== undefined && progs !== null && progs > 0
    ? `${Number(progs).toLocaleString('en-US')} programmes in `
    : '';
  const durStr = duration_s >= 60 ? `${Math.round(duration_s)}s` : `${Number(duration_s.toFixed(1))}s`;
  const tag = is_turbo ? 'Turbo Mode' : 'High RAM load';
  return `Last sync: ${formattedProgs}${durStr} (${tag})`;
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Formats date string into DD MMM YYYY · HH:mm:ss representation.
 *
 * @param dateStr Raw ISO or SQLite timestamp string.
 * @returns Formatted date string or fallback.
 */
export function formatHistoryDate(dateStr?: string | null): string {
  if (!dateStr || typeof dateStr !== 'string') {
    return '—';
  }
  const trimmed = dateStr.trim();
  const match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (match) {
    const year = match[1];
    const monthIdx = parseInt(match[2], 10) - 1;
    const day = match[3];
    const month = MONTH_NAMES[monthIdx] || match[2];
    const hour = match[4] || '00';
    const min = match[5] || '00';
    const sec = match[6] || '00';
    return `${day} ${month} ${year} · ${hour}:${min}:${sec}`;
  }
  const d = new Date(trimmed);
  if (isNaN(d.getTime())) {
    return trimmed;
  }
  const day = String(d.getDate()).padStart(2, '0');
  const month = MONTH_NAMES[d.getMonth()];
  const year = d.getFullYear();
  const hour = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  const sec = String(d.getSeconds()).padStart(2, '0');
  return `${day} ${month} ${year} · ${hour}:${min}:${sec}`;
}
