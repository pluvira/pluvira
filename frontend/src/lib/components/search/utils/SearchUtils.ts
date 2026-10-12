import type { ChannelItem, EpgProgramItem, SearchMethodsConfig } from '$lib/api/types';
import { parseXmltvDate, isProgrammeCurrentlyLive } from '$lib/components/live/utils/LiveUtils';

/**
 * Resolves programme guide items for a channel matching namespaced or raw EPG keys.
 *
 * @param channel Target ChannelItem.
 * @param epgData Map of EPG programmes by ID.
 * @returns Array of matching EpgProgramItem records.
 */
export function getProgrammesForChannelFromEpgData(
  channel?: ChannelItem | null,
  epgData: Record<string, EpgProgramItem[]> = {}
): EpgProgramItem[] {
  if (!channel?.epg_id || !epgData) return [];
  const epgId = channel.epg_id;
  if (epgData[epgId] && epgData[epgId].length > 0) return epgData[epgId];
  if (epgId.includes('::')) {
    const rawId = epgId.split('::', 1)[1];
    if (epgData[rawId] && epgData[rawId].length > 0) return epgData[rawId];
  }
  for (const [k, progs] of Object.entries(epgData)) {
    if ((k.endsWith(`::${epgId}`) || (epgId.includes('::') && k === epgId.split('::')[1])) && progs.length > 0) {
      return progs;
    }
  }
  return epgData[epgId] || [];
}
import { scoreProgrammeMatch, tokenizeQuery } from '$lib/components/live/utils/IntelligentSearchUtils';
import { getMergedStopwords } from '$lib/components/live/utils/StopwordsUtils';

export type SearchDateScope = 'today' | 'three_days' | 'all';

export const SUGGESTED_SEARCH_TOPICS = ['News', 'Movies', 'Sports', 'Series', 'Music', 'Documentary'];

export interface ChannelGroupedSearchResult {
  channel: ChannelItem;
  items: SearchResultItem[];
  totalScore: number;
  bestItem: SearchResultItem;
}

export interface SearchFilterOptions {
  query: string;
  liveOnly: boolean;
  primeTimeOnly?: boolean;
  dateScope: SearchDateScope;
  selectedGroups: string[];
  selectedSources?: string[];
  onlineOnly: boolean;
  minScore: number;
  curatedOnly?: boolean;
}

export interface SearchResultItem {
  resultId?: string;
  program: EpgProgramItem;
  channel: ChannelItem;
  score: number;
  isLive: boolean;
  startDate: Date;
  endDate: Date;
  timeLabel: string;
  durationMins: number;
}

/**
 * Checks if an EPG programme falls into the selected calendar date scope.
 *
 * @param program Target EPG programme item.
 * @param scope Date scope filter ('today' or 'all').
 * @param refDate Reference calendar date (defaults to current system time).
 * @returns True if programme satisfies the date filter.
 */
export function isProgramWithinDateScope(
  program: EpgProgramItem,
  scope: SearchDateScope,
  refDate: Date = new Date()
): boolean {
  if (scope === 'all') return true;
  const start = parseXmltvDate(program.s);
  const end = parseXmltvDate(program.e);
  if (!start) return false;

  if (end && refDate.getTime() >= start.getTime() && refDate.getTime() <= end.getTime()) {
    return true;
  }

  const dayStart = new Date(refDate);
  dayStart.setHours(0, 0, 0, 0);

  if (scope === 'today') {
    const dayEnd = new Date(dayStart);
    dayEnd.setDate(dayEnd.getDate() + 1);
    return (start.getTime() >= dayStart.getTime() && start.getTime() < dayEnd.getTime()) ||
      Boolean(end && end.getTime() > dayStart.getTime() && start.getTime() < dayEnd.getTime());
  }

  if (scope === 'three_days') {
    const daysEnd = new Date(dayStart);
    daysEnd.setDate(daysEnd.getDate() + 3);
    return (start.getTime() >= dayStart.getTime() && start.getTime() < daysEnd.getTime()) ||
      Boolean(end && end.getTime() > dayStart.getTime() && start.getTime() < daysEnd.getTime());
  }

  return true;
}

/**
 * Checks if a programme broadcasts during prime time evening hours (20:30 - 23:00).
 *
 * @param program Target EPG programme item.
 * @param refDate Reference date.
 * @returns True if programme overlaps with prime time window.
 */
export function isProgramInPrimeTime(
  program: EpgProgramItem,
  _refDate: Date = new Date()
): boolean {
  const start = parseXmltvDate(program.s);
  const end = parseXmltvDate(program.e);
  if (!start || !end) return false;

  const ptStart = new Date(start);
  ptStart.setHours(20, 30, 0, 0);
  const ptEnd = new Date(start);
  ptEnd.setHours(23, 0, 0, 0);

  return start.getTime() < ptEnd.getTime() && end.getTime() > ptStart.getTime();
}

/**
 * Filters and scores EPG programme items across channels against active search criteria.
 *
 * @param channels List of available channel items.
 * @param epgData Map of namespaced EPG IDs to list of programme items.
 * @param filters Search and facet filter options.
 * @param config Optional NLP and scoring configuration (stopwords, methods A-D).
 * @param refDate Reference execution timestamp.
 * @returns Scored and ordered list of search result items.
 */
export function filterAndScoreProgrammes(
  channels: ChannelItem[],
  epgData: Record<string, EpgProgramItem[]>,
  filters: SearchFilterOptions,
  config: {
    language?: string;
    customStopwords?: string[];
    searchMethods?: SearchMethodsConfig;
  } = {},
  refDate: Date = new Date()
): SearchResultItem[] {
  const queryTrimmed = (filters.query || '').trim();
  const hasQuery = Boolean(queryTrimmed);

  const stopwords = getMergedStopwords(config.language || 'it', config.customStopwords || []);
  const methods = config.searchMethods || {
    method_a: true,
    method_b: true,
    method_c: true,
    method_d: true
  };
  const tokens = hasQuery
    ? tokenizeQuery(queryTrimmed, stopwords, methods.method_b, methods.method_c)
    : [];

  const results: SearchResultItem[] = [];
  const seenKeys = new Set<string>();

  for (const channel of channels) {
    if (!channel.is_included) continue;
    if (filters.curatedOnly && !channel.is_bookmarked) {
      continue;
    }
    if (filters.selectedGroups.length > 0 && !filters.selectedGroups.includes(channel.group || '')) {
      continue;
    }
    if (filters.selectedSources && filters.selectedSources.length > 0 && !filters.selectedSources.includes(channel.source || '')) {
      continue;
    }
    if (filters.onlineOnly && channel.link_status !== 'online') {
      continue;
    }

    const progs = getProgrammesForChannelFromEpgData(channel, epgData);
    for (const prog of progs) {
      const channelKey = channel.id || channel.original_url || channel.name;
      const dedupeKey = `${channelKey}::${prog.s}::${prog.e || ''}::${prog.t}`;
      if (seenKeys.has(dedupeKey)) continue;
      seenKeys.add(dedupeKey);

      const start = parseXmltvDate(prog.s);
      const end = parseXmltvDate(prog.e);
      if (!start || !end) continue;

      const isLive = isProgrammeCurrentlyLive(prog, refDate);
      if (filters.liveOnly && !isLive) continue;
      if (filters.primeTimeOnly && !isProgramInPrimeTime(prog, refDate)) continue;

      if (!isProgramWithinDateScope(prog, filters.dateScope, refDate)) continue;

      let score = 0;
      if (hasQuery) {
        score = scoreProgrammeMatch(prog, tokens, methods, refDate);
        if (score <= 0) continue;
        if (filters.minScore > 0 && score < filters.minScore) continue;
      } else {
        score = isLive ? 100 : 50;
      }

      const durationMins = Math.max(1, Math.round((end.getTime() - start.getTime()) / 60000));
      const formatTime = (d: Date) =>
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      const timeLabel = `${formatTime(start)} - ${formatTime(end)}`;

      results.push({
        resultId: dedupeKey,
        program: prog,
        channel,
        score,
        isLive,
        startDate: start,
        endDate: end,
        timeLabel,
        durationMins
      });
    }
  }

  return sortSearchResults(results, hasQuery);
}

/**
 * Sorts search results by relevance score (when query active) or by live status and time.
 *
 * @param items List of scored search result items.
 * @param hasQuery Whether a textual search query is active.
 * @returns Ordered search result items.
 */
export function sortSearchResults(
  items: SearchResultItem[],
  hasQuery: boolean
): SearchResultItem[] {
  return [...items].sort((a, b) => {
    if (hasQuery) {
      if (b.score !== a.score) {
        return b.score - a.score;
      }
    }
    if (a.isLive !== b.isLive) {
      return a.isLive ? -1 : 1;
    }
    return a.startDate.getTime() - b.startDate.getTime();
  });
}

/**
 * Escapes HTML characters to prevent XSS.
 *
 * @param str Raw string input.
 * @returns Escaped HTML string.
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Wraps matched query tokens in text with semantic amber mark highlight tags.
 *
 * @param text Original source text to highlight.
 * @param tokens List of search query tokens.
 * @returns Sanitized HTML string with marked token matches.
 */
export function highlightQueryMatches(text: string, tokens: string[] = []): string {
  if (!text) return '';
  const validTokens = tokens
    .map((t) => t.trim())
    .filter((t) => t.length > 0);

  if (validTokens.length === 0) {
    return escapeHtml(text);
  }

  const escapedPatterns = validTokens.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const regex = new RegExp(`(${escapedPatterns.join('|')})`, 'gi');
  const parts = text.split(regex);

  return parts
    .map((part) => {
      if (validTokens.some((t) => t.toLowerCase() === part.toLowerCase())) {
        return `<mark class="bg-primary/20 text-primary rounded px-0.5 font-semibold">${escapeHtml(part)}</mark>`;
      }
      return escapeHtml(part);
    })
    .join('');
}

/**
 * Groups flat search result items by parent channel identity.
 *
 * @param items List of search result items.
 * @returns Ordered channel-grouped result items list.
 */
export function groupResultsByChannel(items: SearchResultItem[]): ChannelGroupedSearchResult[] {
  const groupsMap = new Map<string, { channel: ChannelItem; items: SearchResultItem[]; seenProgKeys: Set<string> }>();

  for (const item of items) {
    const key = item.channel.id || item.channel.original_url || item.channel.name;
    if (!groupsMap.has(key)) {
      groupsMap.set(key, { channel: item.channel, items: [], seenProgKeys: new Set<string>() });
    }
    const groupEntry = groupsMap.get(key)!;
    const progKey = `${item.program.s}::${item.program.e || ''}::${item.program.t}`;
    if (groupEntry.seenProgKeys.has(progKey)) continue;
    groupEntry.seenProgKeys.add(progKey);
    groupEntry.items.push(item);
  }

  const grouped: ChannelGroupedSearchResult[] = [];
  for (const group of groupsMap.values()) {
    const sortedItems = [...group.items].sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.startDate.getTime() - b.startDate.getTime();
    });
    const totalScore = sortedItems.reduce((sum, it) => sum + it.score, 0);
    grouped.push({
      channel: group.channel,
      items: sortedItems,
      totalScore,
      bestItem: sortedItems[0]
    });
  }

  return grouped.sort((a, b) => {
    if (b.bestItem.score !== a.bestItem.score) {
      return b.bestItem.score - a.bestItem.score;
    }
    return a.channel.name.localeCompare(b.channel.name);
  });
}

/**
 * Resolves score badge label and color variant for a search result item.
 *
 * @param item Search result item.
 * @returns Object with badge label and UI variant.
 */
export function getMatchScoreBadgeDetails(item: SearchResultItem): {
  label: string;
  variant: 'muted';
} {
  return { label: `${item.score}`, variant: 'muted' };
}

/**
 * Returns clean English label for date scope.
 *
 * @param scope Target date scope.
 * @returns Standard English display label.
 */
export function formatDateScopeLabel(scope: SearchDateScope): string {
  if (scope === 'today') return 'TODAY';
  if (scope === 'three_days') return '3 DAYS';
  return 'ALL';
}
