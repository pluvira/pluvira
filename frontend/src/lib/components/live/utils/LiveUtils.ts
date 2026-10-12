import type { ChannelItem, EpgProgramItem } from '$lib/api/types';

export type { EpgProgramItem };

export type TvMobileTab = 'epg' | 'details';

export interface RenderedBlock {
  program: EpgProgramItem;
  leftPx: number;
  widthPx: number;
  timeLabel: string;
  durationMins: number;
  matchScore?: number;
}

export interface LiveProgramInfo {
  current: EpgProgramItem | null;
  next: EpgProgramItem | null;
  progressPct: number;
  timeRemainingMins: number;
  timeLabel: string;
  startDate: Date | null;
  endDate: Date | null;
}

export const TIMELINE_ZOOM_LEVELS = [
  { label: '3 Hours', value: 3 },
  { label: '4 Hours', value: 4 },
  { label: '6 Hours', value: 6 },
  { label: '9 Hours', value: 9 },
  { label: '12 Hours', value: 12 },
  { label: '24 Hours', value: 24 }
];

export function parseXmltvDate(dateStr: string): Date | null {
  if (!dateStr || typeof dateStr !== 'string') return null;
  const trimmed = dateStr.trim();
  if (!trimmed) return null;

  try {
    if (trimmed.includes('-')) {
      let isoStr = trimmed.replace(' ', 'T');
      if (!isoStr.endsWith('Z') && !isoStr.includes('+') && !isoStr.match(/-\d{2}:?\d{2}$/)) {
        isoStr += 'Z';
      }
      const parsed = new Date(isoStr);
      if (!isNaN(parsed.getTime())) {
        return parsed;
      }
    }

    if (trimmed.length < 14) return null;
    const year = parseInt(trimmed.substring(0, 4), 10);
    const month = parseInt(dateStr.substring(4, 6), 10) - 1;
    const day = parseInt(dateStr.substring(6, 8), 10);
    const hour = parseInt(dateStr.substring(8, 10), 10);
    const minute = parseInt(dateStr.substring(10, 12), 10);
    const second = parseInt(dateStr.substring(12, 14), 10);

    const utcDate = new Date(Date.UTC(year, month, day, hour, minute, second));

    const offsetMatch = dateStr.match(/([+-])(\d{2}):?(\d{2})/);
    if (offsetMatch) {
      const sign = offsetMatch[1] === '+' ? 1 : -1;
      const offsetHours = parseInt(offsetMatch[2], 10);
      const offsetMins = parseInt(offsetMatch[3], 10);
      const totalOffsetMs = sign * (offsetHours * 60 + offsetMins) * 60 * 1000;
      return new Date(utcDate.getTime() - totalOffsetMs);
    }

    return utcDate;
  } catch {
    return null;
  }
}

export function getDayBounds(dateStr: string): [Date, Date] {
  const [y, m, d] = dateStr.split('-').map((v) => parseInt(v, 10));
  const dayStart = new Date(y, m - 1, d, 0, 0, 0, 0);
  const dayEnd = new Date(y, m - 1, d, 23, 59, 59, 999);
  return [dayStart, dayEnd];
}

export function getTimelineBounds(dateStr: string, days: number = 3): [Date, Date] {
  const [y, m, d] = dateStr.split('-').map((v) => parseInt(v, 10));
  const start = new Date(y, m - 1, d, 0, 0, 0, 0);
  const end = new Date(start.getTime() + days * 86400 * 1000);
  return [start, end];
}

export function calculateBlockPosition(
  program: EpgProgramItem,
  windowStart: Date,
  windowEnd: Date,
  timelineWidth = 7200
): RenderedBlock | null {
  const pStart = parseXmltvDate(program.s);
  const pEnd = parseXmltvDate(program.e);

  if (!pStart || !pEnd) return null;
  if (pEnd <= windowStart || pStart >= windowEnd) return null;

  const dispStart = pStart < windowStart ? windowStart : pStart;
  const dispEnd = pEnd > windowEnd ? windowEnd : pEnd;

  const durationMs = windowEnd.getTime() - windowStart.getTime();
  const leftPx = ((dispStart.getTime() - windowStart.getTime()) / durationMs) * timelineWidth;
  const widthPx = Math.max(12, ((dispEnd.getTime() - dispStart.getTime()) / durationMs) * timelineWidth);

  const durationMins = Math.round((pEnd.getTime() - pStart.getTime()) / (60 * 1000));
  const timeLabel = `${pStart.getHours().toString().padStart(2, '0')}:${pStart.getMinutes().toString().padStart(2, '0')}`;

  return {
    program,
    leftPx,
    widthPx,
    timeLabel,
    durationMins
  };
}

export function getCurrentAndNextProgram(
  programmes: EpgProgramItem[] = [],
  now: Date = new Date()
): LiveProgramInfo {
  if (!Array.isArray(programmes) || programmes.length === 0) {
    return {
      current: null,
      next: null,
      progressPct: 0,
      timeRemainingMins: 0,
      timeLabel: 'No schedule data',
      startDate: null,
      endDate: null
    };
  }

  const nowMs = now.getTime();
  let current: EpgProgramItem | null = null;
  let next: EpgProgramItem | null = null;
  let currentStart: Date | null = null;
  let currentEnd: Date | null = null;

  for (let i = 0; i < programmes.length; i++) {
    const prog = programmes[i];
    const pStart = parseXmltvDate(prog.s);
    const pEnd = parseXmltvDate(prog.e);

    if (!pStart || !pEnd) continue;

    const sMs = pStart.getTime();
    const eMs = pEnd.getTime();

    if (sMs <= nowMs && eMs > nowMs) {
      current = prog;
      currentStart = pStart;
      currentEnd = pEnd;
      if (i + 1 < programmes.length) {
        next = programmes[i + 1];
      }
      break;
    } else if (sMs > nowMs && !next) {
      next = prog;
    }
  }

  let progressPct = 0;
  let timeRemainingMins = 0;
  let timeLabel = 'No schedule data';

  if (current && currentStart && currentEnd) {
    const totalDurationMs = currentEnd.getTime() - currentStart.getTime();
    const elapsedMs = nowMs - currentStart.getTime();
    progressPct = totalDurationMs > 0
      ? Math.max(0, Math.min(100, Math.round((elapsedMs / totalDurationMs) * 100)))
      : 0;

    timeRemainingMins = Math.max(0, Math.round((currentEnd.getTime() - nowMs) / (60 * 1000)));

    const sH = currentStart.getHours().toString().padStart(2, '0');
    const sM = currentStart.getMinutes().toString().padStart(2, '0');
    const eH = currentEnd.getHours().toString().padStart(2, '0');
    const eM = currentEnd.getMinutes().toString().padStart(2, '0');
    timeLabel = `${sH}:${sM} - ${eH}:${eM}`;
  }

  return {
    current,
    next,
    progressPct,
    timeRemainingMins,
    timeLabel,
    startDate: currentStart,
    endDate: currentEnd
  };
}

export function getProgramProgressPct(
  program: EpgProgramItem | null,
  now: Date = new Date()
): number {
  if (!program) return 0;
  const pStart = parseXmltvDate(program.s);
  const pEnd = parseXmltvDate(program.e);
  if (!pStart || !pEnd) return 0;

  const nowMs = now.getTime();
  const sMs = pStart.getTime();
  const eMs = pEnd.getTime();

  if (nowMs < sMs) return 0;
  if (nowMs >= eMs) return 100;

  const totalMs = eMs - sMs;
  const elapsedMs = nowMs - sMs;
  return totalMs > 0 ? Math.max(0, Math.min(100, Math.round((elapsedMs / totalMs) * 100))) : 0;
}

export function formatTimeRemaining(mins: number): string {
  if (mins <= 0) return 'Ending now';
  if (mins < 1) return '< 1m left';
  if (mins < 60) return `${mins}m left`;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  return remMins > 0 ? `${hrs}h ${remMins}m left` : `${hrs}h left`;
}

export function extractTvGroups(channels: ChannelItem[]): string[] {
  if (!Array.isArray(channels)) return [];
  const groups = new Set<string>();
  channels.forEach((ch) => {
    if (ch?.group?.trim()) {
      groups.add(ch.group.trim());
    }
  });
  return Array.from(groups).sort();
}

export function isProgrammeCurrentlyLive(
  program: EpgProgramItem | null,
  now: Date = new Date()
): boolean {
  if (!program) return false;
  const pStart = parseXmltvDate(program.s);
  const pEnd = parseXmltvDate(program.e);
  if (!pStart || !pEnd) return false;
  const nowMs = now.getTime();
  return pStart.getTime() <= nowMs && pEnd.getTime() > nowMs;
}

export function extractUniqueEpgIds(channels: ChannelItem[]): string[] {
  if (!Array.isArray(channels)) return [];
  const epgIds = new Set<string>();
  channels.forEach((ch) => {
    if (ch?.epg_id && ch.epg_id.trim()) {
      const trimmed = ch.epg_id.trim();
      epgIds.add(trimmed);
      if (trimmed.includes('::')) {
        const raw = trimmed.split('::', 2)[1];
        if (raw) epgIds.add(raw);
      }
    }
  });
  return Array.from(epgIds);
}

export function getEpgDateRange(
  baseDate: Date = new Date(),
  daysAhead = 3,
  daysBehind = 0
): { date_from: string; date_to: string } {
  const fromD = new Date(baseDate);
  fromD.setDate(fromD.getDate() - daysBehind);
  const toD = new Date(baseDate);
  toD.setDate(toD.getDate() + daysAhead);

  const formatDate = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  return {
    date_from: formatDate(fromD),
    date_to: formatDate(toD)
  };
}
