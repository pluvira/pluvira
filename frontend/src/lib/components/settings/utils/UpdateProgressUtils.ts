import type { UpdateProgressDTO } from '$lib/api/types';

export function createDefaultProgressDTO(): UpdateProgressDTO {
  return {
    is_running: false,
    mode: 'idle',
    elapsed_seconds: 0,
    sources: [],
    phases: {
      rewrites: {
        title: 'Metadata Cascading Rewrites',
        status: 'pending',
        detail: 'Pending'
      },
      database_cache: {
        title: 'Data Persistence & Cache Refresh',
        status: 'pending',
        detail: 'Pending'
      }
    },
    summary: null
  };
}



export function parseLogLevel(line: string): 'info' | 'warning' | 'error' | 'debug' {
  const lower = line.toLowerCase();
  if (
    lower.includes('error') ||
    lower.includes('critical') ||
    lower.includes('failed') ||
    lower.includes('exception') ||
    lower.includes('errno')
  ) {
    return 'error';
  }
  if (lower.includes('warn') || lower.includes('warning')) {
    return 'warning';
  }
  if (lower.includes('debug')) {
    return 'debug';
  }
  return 'info';
}

export interface FormattedLogLine {
  id: number;
  raw: string;
  level: 'info' | 'warning' | 'error' | 'debug';
}

export function formatLogLines(rawLogs: string[]): FormattedLogLine[] {
  return rawLogs.map((raw, idx) => ({
    id: idx,
    raw,
    level: parseLogLevel(raw)
  }));
}
