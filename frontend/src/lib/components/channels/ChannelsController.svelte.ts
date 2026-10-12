import { api } from '$lib/api/client';
import type {
  ChannelItem,
  ChannelRewritePayload,
  SourceStatItem,
  EpgSourceStatItem
} from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import { licenseStore } from '$lib/stores/licenseStore';
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
import { getPreference, setPreference, getHashQueryParam } from '$lib/utils/preferences';
import { countChannelFilters } from '$lib/utils/objectUtils';
import {
  filterChannels,
  extractUniqueGroups,
  extractUniqueSources,
  updateChannelStreamStatus,
  DEFAULT_VISIBLE_COLUMNS,
  type ChannelFilterOptions,
  type ChannelsHubTab,
  type HealthViewMode
} from './utils/ChannelsUtils';

export interface BulkModalState {
  open: boolean;
  actionType: 'group' | 'user_agent';
  title: string;
  label: string;
  suggestions: string[];
}

export class ChannelsController {
  public loading = $state(false);
  public activeTab = $state<ChannelsHubTab>(
    (getHashQueryParam('tab') as ChannelsHubTab) || getPreference<ChannelsHubTab>('ch_active_hub_tab', 'channels')
  );
  public healthViewMode = $state<HealthViewMode>(
    getPreference<HealthViewMode>('ch_health_view_mode', 'normal')
  );
  public showFilterSheet = $state(false);
  public showMergeSheet = $state(false);
  public showTrialModal = $state(false);
  public showPurgeModal = $state(false);
  public showAutoAssignModal = $state(false);
  public autoAssigning = $state(false);
  public selectedMergeChannel = $state<ChannelItem | null>(null);
  public sourcesStats = $state<SourceStatItem[]>([]);
  public epgSourcesStats = $state<EpgSourceStatItem[]>([]);
  public activeChannel = $state<ChannelItem | null>(null);

  public showDetailsModal = $state(false);
  public showEditModal = $state(false);
  public showLogoModal = $state(false);
  public showFieldModal = $state(false);
  public showScannerModal = $state(false);
  public showMappingModal = $state(false);
  public showColumnsModal = $state(false);
  public showBulkTestModal = $state(false);

  public field = $state<ChannelRewritePayload['field']>('name');
  public activeFieldLabel = $state('Attribute');

  /**
   * Opens the localized failover & backup streams management sheet for a target channel.
   *
   * @param channel Target ChannelItem.
   */
  public openMergeSheet(channel: ChannelItem): void {
    this.selectedMergeChannel = channel;
    this.showMergeSheet = true;
  }

  /**
   * Closes the localized failover management sheet and clears active selection.
   */
  public closeMergeSheet(): void {
    this.showMergeSheet = false;
    this.selectedMergeChannel = null;
  }

  public openTrialModal(): void {
    this.showTrialModal = true;
  }

  public closeTrialModal(): void {
    this.showTrialModal = false;
  }

  public openAutoAssignModal(): void {
    this.showAutoAssignModal = true;
  }

  public closeAutoAssignModal(): void {
    this.showAutoAssignModal = false;
  }

  /**
   * Activates 14-day Pro trial on-demand, updates licenseStore and refreshes catalog.
   */
  public async activateProTrial(token?: string): Promise<boolean> {
    try {
      const res = await api.activateTrial(token);
      toastStore.success(res.message || 'Pluvira Pro 14-day trial activated successfully!');
      const lic = await api.getLicense();
      licenseStore.updateFromLicenseResponse(lic);
      this.closeTrialModal();
      await this.loadChannels();
      return true;
    } catch (err: any) {
      if (err?.errorCode === 'FREE_TIER_LIMIT_EXCEEDED' || err?.status === 403) {
        toastStore.warning('14-day trial has already been claimed for this instance. Upgrade to Pluvira Pro to reactivate unlimited features.');
      } else {
        toastStore.error(err.message || 'Failed to activate trial.');
      }
      return false;
    }
  }
  public bulkModal = $state<BulkModalState>({
    open: false,
    actionType: 'group',
    title: 'Bulk Edit',
    label: 'New Value',
    suggestions: []
  });
  public allChannels = $state<ChannelItem[]>([]);
  public filteredChannels = $state<ChannelItem[]>([]);
  public selectedRows = $state(new Set<string>());

  public visibleColumns = $state<string[]>(
    getPreference('ch_visible_cols', [...DEFAULT_VISIBLE_COLUMNS])
  );

  public filters = $state<ChannelFilterOptions>({
    searchQuery: getPreference('ch_search', ''),
    selectedGroup: '',
    selectedSource: '',
    selectedGroups: getPreference<string[]>('ch_groups', []),
    selectedSources: getPreference<string[]>('ch_sources', []),
    linkStatus: getPreference('ch_link_status', 'all'),
    inclusionStatus: getPreference('ch_inclusion_status', 'all'),
    epgStatus: getPreference('ch_epg_status', 'all'),
    corsStatus: getPreference('ch_cors_status', 'all'),
    bookmarkStatus: getPreference('ch_bookmark_status', 'all')
  });

  public availableGroups = $state<Array<{ label: string; value: string }>>([]);
  public availableSources = $state<Array<{ label: string; value: string }>>([]);

  public get quarantinedCount(): number {
    return (this.allChannels || []).filter((ch) => ch.link_status === 'offline').length;
  }

  public get quarantinedChannels(): ChannelItem[] {
    return (this.allChannels || []).filter((ch) => ch.link_status === 'offline');
  }

  public get unmappedChannelsCount(): number {
    return (this.allChannels || []).filter((ch) => !ch.is_mapped).length;
  }

  public async runAutoAssignEpg(
    scope: 'curated' | 'all' = 'curated',
    threshold = 0.85,
    overwrite = false
  ): Promise<any> {
    this.autoAssigning = true;
    try {
      const playlistId = getPreference<string>('active_playlist_id', 'default');
      const res = await api.autoMapEpg({
        scope,
        playlist_id: playlistId,
        similarity_threshold: threshold,
        overwrite_existing: overwrite,
      });
      toastStore.success(res.message || `Mapped ${res.mapped_count} channel(s) automatically.`);
      await this.loadChannels();
      this.closeAutoAssignModal();
      return res;
    } catch (err: any) {
      if (
        err?.status === 403 ||
        err?.errorCode === 'PRO_FEATURE_REQUIRED' ||
        err?.message?.includes('requires Pluvira Pro')
      ) {
        this.closeAutoAssignModal();
        this.openTrialModal();
      } else {
        toastStore.error(err.message || 'Auto-assign EPG failed.');
      }
      return null;
    } finally {
      this.autoAssigning = false;
    }
  }

  /**
   * Purges all offline quarantined streams across channels.
   */
  public async purgeQuarantined(): Promise<number> {
    try {
      const playlistId = getPreference<string>('active_playlist_id', 'default');
      const res = await api.purgeQuarantined({ playlist_id: playlistId });
      await api.resetScanner();
      this.allChannels = this.allChannels.map((ch) =>
        ch.link_status === 'offline' ? { ...ch, link_status: 'unchecked' as const } : ch
      );
      this.applyFilters();
      this.showPurgeModal = false;
      const purgedCount = res.purged_count || this.quarantinedCount || 1;
      toastStore.success(`Purged ${purgedCount} quarantined stream(s) and reset offline status.`);
      await this.loadChannels();
      return purgedCount;
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : String(err);
      toastStore.error(`Failed to purge quarantined streams: ${msg}`);
      return 0;
    }
  }

  public get activeFilterCount(): number {
    return countChannelFilters(this.filters);
  }
  /**
   * Applies a draft filter state committed from the mobile filter bottom sheet.
   *
   * @param draft Staged ChannelFilterOptions draft object.
   */
  public applyDraftFilters(draft: ChannelFilterOptions): void {
    this.filters = { ...this.filters, ...draft };
    this.applyFilters();
  }

  public removeFilter(key: 'searchQuery' | 'linkStatus' | 'inclusionStatus' | 'epgStatus' | 'corsStatus' | 'bookmarkStatus'): void {
    if (key === 'searchQuery') {
      this.filters.searchQuery = '';
    } else {
      this.filters[key] = 'all';
    }
    this.applyFilters();
  }

  public removeGroupFilter(group: string): void {
    this.filters.selectedGroups = (this.filters.selectedGroups || []).filter((g) => g !== group);
    this.applyFilters();
  }

  public removeSourceFilter(source: string): void {
    this.filters.selectedSources = (this.filters.selectedSources || []).filter((s) => s !== source);
    this.applyFilters();
  }

  /**
   * Resets active filters to default values and reapplies.
   */
  public resetFilters(): void {
    this.filters = {
      searchQuery: this.filters.searchQuery || '',
      selectedGroup: '',
      selectedSource: '',
      selectedGroups: [],
      selectedSources: [],
      linkStatus: 'all',
      inclusionStatus: 'all',
      epgStatus: 'all',
      corsStatus: 'all',
      bookmarkStatus: 'all'
    };
    this.applyFilters();
  }

  /**
   * Switches the active channels hub tab and persists user preference.
   *
   * @param tab Target hub tab ('channels' | 'merge' | 'sources').
   */
  public setActiveTab(tab: ChannelsHubTab): void {
    this.activeTab = tab;
    setPreference('ch_active_hub_tab', tab);
    if (tab === 'sources') {
      this.loadSourcesAnalytics();
    }
  }

  /**
   * Fetches aggregate sources and EPG analytics data.
   */
  public async loadSourcesAnalytics(): Promise<void> {
    try {
      const res = await api.getDashboardAnalytics();
      this.sourcesStats = (res.sources_stats as unknown as SourceStatItem[]) || [];
      this.epgSourcesStats = (res.epg_sources_stats as unknown as EpgSourceStatItem[]) || [];
    } catch {
      this.sourcesStats = [];
      this.epgSourcesStats = [];
    }
  }

  /**
   * Toggles enabled status for an IPTV playlist source.
   */
  public async toggleSource(name: string): Promise<void> {
    try {
      await api.toggleSource(name);
      await this.loadSourcesAnalytics();
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Failed to toggle source '${name}': ${err.message}`);
    }
  }

  /**
   * Toggles enabled status for an EPG guide source.
   */
  public async toggleEpgSource(name: string): Promise<void> {
    try {
      await api.toggleEpgSource(name);
      await this.loadSourcesAnalytics();
    } catch (err: any) {
      toastStore.error(`Failed to toggle EPG source '${name}': ${err.message}`);
    }
  }

  /**
   * Refreshes IPTV sources in bulk and reloads analytics.
   */
  public async refreshSources(names: string[]): Promise<void> {
    try {
      await api.bulkRefreshSources({ names });
      toastStore.success(`Refresh triggered for ${names.length} IPTV source(s).`);
      await this.loadSourcesAnalytics();
    } catch (err: any) {
      toastStore.error(`Failed to refresh sources: ${err.message}`);
    }
  }

  /**
   * Refreshes EPG sources in bulk and reloads analytics.
   */
  public async refreshEpgSources(names: string[]): Promise<void> {
    try {
      await api.bulkRefreshEpgSources({ names });
      toastStore.success(`Refresh triggered for ${names.length} EPG source(s).`);
      await this.loadSourcesAnalytics();
    } catch (err: any) {
      toastStore.error(`Failed to refresh EPG sources: ${err.message}`);
    }
  }

  public openDetailsModal(channel: ChannelItem): void {
    this.activeChannel = channel;
    this.showDetailsModal = true;
  }

  public openEditMetadataModal(channel: ChannelItem): void {
    this.activeChannel = channel;
    this.showEditModal = true;
  }

  public openLogoModal(channel: ChannelItem): void {
    this.activeChannel = channel;
    this.showLogoModal = true;
  }

  public openFieldModal(channel: ChannelItem, field: ChannelRewritePayload['field'], label: string): void {
    this.activeChannel = channel;
    this.field = field;
    this.activeFieldLabel = label;
    this.showFieldModal = true;
  }

  public openScannerModal(channel: ChannelItem): void {
    this.activeChannel = channel;
    this.showScannerModal = true;
  }

  public openMappingModal(channel: ChannelItem): void {
    this.activeChannel = channel;
    this.showMappingModal = true;
  }

  /**
   * Switches Health tab view mode and persists preference.
   *
   * @param mode View mode ('normal' | 'full').
   */
  public setHealthViewMode(mode: HealthViewMode): void {
    this.healthViewMode = mode;
    setPreference('ch_health_view_mode', mode);
  }

  /**
   * Fetches all processed channels from API.
   */
  public async loadChannels(): Promise<void> {
    this.loading = true;
    try {
      const targetTab = getHashQueryParam('tab') as ChannelsHubTab | null;
      if (targetTab && ['channels', 'merge', 'sources'].includes(targetTab)) {
        this.activeTab = targetTab;
      }
      const targetSource = getHashQueryParam('source');
      if (targetSource) {
        this.filters.selectedSources = [targetSource];
      }

      const response: any = await api.getChannels({ limit: 1000 });
      const items = Array.isArray(response) ? response : (response.items || response.channels || []);
      this.allChannels = items;
      this.availableGroups = extractUniqueGroups(this.allChannels);
      this.availableSources = extractUniqueSources(this.allChannels);
      this.applyFilters();
    } catch (err: any) {
      toastStore.error(`Failed to load channels: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Applies active filter configuration to update filteredChannels.
   */
  public applyFilters(): void {
    this.filteredChannels = filterChannels(this.allChannels, this.filters);
    setPreference('ch_search', this.filters.searchQuery || '');
    setPreference('ch_groups', this.filters.selectedGroups || []);
    setPreference('ch_sources', this.filters.selectedSources || []);
    setPreference('ch_link_status', this.filters.linkStatus || 'all');
    setPreference('ch_inclusion_status', this.filters.inclusionStatus || 'all');
    setPreference('ch_epg_status', this.filters.epgStatus || 'all');
    setPreference('ch_cors_status', this.filters.corsStatus || 'all');
    setPreference('ch_bookmark_status', this.filters.bookmarkStatus || 'all');
  }

  /**
   * Toggles visibility of a specific table column key.
   *
   * @param key Column identifier key string.
   * @param visible Desired visibility boolean.
   */
  public toggleColumn(key: string, visible: boolean): void {
    if (visible) {
      if (!this.visibleColumns.includes(key)) {
        this.visibleColumns = [...this.visibleColumns, key];
      }
    } else {
      this.visibleColumns = this.visibleColumns.filter((k) => k !== key);
    }
    setPreference('ch_visible_cols', this.visibleColumns);
  }

  /**
   * Toggles curated playlist bookmark status for a channel.
   *
   * @param channel Target channel item.
   */
  public async toggleBookmark(channel: ChannelItem): Promise<boolean | null> {
    if (!channel) return null;
    try {
      const res = await api.bookmarkChannel({
        playlist_id: getPreference<string>('active_playlist_id', 'default'),
        channel: {
          name: channel.name,
          url: channel.original_url || channel.url,
          source: channel.source,
          group: channel.group,
          logo: channel.logo,
          epg_id: channel.epg_id
        }
      });
      channel.is_bookmarked = res.bookmarked;
      if (res.bookmarked && !channel.is_included) {
        channel.is_included = true;
        await api.bulkSetInclusion({
          channel_items: [{ original_data: channel.original_data || { name: channel.name }, source: channel.source }],
          is_included: true
        }).catch(() => null);
      }
      this.allChannels = this.allChannels.map((c) =>
        c.id === channel.id ? { ...c, is_bookmarked: res.bookmarked, is_included: channel.is_included } : c
      );
      this.applyFilters();
      if (res.bookmarked) {
        toastStore.success(`'${channel.name}' bookmarked in playlist.`);
      } else {
        toastStore.info(`'${channel.name}' removed from playlist.`);
      }
      return res.bookmarked;
    } catch (err: any) {
      if (
        err?.status === 403 ||
        err?.errorCode === 'PERSONAL_CHANNEL_LIMIT_EXCEEDED' ||
        err?.message?.includes('PERSONAL_CHANNEL_LIMIT_EXCEEDED') ||
        err?.message?.includes('maximum 25 channels allowed')
      ) {
        this.showTrialModal = true;
        return null;
      }
      toastStore.error(`Failed to update bookmark: ${err.message}`);
      return null;
    }
  }

  /**
   * Toggles inclusion status for a single channel item.
   *
   * @param channel Target channel item.
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
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Failed to toggle inclusion: ${err.message}`);
    }
  }

  /**
   * Toggles channel inclusion/exclusion status in bulk.
   *
   * @param isIncluded Target inclusion state.
   */
  public async bulkSetInclusion(isIncluded: boolean): Promise<void> {
    const selected = this.allChannels.filter((ch) => this.selectedRows.has(ch.id));
    if (selected.length === 0) return;

    try {
      await api.bulkSetInclusion({
        channel_items: selected.map((ch) => ({ original_data: ch.original_data, source: ch.source })),
        is_included: isIncluded
      });
      toastStore.success(`Inclusion updated for ${selected.length} channels.`);
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Bulk inclusion failed: ${err.message}`);
    }
  }

  /**
   * Assigns a new group in bulk via individual rewrite rules.
   *
   * @param newGroup Group name to set.
   */
  public async bulkSetGroup(newGroup: string): Promise<void> {
    const originalUrls = this.allChannels
      .filter((ch) => this.selectedRows.has(ch.id))
      .map((ch) => ch.original_url);

    if (originalUrls.length === 0) return;

    try {
      await api.bulkSetGroup({ original_urls: originalUrls, group: newGroup });
      toastStore.success(`Group updated for ${originalUrls.length} channels.`);
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Bulk group assignment failed: ${err.message}`);
    }
  }

  /**
   * Assigns a new User-Agent in bulk via individual rewrite rules.
   *
   * @param newUserAgent User-Agent string to set.
   */
  public async bulkSetUserAgent(newUserAgent: string): Promise<void> {
    const originalUrls = this.allChannels
      .filter((ch) => this.selectedRows.has(ch.id))
      .map((ch) => ch.original_url);

    if (originalUrls.length === 0) return;

    try {
      await api.bulkSetUserAgent({ original_urls: originalUrls, user_agent: newUserAgent });
      toastStore.success(`User-Agent updated for ${originalUrls.length} channels.`);
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Bulk User-Agent assignment failed: ${err.message}`);
    }
  }

  /**
   * Clears individual rewrite rules in bulk for selected channels.
   */
  public async bulkResetRewrites(): Promise<void> {
    const originalUrls = this.allChannels
      .filter((ch) => this.selectedRows.has(ch.id))
      .map((ch) => ch.original_url);

    if (originalUrls.length === 0) return;

    try {
      await api.bulkResetRewrites({ original_urls: originalUrls });
      toastStore.info(`Rewrites reset for ${originalUrls.length} channels.`);
      await this.loadChannels();
    } catch (err: any) {
      toastStore.error(`Bulk reset failed: ${err.message}`);
    }
  }

  /**
   * Opens bulk group edit modal configured with existing available group suggestions.
   */
  public openBulkGroupModal(): void {
    this.bulkModal = {
      open: true,
      actionType: 'group',
      title: 'Bulk Edit Group',
      label: 'Group Name',
      suggestions: this.availableGroups.map((g) => g.value).filter(Boolean)
    };
  }

  /**
   * Opens bulk User-Agent edit modal configured with existing unique UA suggestions.
   */
  public openBulkUserAgentModal(): void {
    const uniqueUas = Array.from(
      new Set(this.allChannels.map((c) => c.user_agent).filter((ua): ua is string => Boolean(ua)))
    );
    this.bulkModal = {
      open: true,
      actionType: 'user_agent',
      title: 'Bulk Edit User-Agent',
      label: 'User-Agent',
      suggestions: uniqueUas
    };
  }

  /**
   * Applies the staged bulk modal action with the specified value.
   *
   * @param val Value to assign to selected channels.
   */
  public async applyBulkInput(val: string): Promise<void> {
    if (this.bulkModal.actionType === 'group') {
      await this.bulkSetGroup(val);
    } else if (this.bulkModal.actionType === 'user_agent') {
      await this.bulkSetUserAgent(val);
    }
  }

  /**
   * Updates channel link and CORS status reactively when player status events are received.
   *
   * @param event Stream status update event from video player.
   */
  public handleStreamStatusUpdate(event: StreamStatusUpdateEvent): void {
    const res = updateChannelStreamStatus(this.allChannels, event);
    if (res.updated) {
      this.allChannels = res.updatedList;
      this.applyFilters();
      if (event.link_status === 'offline' && event.errorCode) {
        toastStore.warning(`Stream KO (${res.targetName || 'Channel'}): ${event.errorCode}`);
      }
    }
  }
}
