import type { ChannelItem } from '$lib/api/types';
import type { TableColumn } from '../../ui/TableUtils';
import { truncateMiddle } from '$lib/utils/stringUtils';

export { truncateMiddle };
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
export type ChannelsHubTab = 'channels' | 'merge' | 'sources';

export type HealthViewMode = 'normal' | 'full';

export interface TableColumnOption {
  key: string;
  label: string;
}

export const ALL_CHANNEL_COLUMNS: TableColumnOption[] = [
  { key: 'logo', label: 'Channel Logo' },
  { key: 'name', label: 'Channel Name' },
  { key: 'source', label: 'Source Provider' },
  { key: 'group', label: 'Category Group' },
  { key: 'bookmark', label: 'Star Bookmark' },
  { key: 'link_status', label: 'Link Health Status' },
  { key: 'epg', label: 'EPG Guide Mapping' },
  { key: 'inclusion', label: 'Inclusion (INC/EXC)' },
  { key: 'merge', label: 'Failover & Merges' },
  { key: 'details', label: 'Details Action' },
  { key: 'play', label: 'Live Playback Action' }
];

export const CHANNEL_TABLE_COLUMNS: TableColumn<ChannelItem>[] = [
  { key: 'logo', label: 'Logo', align: 'center', width: 'w-16' },
  { key: 'name', label: 'Name', sortable: true, align: 'left', width: 'w-44' },
  { key: 'group', label: 'Group', sortable: true, align: 'left', width: 'w-28' },
  { key: 'url', label: 'Stream URL', align: 'left' },
  { key: 'source', label: 'Source', sortable: true, align: 'left', width: 'w-32' },
  { key: 'link_status', label: 'Link', sortable: true, align: 'center', width: 'w-16' },
  { key: 'is_included', label: 'Status', sortable: true, align: 'center', width: 'w-16' },
  { key: 'is_mapped', label: 'EPG', sortable: true, align: 'center', width: 'w-20' },
  { key: 'cors', label: 'CORS', sortable: true, align: 'center', width: 'w-20' },
  { key: 'user_agent', label: 'User-Agent', align: 'left', width: 'w-28' },
  { key: 'rewrites', label: 'Rewrites', align: 'left', width: 'w-24' },
  { key: 'actions', label: 'Actions', align: 'center', width: 'w-40' }
];

export interface ChannelMetadataFieldConfig {
  label: string;
  key: 'name' | 'group' | 'logo' | 'user_agent' | 'url';
  actionTitle: string;
  isLogo?: boolean;
}

export const CHANNEL_METADATA_FIELDS: ChannelMetadataFieldConfig[] = [
  { label: 'Name', key: 'name', actionTitle: 'Edit channel name' },
  { label: 'Group', key: 'group', actionTitle: 'Edit group / rewrites' },
  { label: 'Logo URL', key: 'logo', actionTitle: 'Edit logo URL', isLogo: true },
  { label: 'User-Agent', key: 'user_agent', actionTitle: 'Edit User-Agent' },
  { label: 'Stream URL', key: 'url', actionTitle: 'Edit stream URL' }
];

export const DEFAULT_VISIBLE_COLUMNS: string[] = [
  'logo',
  'name',
  'source',
  'group',
  'bookmark',
  'link_status',
  'epg',
  'inclusion',
  'merge',
  'details',
  'play'
];

export interface ChannelFilterOptions {
  searchQuery?: string;
  selectedGroup?: string;
  selectedSource?: string;
  selectedGroups?: string[];
  selectedSources?: string[];
  linkStatus?: string;
  inclusionStatus?: string;
  epgStatus?: string;
  corsStatus?: string;
  bookmarkStatus?: string;
}

/**
 * Filters an array of ChannelItem objects based on criteria.
 *
 * @param channels Source channel items list.
 * @param filters Active filter configuration object.
 * @returns Filtered channels array.
 */
export function filterChannels(
  channels: ChannelItem[],
  filters: ChannelFilterOptions
): ChannelItem[] {
  if (!Array.isArray(channels)) return [];

  const query = (filters.searchQuery || '').toLowerCase().trim();
  const singleGroup = filters.selectedGroup || '';
  const singleSource = filters.selectedSource || '';
  const selGroups = Array.isArray(filters.selectedGroups)
    ? filters.selectedGroups
    : (singleGroup ? [singleGroup] : []);
  const selSources = Array.isArray(filters.selectedSources)
    ? filters.selectedSources
    : (singleSource ? [singleSource] : []);

  const link = (filters.linkStatus || 'all').toLowerCase();
  const inclusion = (filters.inclusionStatus || 'all').toLowerCase();
  const epg = (filters.epgStatus || 'all').toLowerCase();
  const cors = (filters.corsStatus || 'all').toLowerCase();
  const bookmark = (filters.bookmarkStatus || 'all').toLowerCase();

  return channels.filter((ch) => {
    if (!ch) return false;

    if (query) {
      const nameMatch = (ch.name || '').toLowerCase().includes(query) ||
        (ch.original_data?.name || '').toLowerCase().includes(query);
      const groupMatch = (ch.group || '').toLowerCase().includes(query) ||
        (ch.original_data?.group || '').toLowerCase().includes(query);
      const epgIdMatch = (ch.epg_id || '').toLowerCase().includes(query);
      const urlMatch = (ch.url || '').toLowerCase().includes(query) ||
        (ch.original_url || '').toLowerCase().includes(query);
      const uaMatch = (ch.user_agent || '').toLowerCase().includes(query);
      const rewriteMatch = Array.isArray(ch.rewrites) &&
        ch.rewrites.some((r) => r.toLowerCase().includes(query));

      if (!nameMatch && !groupMatch && !epgIdMatch && !urlMatch && !uaMatch && !rewriteMatch) {
        return false;
      }
    }

    const chGroup = ch.group || '';
    if (selGroups.length > 0 && !selGroups.includes(chGroup)) {
      return false;
    }

    const chSource = ch.source || '';
    if (selSources.length > 0 && !selSources.includes(chSource)) {
      return false;
    }

    const chLink = (ch.link_status || 'unchecked').toLowerCase();
    if (link !== 'all' && chLink !== link) {
      return false;
    }

    if (inclusion !== 'all') {
      const isInc = Boolean(ch.is_included);
      if (inclusion === 'included' && !isInc) return false;
      if (inclusion === 'excluded' && isInc) return false;
    }

    if (epg !== 'all') {
      const isMapped = Boolean(ch.is_mapped);
      if (epg === 'mapped' && !isMapped) return false;
      if (epg === 'unmapped' && isMapped) return false;
    }

    if (cors !== 'all') {
      if (cors === 'cors_ok' && !ch.cors_supported) return false;
      if (cors === 'needs_proxy' && !ch.needs_proxy) return false;
    }

    if (bookmark !== 'all') {
      const isBookmarked = Boolean(ch.is_bookmarked);
      const bookmarkedLists = ch.bookmarked_playlist_ids || (isBookmarked ? ['default'] : []);
      if (bookmark === 'bookmarked' && !isBookmarked && bookmarkedLists.length === 0) return false;
      if (bookmark === 'not_bookmarked' && (isBookmarked || bookmarkedLists.length > 0)) return false;
      if (bookmark.startsWith('playlist:')) {
        const targetPlId = bookmark.replace('playlist:', '');
        if (!bookmarkedLists.includes(targetPlId)) return false;
      }
    }

    return true;
  });
}

/**
 * Extracts unique group names sorted alphabetically from channels array.
 *
 * @param channels Source channels list.
 * @returns Sorted unique group names array.
 */
export function extractUniqueGroups(channels: ChannelItem[]): Array<{ label: string; value: string }> {
  const groups = new Set<string>();
  let hasEmptyGroup = false;

  channels.forEach((ch) => {
    if (ch.group && ch.group.trim()) {
      groups.add(ch.group.trim());
    } else {
      hasEmptyGroup = true;
    }
  });

  const result: Array<{ label: string; value: string }> = Array.from(groups)
    .sort()
    .map((g) => ({ label: g, value: g }));

  if (hasEmptyGroup) {
    result.unshift({ label: '(Uncategorized / Empty)', value: '' });
  }

  return result;
}

/**
 * Extracts unique source provider names sorted alphabetically from channels array.
 *
 * @param channels Source channels list.
 * @returns Array of source TagOption items.
 */
export function extractUniqueSources(channels: ChannelItem[]): Array<{ label: string; value: string }> {
  const sources = new Set<string>();
  channels.forEach((ch) => {
    if (ch.source) sources.add(ch.source.trim());
  });

  return Array.from(sources)
    .sort()
    .map((s) => ({ label: s, value: s }));
}


/**
 * Result payload returned by channel stream status update routines.
 */
export interface ChannelStreamUpdateResult {
  updatedList: ChannelItem[];
  updated: boolean;
  targetName: string;
}

/**
 * Updates channel stream link, CORS, and proxy status immutably when a player status event is received.
 *
 * @param channels Array of ChannelItem objects.
 * @param event Stream status update event.
 * @returns ChannelStreamUpdateResult with updated list, boolean flag, and matched channel name.
 */
export function updateChannelStreamStatus(
  channels: ChannelItem[],
  event: StreamStatusUpdateEvent
): ChannelStreamUpdateResult {
  let updated = false;
  let targetName = '';

  const updatedList = (channels || []).map((ch) => {
    const matches = (event.channelId && ch.id === event.channelId) ||
      (ch.original_url === event.originalUrl && (!event.source || ch.source === event.source));
    if (matches) {
      updated = true;
      targetName = ch.name;
      return {
        ...ch,
        link_status: event.link_status,
        cors_supported: event.cors_supported,
        needs_proxy: event.needs_proxy
      };
    }
    return ch;
  });

  return { updatedList, updated, targetName };
}


/**
 * Tests image reachability via HTML Image loader.
 *
 * @param url Image URL to test.
 * @returns Promise resolving to boolean reachability result.
 */
export function testImageReachability(url: string): Promise<boolean> {
  if (!url || !url.trim() || typeof Image === 'undefined') {
    return Promise.resolve(false);
  }
  return new Promise<boolean>((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url.trim();
  });
}
