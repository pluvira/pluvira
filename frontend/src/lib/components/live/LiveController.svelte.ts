import { api } from '$lib/api/client';
import type { ChannelItem, ChannelRewritePayload } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
import { getPreference, setPreference, getLiveChannelScope, setLiveChannelScope, type LiveChannelScope } from '$lib/utils/preferences';
import { extractUniqueEpgIds, getEpgDateRange, type EpgProgramItem, type TvMobileTab } from './utils';
import { updateChannelStreamStatus } from '../channels/utils/ChannelsUtils';

export class LiveController {
  public loading = $state(false);
  public channelScope = $state<LiveChannelScope>(getLiveChannelScope());
  public allChannels = $state<ChannelItem[]>([]);
  public filteredChannels = $state<ChannelItem[]>([]);
  public activeChannel = $state<ChannelItem | null>(null);
  public epgData = $state<Record<string, EpgProgramItem[]>>({});
  public page = $state(1);
  public pageSize = $state(20);
  public totalPages = $derived(
    Math.max(1, Math.ceil((this.filteredChannels?.length || 0) / (this.pageSize || 20)))
  );
  public paginatedChannels = $derived.by(() => {
    const start = (this.page - 1) * (this.pageSize || 20);
    return (this.filteredChannels || []).slice(start, start + (this.pageSize || 20));
  });

  public showMergeSheet = $state(false);
  public selectedMergeChannel = $state<ChannelItem | null>(null);
  public activeMobileTab = $state<TvMobileTab>(getPreference<TvMobileTab>('tv_active_mobile_tab', 'epg'));

  public channelQuery = $state(getPreference<string>('tv_channel_search', ''));
  public get searchQuery(): string {
    return this.channelQuery;
  }
  public set searchQuery(val: string) {
    this.channelQuery = val;
  }
  public showDetailsModal = $state(false);
  public showEditModal = $state(false);
  public showMappingModal = $state(false);
  public showScannerModal = $state(false);
  public showLogoModal = $state(false);
  public showFieldModal = $state(false);
  public field = $state<ChannelRewritePayload['field']>('name');
  public activeFieldLabel = $state('Attribute');
  public selectedModalChannel = $state<ChannelItem | null>(null);

  public selectedDateStr = $state(
    (() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    })()
  );
  public containerWidth = $state(1200);
  public hoursVisible = $state(getPreference<number>('tv_hours_visible', 6));
  public timelineWidth = $derived(
    Math.max(1200, Math.round(((this.containerWidth || 1200) / (this.hoursVisible || 6)) * 72))
  );
  public scrollOffsetPx = $state(0);

  /**
   * Fetches playlist channels and live EPG programmes from API.
   */
  public async loadTvData(): Promise<void> {
    const t0 = performance.now();
    console.log('[LiveController] loadTvData start...');
    this.loading = true;
    try {
      const response = await api.getChannels({ limit: 1000 });
      console.log(`[LiveController] getChannels in ${(performance.now() - t0).toFixed(1)}ms (${response.items?.length || 0} channels).`);
      const items: ChannelItem[] = response.items || [];

      this.allChannels = items;
      this.applyFilters();

      const lastChannelId = getPreference<string>('tv_last_channel_id', '');
      if (lastChannelId) {
        const restored = this.filteredChannels.find((c) => c.id === lastChannelId);
        if (restored) {
          this.activeChannel = restored;
        }
      }

      if (!this.activeChannel && this.filteredChannels.length > 0) {
        this.activeChannel = this.filteredChannels[0];
      } else if (this.activeChannel) {
        const matched = this.allChannels.find((c) => c.id === this.activeChannel!.id);
        if (matched) this.activeChannel = matched;
      }

      await this.loadVisibleEpg();
      this.handleDeepLinkParams();
      console.log(`[LiveController] loadTvData complete in ${(performance.now() - t0).toFixed(1)}ms (${this.filteredChannels.length} active).`);
    } catch (err: any) {
      console.error('[LiveController] loadTvData failed:', err);
      toastStore.error(`Failed to load TV guide data: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Resolves programme guide items for a channel matching namespaced or raw EPG keys.
   *
   * @param channel Target ChannelItem.
   */
  public getProgrammesForChannel(channel?: ChannelItem | null): EpgProgramItem[] {
    if (!channel?.epg_id || !this.epgData) return [];
    const epgId = channel.epg_id;
    if (this.epgData[epgId] && this.epgData[epgId].length > 0) return this.epgData[epgId];
    if (epgId.includes('::')) {
      const rawId = epgId.split('::', 1)[1];
      if (this.epgData[rawId] && this.epgData[rawId].length > 0) return this.epgData[rawId];
    }
    for (const [k, progs] of Object.entries(this.epgData)) {
      if (k.endsWith(`::${epgId}`) && progs.length > 0) return progs;
    }
    return this.epgData[epgId] || [];
  }

  /**
   * Selects a channel for live streaming and updates metadata.
   *
   * @param channel Target ChannelItem.
   */
  public selectChannel(channel: ChannelItem): void {
    this.activeChannel = channel;
    if (channel?.id) {
      setPreference('tv_last_channel_id', channel.id);
      this.loadVisibleEpg();
    }
  }

  /**
   * Switches the active tab on mobile viewport and persists user preference.
   *
   * @param tab Target mobile tab ('epg' | 'channels' | 'details').
   */
  public setMobileTab(tab: TvMobileTab): void {
    this.activeMobileTab = tab;
    setPreference('tv_active_mobile_tab', tab);
  }

  /**
   * Sets the active channel page index.
   *
   * @param p 1-based page index.
   */
  public setPage(p: number): void {
    if (p >= 1 && p <= this.totalPages) {
      this.page = p;
      this.loadVisibleEpg();
    }
  }

  /**
   * Advances channel page to next slice.
   */
  public nextPage(): void {
    if (this.page < this.totalPages) {
      this.page += 1;
      this.loadVisibleEpg();
    }
  }

  /**
   * Moves channel page to previous slice.
   */
  public prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadVisibleEpg();
    }
  }

  /**
   * Opens the localized failover & backup streams management sheet for a channel.
   *
   * @param channel Target ChannelItem.
   */
  public openMergeSheet(channel: ChannelItem): void {
    this.selectedMergeChannel = channel;
    this.showMergeSheet = true;
  }

  /**
   * Closes the localized failover sheet.
   */
  public closeMergeSheet(): void {
    this.showMergeSheet = false;
    this.selectedMergeChannel = null;
  }

  /**
   * Toggles channel scope between curated list and all channels.
   */
  public toggleChannelScope(): void {
    this.channelScope = this.channelScope === 'curated' ? 'all' : 'curated';
    setLiveChannelScope(this.channelScope);
    this.page = 1;
    this.applyFilters();
  }

  /**
   * Explicitly sets channel scope mode and updates filters.
   *
   * @param scope Target scope ('curated' | 'all').
   */
  public setChannelScope(scope: LiveChannelScope): void {
    this.channelScope = scope;
    setLiveChannelScope(scope);
    this.page = 1;
    this.applyFilters();
  }

  /**
   * Filters channels list by channel name query.
   */
  public applyFilters(): void {
    const chQ = (this.channelQuery || '').toLowerCase().trim();

    let filtered = this.allChannels.filter((ch) => {
      if (!ch.is_included) return false;
      if (this.channelScope === 'curated' && !ch.is_bookmarked) return false;
      if (chQ) {
        return (ch.name || '').toLowerCase().includes(chQ) ||
               (ch.group || '').toLowerCase().includes(chQ) ||
               (ch.epg_id || '').toLowerCase().includes(chQ);
      }
      return true;
    });

    filtered.sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { numeric: true, sensitivity: 'base' }));
    this.filteredChannels = filtered;
    if (this.page > this.totalPages) {
      this.page = Math.max(1, this.totalPages);
    }

    if (this.activeChannel && !this.filteredChannels.some((c) => c.id === this.activeChannel!.id)) {
      if (this.filteredChannels.length > 0) {
        this.activeChannel = this.filteredChannels[0];
      }
    } else if (!this.activeChannel && this.filteredChannels.length > 0) {
      this.activeChannel = this.filteredChannels[0];
    }

    setPreference('tv_channel_search', this.channelQuery || '');
    setPreference('tv_hours_visible', this.hoursVisible);
    this.loadVisibleEpg();
  }

  /**
   * Fetches EPG programmes for currently visible paginated channels and active channel.
   * Merges batches into local in-memory epgData cache.
   */
  public async loadVisibleEpg(): Promise<void> {
    const targetChannels = [...this.paginatedChannels];
    if (this.activeChannel && !targetChannels.some((c) => c.id === this.activeChannel!.id)) {
      targetChannels.push(this.activeChannel);
    }

    const uniqueIds = extractUniqueEpgIds(targetChannels);
    const missingIds = uniqueIds.filter((id) => !this.epgData[id]);
    const t0 = performance.now();
    console.log(`[LiveController] loadVisibleEpg: ${targetChannels.length} channels, ${uniqueIds.length} EPG IDs, ${missingIds.length} missing.`);

    if (missingIds.length === 0) return;

    try {
      const curr = new Date(this.selectedDateStr + 'T00:00:00');
      const { date_from, date_to } = getEpgDateRange(curr, 3, 1);
      const batch = await api.getEpgProgrammes({
        ids: missingIds,
        date_from,
        date_to
      });
      if (batch && Object.keys(batch).length > 0) {
        const batchKeys = Object.keys(batch);
        const progCount = Object.values(batch).reduce<number>((acc, p) => acc + (Array.isArray(p) ? p.length : 0), 0);
        console.log(`[LiveController] getEpgProgrammes in ${(performance.now() - t0).toFixed(1)}ms: ${batchKeys.length} channels, ${progCount} progs.`);
        this.epgData = { ...this.epgData, ...batch };
      }
    } catch (err: any) {
      console.error(`[LiveController] getEpgProgrammes error after ${(performance.now() - t0).toFixed(1)}ms:`, err);
    }
  }

  /**
   * Toggles inclusion status for a single channel item and refreshes active state.
   */
  public async toggleChannelInclusion(channel: ChannelItem): Promise<void> {
    if (!channel) return;
    const targetInclusion = !channel.is_included;
    try {
      await api.bulkSetInclusion({
        channel_items: [{ original_data: channel.original_data || { name: channel.name }, source: channel.source }],
        is_included: targetInclusion
      });
      toastStore.success(`Channel '${channel.name}' ${targetInclusion ? 'included' : 'excluded'}.`);
      channel.is_included = targetInclusion;
      this.allChannels = this.allChannels.map((c) => (c.id === channel.id ? { ...c, is_included: targetInclusion } : c));
      this.applyFilters();
      if (this.activeChannel?.id === channel.id) {
        if (targetInclusion) {
          this.activeChannel = { ...this.activeChannel, is_included: true };
        } else {
          this.activeChannel = this.filteredChannels[0] || null;
        }
      }
    } catch (err: any) {
      toastStore.error(`Failed to toggle inclusion: ${err.message}`);
    }
  }

  public openDetailsModal(channel: ChannelItem): void {
    this.selectedModalChannel = channel;
    this.showDetailsModal = true;
  }

  public openEditModal(channel: ChannelItem): void {
    this.selectedModalChannel = channel;
    this.showEditModal = true;
  }

  public openMappingModal(channel: ChannelItem): void {
    this.selectedModalChannel = channel;
    this.showMappingModal = true;
  }

  public openScannerModal(channel: ChannelItem): void {
    this.selectedModalChannel = channel;
    this.showScannerModal = true;
  }

  public openLogoModal(channel: ChannelItem): void {
    this.selectedModalChannel = channel;
    this.showLogoModal = true;
  }

  public openFieldModal(channel: ChannelItem, field: ChannelRewritePayload['field'], label: string): void {
    this.selectedModalChannel = channel;
    this.field = field;
    this.activeFieldLabel = label;
    this.showFieldModal = true;
  }

  /**
   * Parses deep-link hash parameters and navigates timeline/channel selection.
   */
  private handleDeepLinkParams(): void {
    if (typeof window === 'undefined') return;
    const hash = window.location.hash;
    if (!hash.includes('?')) return;

    const params = new URLSearchParams(hash.split('?')[1]);
    const targetChannelId = params.get('channel');
    const targetTimeEpoch = params.get('time');

    if (targetChannelId) {
      const ch = this.allChannels.find((c) => c.id === targetChannelId);
      if (ch) {
        this.channelQuery = '';
        this.applyFilters();
        this.selectChannel(ch);

        const targetIndex = this.filteredChannels.findIndex((c) => c.id === targetChannelId);
        if (targetIndex >= 0) {
          this.page = Math.floor(targetIndex / (this.pageSize || 20)) + 1;
        }

        if (targetTimeEpoch) {
          const epoch = parseInt(targetTimeEpoch, 10);
          if (!isNaN(epoch)) {
            const targetDate = new Date(epoch);
            const dayStart = new Date(targetDate);
            dayStart.setHours(0, 0, 0, 0);
            const elapsedMs = targetDate.getTime() - dayStart.getTime();
            const windowMs = 3 * 86400 * 1000;
            const viewportWidth = this.containerWidth || 800;
            this.scrollOffsetPx = Math.max(0, (elapsedMs / windowMs) * this.timelineWidth - viewportWidth / 3);
          }
        }
      }
    }
  }

  /**
   * Updates timeline zoom level.
   *
   * @param hours Number of hours visible in viewport.
   */
  public setZoom(hours: number): void {
    this.hoursVisible = Math.max(1, Math.min(24, hours));
    setPreference('tv_hours_visible', this.hoursVisible);
  }

  /**
   * Scrolls the horizontal timeline grid towards previous, current (now), or next window.
   *
   * @param direction Target scroll direction.
   */
  public scrollTimeline(direction: 'prev' | 'now' | 'next'): void {
    const viewportWidth = this.containerWidth || 800;
    const maxScroll = Math.max(0, this.timelineWidth - viewportWidth);

    if (direction === 'now') {
      const now = new Date();
      const dayStart = new Date(now);
      dayStart.setHours(0, 0, 0, 0);
      const elapsedMs = now.getTime() - dayStart.getTime();
      const windowMs = 3 * 86400 * 1000;
      this.scrollOffsetPx = Math.max(0, (elapsedMs / windowMs) * this.timelineWidth - viewportWidth / 3);
    } else if (direction === 'next') {
      this.scrollOffsetPx = Math.min(maxScroll, this.scrollOffsetPx + viewportWidth / 2);
    } else if (direction === 'prev') {
      this.scrollOffsetPx = Math.max(0, this.scrollOffsetPx - viewportWidth / 2);
    }
  }

  /**
   * Updates channel link status and CORS parameters reactively.
   *
   * @param event Stream status update event from player.
   */
  public handleStreamStatusUpdate(event: StreamStatusUpdateEvent): void {
    const res = updateChannelStreamStatus(this.allChannels, event);
    if (res.updated) {
      this.allChannels = res.updatedList;
      if (this.activeChannel) {
        const matched = this.allChannels.find((c) => c.id === this.activeChannel!.id);
        if (matched) this.activeChannel = matched;
      }
      this.applyFilters();
      if (event.link_status === 'offline' && event.errorCode) {
        toastStore.warning(`Live Stream KO (${res.targetName || 'Channel'}): ${event.errorCode}`);
      }
    }
  }
}
