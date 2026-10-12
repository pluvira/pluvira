import type { BackupBundle, BackupDiffSummary } from '$lib/api/types';

export function formatByteSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export interface FormattedDiffRow {
  key: string;
  label: string;
  added: number;
  updated: number;
  removed: number;
}

/**
 * Reads a client-selected File object and parses it as a JSON BackupBundle.
 *
 * @param file Target File uploaded by the user.
 * @returns Promise resolving to the parsed BackupBundle.
 * @throws Error if file reading or JSON parsing fails.
 */
export async function readBackupFileAsJson(file: File): Promise<BackupBundle> {
  if (!file) {
    throw new Error('No file provided for backup import.');
  }
  return new Promise<BackupBundle>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        if (!text || !text.trim()) {
          throw new Error('Backup file is empty.');
        }
        const data = JSON.parse(text);
        if (!data || typeof data !== 'object') {
          throw new Error('Invalid backup file structure: root must be a JSON object.');
        }
        if (!data.config || typeof data.config !== 'object') {
          throw new Error('Invalid backup file: missing "config" root property.');
        }
        resolve(data as BackupBundle);
      } catch (err: any) {
        reject(new Error(`Failed to parse backup JSON: ${err.message}`));
      }
    };
    reader.onerror = () => {
      reject(new Error('Failed to read backup file from disk.'));
    };
    reader.readAsText(file);
  });
}

/**
 * Converts raw BackupDiffSummary into formatted tabular rows for UI display.
 *
 * @param diff Structured diff summary from backend validation.
 * @returns Array of FormattedDiffRow objects.
 */
export function formatDiffSummary(diff?: BackupDiffSummary | null): FormattedDiffRow[] {
  if (!diff) return [];
  return [
    {
      key: 'sources',
      label: 'IPTV M3U Sources',
      added: diff.sources?.added || 0,
      updated: diff.sources?.updated || 0,
      removed: diff.sources?.removed || 0
    },
    {
      key: 'epg_sources',
      label: 'XMLTV EPG Sources',
      added: diff.epg_sources?.added || 0,
      updated: diff.epg_sources?.updated || 0,
      removed: diff.epg_sources?.removed || 0
    },
    {
      key: 'individual_rewrites',
      label: 'Individual Rewrites',
      added: diff.individual_rewrites?.added || 0,
      updated: diff.individual_rewrites?.updated || 0,
      removed: diff.individual_rewrites?.removed || 0
    },
    {
      key: 'channel_merges',
      label: 'Master Channel Merges',
      added: diff.channel_merges?.added || 0,
      updated: diff.channel_merges?.updated || 0,
      removed: diff.channel_merges?.removed || 0
    },
    {
      key: 'schedule_jobs',
      label: 'Scheduled Update Jobs',
      added: diff.schedule_jobs?.added || 0,
      updated: diff.schedule_jobs?.updated || 0,
      removed: diff.schedule_jobs?.removed || 0
    }
  ];
}

/**
 * Checks if a BackupDiffSummary contains any detected changes.
 *
 * @param diff Structured diff summary from backend validation.
 * @returns True if at least one entity or setting has changed.
 */
export function hasAnyDiffChanges(diff?: BackupDiffSummary | null): boolean {
  if (!diff) return false;
  const categories = [
    diff.sources,
    diff.epg_sources,
    diff.individual_rewrites,
    diff.channel_merges,
    diff.schedule_jobs
  ];
  const hasCategoryChanges = categories.some(
    (c) => c && (c.added > 0 || c.updated > 0 || c.removed > 0)
  );
  const hasSettingsChanges =
    Array.isArray(diff.settings_modified) && diff.settings_modified.length > 0;
  const hasAuthChanges = Boolean(diff.auth_modified);
  return hasCategoryChanges || hasSettingsChanges || hasAuthChanges;
}
