import { api } from '$lib/api/client';
import type { ChannelItem, EpgProgramItem, SearchMethodsConfig } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import { countActiveFilters } from '$lib/utils/objectUtils';
import {
  getPreference,
  setPreference,
  getSearchViewMode,
  setSearchViewMode,
  getSearchDensityMode,
  setSearchDensityMode,
  getRecentSearches,
  addRecentSearch,
  removeRecentSearch,
  clearRecentSearches
} from '$lib/utils/preferences';
import {
  extractUniqueGroups,
  extractUniqueSources,
  updateChannelStreamStatus
} from '../channels/utils/ChannelsUtils';
import { extractUniqueEpgIds, getEpgDateRange } from '../live/utils/LiveUtils';
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
import {
  filterAndScoreProgrammes,
  groupResultsByChannel,
  type SearchDateScope,
  type SearchFilterOptions,
  type SearchResultItem,
  type ChannelGroupedSearchResult
} from './utils/SearchUtils';

export class SearchController {
  public loading = $state(false);
  public query = $state(getPreference<string>('search_query', ''));
  public liveOnly = $state(getPreference<boolean>('search_live_only', false));
  public primeTimeOnly = $state(getPreference<boolean>('search_prime_time', false));
  public dateScope = $state<SearchDateScope>(getPreference<SearchDateScope>('search_date_scope', 'today'));
  public selectedGroups = $state<string[]>(getPreference<string[]>('search_groups', []));
  public selectedSources = $state<string[]>(getPreference<string[]>('search_sources', []));
  public onlineOnly = $state(getPreference<boolean>('search_online_only', false));
  public curatedOnly = $state(getPreference<boolean>('search_curated_only', true));
  public showAdvancedModal = $state(false);
  public minScore = $state(getPreference<number>('search_min_score', 0));

  public viewMode = $state<'timeline' | 'grouped'>(getSearchViewMode());
  public densityMode = $state<'cards' | 'compact'>(getSearchDensityMode());
  public recentSearches = $state<string[]>(getRecentSearches());

  public page = $state(1);
  public pageSize = $state(24);

  public allChannels = $state<ChannelItem[]>([]);
  public epgData = $state<Record<string, EpgProgramItem[]>>({});
  public availableGroups = $state<Array<{ label: string; value: string }>>([]);
  public availableSources = $state<Array<{ label: string; value: string }>>([]);
  public language = 'it';
  public customStopwords: string[] = [];
  public searchMethods = $state<SearchMethodsConfig>({
    method_a: true,
    method_b: true,
    method_c: true,
    method_d: true
  });

  public activeFilterCount = $derived.by(() => {
    return countActiveFilters({
      liveOnly: this.liveOnly,
      primeTimeOnly: this.primeTimeOnly,
      dateScope: this.dateScope,
      selectedGroups: this.selectedGroups,
      selectedSources: this.selectedSources,
      onlineOnly: this.onlineOnly,
      minScore: this.minScore,
      curatedOnly: this.curatedOnly
    }, {
      dateScope: 'today',
      curatedOnly: true
    });
  });
  public results = $derived.by<SearchResultItem[]>(() => {
    const filters: SearchFilterOptions = {
      query: this.query,
      liveOnly: this.liveOnly,
      primeTimeOnly: this.primeTimeOnly,
      dateScope: this.dateScope,
      selectedGroups: this.selectedGroups,
      selectedSources: this.selectedSources,
      onlineOnly: this.onlineOnly,
      minScore: this.minScore,
      curatedOnly: this.curatedOnly
    };
    return filterAndScoreProgrammes(
      this.allChannels,
      this.epgData,
      filters,
      {
        language: this.language,
        customStopwords: this.customStopwords,
        searchMethods: this.searchMethods
      }
    );
  });

  public groupedResults = $derived.by<ChannelGroupedSearchResult[]>(() => {
    return groupResultsByChannel(this.results);
  });

  public totalPages = $derived.by<number>(() => {
    const count = this.viewMode === 'timeline' ? this.results.length : this.groupedResults.length;
    return Math.max(1, Math.ceil(count / this.pageSize));
  });

  public paginatedResults = $derived.by<SearchResultItem[]>(() => {
    const start = (this.page - 1) * this.pageSize;
    return this.results.slice(start, start + this.pageSize);
  });

  public paginatedGroupedResults = $derived.by<ChannelGroupedSearchResult[]>(() => {
    const start = (this.page - 1) * this.pageSize;
    return this.groupedResults.slice(start, start + this.pageSize);
  });

  /**
   * Loads playlist channels and EPG guide data from API.
   */
  public async loadSearchData(): Promise<void> {
    const t0 = performance.now();
    console.log('[SearchController] loadSearchData start...');
    this.loading = true;
    try {
      const [response, configRes]: [any, any] = await Promise.all([
        api.getChannels({ limit: 1000 }),
        api.getConfig().catch(() => null)
      ]);
      const items: ChannelItem[] = Array.isArray(response) ? response : (response.items || response.channels || []);

      if (configRes?.settings) {
        this.language = configRes.settings.language || 'it';
        this.customStopwords = configRes.settings.custom_stopwords || [];
        if (configRes.settings.search_methods) {
          this.searchMethods = configRes.settings.search_methods;
        }
      }

      this.allChannels = items;
      this.availableGroups = extractUniqueGroups(this.allChannels).filter((g) => g.value !== '');
      this.availableSources = extractUniqueSources(this.allChannels);

      const uniqueIds = extractUniqueEpgIds(this.allChannels);
      console.log(`[SearchController] Loaded ${items.length} channels, extracting ${uniqueIds.length} EPG IDs.`);
      if (uniqueIds.length > 0) {
        const { date_from, date_to } = getEpgDateRange(new Date(), 3, 1);
        this.epgData = await api.getEpgProgrammes({
          ids: uniqueIds,
          date_from,
          date_to
        });
        const count = Object.values(this.epgData || {}).reduce((acc, p) => acc + (p?.length || 0), 0);
        console.log(`[SearchController] EPG query in ${(performance.now() - t0).toFixed(1)}ms: ${Object.keys(this.epgData || {}).length} channels, ${count} progs.`);
      } else {
        this.epgData = {};
      }
    } catch (err: any) {
      console.error('[SearchController] loadSearchData failed:', err);
      toastStore.error(`Failed to load search data: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Toggles live programmes only filter.
   */
  public toggleLive(): void {
    this.liveOnly = !this.liveOnly;
    this.page = 1;
    setPreference('search_live_only', this.liveOnly);
  }

  /**
   * Toggles prime time programmes filter.
   */
  public togglePrimeTime(): void {
    this.primeTimeOnly = !this.primeTimeOnly;
    this.page = 1;
    setPreference('search_prime_time', this.primeTimeOnly);
  }

  /**
   * Toggles date scope between 'today' and 'all'.
   */
  public toggleDateScope(): void {
    if (this.dateScope === 'today') {
      this.setDateScope('three_days');
    } else if (this.dateScope === 'three_days') {
      this.setDateScope('all');
    } else {
      this.setDateScope('today');
    }
  }

  /**
   * Sets explicit date scope filter.
   *
   * @param scope Target date scope.
   */
  public setDateScope(scope: SearchDateScope): void {
    this.dateScope = scope;
    this.page = 1;
    setPreference('search_date_scope', scope);
  }

  /**
   * Toggles online-only stream status filter.
   */
  public toggleOnlineOnly(): void {
    this.onlineOnly = !this.onlineOnly;
    setPreference('search_online_only', this.onlineOnly);
  }

  /**
   * Toggles curated channels only filter (My List).
   */
  public toggleCuratedOnly(): void {
    this.curatedOnly = !this.curatedOnly;
    this.page = 1;
    setPreference('search_curated_only', this.curatedOnly);
  }

  /**
   * Sets debounced search query.
   *
   * @param val Query text string.
   */
  public setQuery(val: string): void {
    this.query = val;
    this.page = 1;
    setPreference('search_query', val);
    if (val.trim().length >= 3) {
      addRecentSearch(val.trim());
      this.recentSearches = getRecentSearches();
    }
  }

  /**
   * Toggles view layout mode between timeline and channel-grouped.
   */
  public toggleViewMode(): void {
    this.viewMode = this.viewMode === 'timeline' ? 'grouped' : 'timeline';
    this.page = 1;
    setSearchViewMode(this.viewMode);
  }

  /**
   * Sets layout view mode explicitly.
   *
   * @param mode Target layout mode.
   */
  public setViewMode(mode: 'timeline' | 'grouped'): void {
    this.viewMode = mode;
    this.page = 1;
    setSearchViewMode(mode);
  }

  /**
   * Toggles cards density between detailed cards and compact rows.
   */
  public toggleDensityMode(): void {
    this.densityMode = this.densityMode === 'cards' ? 'compact' : 'cards';
    setSearchDensityMode(this.densityMode);
  }

  /**
   * Sets cards density mode explicitly.
   *
   * @param density Target density mode.
   */
  public setDensityMode(density: 'cards' | 'compact'): void {
    this.densityMode = density;
    setSearchDensityMode(density);
  }

  /**
   * Selects a recent search query.
   *
   * @param query Search query text.
   */
  public selectRecentSearch(query: string): void {
    this.setQuery(query);
  }

  /**
   * Removes a search query from recent history.
   *
   * @param query Query to remove.
   */
  public removeRecent(query: string): void {
    removeRecentSearch(query);
    this.recentSearches = getRecentSearches();
  }

  /**
   * Clears all recent searches history.
   */
  public clearRecent(): void {
    clearRecentSearches();
    this.recentSearches = [];
  }

  public setPage(p: number): void {
    if (p >= 1 && p <= this.totalPages) {
      this.page = p;
    }
  }

  public nextPage(): void {
    if (this.page < this.totalPages) {
      this.page++;
    }
  }

  public prevPage(): void {
    if (this.page > 1) {
      this.page--;
    }
  }

  /**
   * Toggles channel bookmark status into the default personal playlist.
   *
   * @param channel Channel item model.
   * @returns Updated bookmark status boolean or null.
   */
  public async toggleBookmark(channel: ChannelItem): Promise<boolean | null> {
    try {
      const res = await api.bookmarkChannel({
        playlist_id: 'default',
        channel: {
          name: channel.name,
          url: channel.original_url || channel.url,
          source: channel.source,
          group: channel.group,
          logo: channel.logo,
          epg_id: channel.epg_id
        }
      });

      const isBookmarked = Boolean(res.bookmarked);
      channel.is_bookmarked = isBookmarked;

      if (isBookmarked) {
        toastStore.success(`Added "${channel.name}" to My Playlist`);
      } else {
        toastStore.info(`Removed "${channel.name}" from My Playlist`);
      }
      return isBookmarked;
    } catch (err: any) {
      toastStore.error(`Failed to update bookmark: ${err.message}`);
      return null;
    }
  }

  /**
   * Toggles selection of category group.
   *
   * @param group Target group title.
   */
  public switchGroup(group: string): void {
    if (!group) {
      this.selectedGroups = [];
    } else if (this.selectedGroups.includes(group)) {
      this.selectedGroups = this.selectedGroups.filter((g) => g !== group);
    } else {
      this.selectedGroups = [...this.selectedGroups, group];
    }
    setPreference('search_groups', this.selectedGroups);
  }

  /**
   * Sets minimum relevance score threshold.
   *
   * @param score Score integer or float.
   */
  public setMinScore(score: number): void {
    this.minScore = score;
    setPreference('search_min_score', score);
  }

  public switchSource(source: string): void {
    if (!source) {
      this.selectedSources = [];
    } else if (this.selectedSources.includes(source)) {
      this.selectedSources = this.selectedSources.filter((s) => s !== source);
    } else {
      this.selectedSources = [...this.selectedSources, source];
    }
    setPreference('search_sources', this.selectedSources);
  }

  /**
   * Resets all search filters and facets to default state.
   */
  public resetFilters(): void {
    this.query = '';
    this.liveOnly = false;
    this.primeTimeOnly = false;
    this.dateScope = 'today';
    this.selectedGroups = [];
    this.selectedSources = [];
    this.onlineOnly = false;
    this.curatedOnly = true;
    this.minScore = 0;
    this.page = 1;
    setPreference('search_query', '');
    setPreference('search_live_only', false);
    setPreference('search_prime_time', false);
    setPreference('search_date_scope', 'today');
    setPreference('search_groups', []);
    setPreference('search_sources', []);
    setPreference('search_online_only', false);
    setPreference('search_curated_only', true);
    setPreference('search_min_score', 0);
  }

  public openAdvancedModal(): void {
    this.showAdvancedModal = true;
  }

  public closeAdvancedModal(): void {
    this.showAdvancedModal = false;
  }

  /**
   * Synchronizes stream health updates reported from video playback.
   *
   * @param event Playback status event.
   */
  public handleStreamStatusUpdate(event: StreamStatusUpdateEvent): void {
    const res = updateChannelStreamStatus(this.allChannels, event);
    if (res.updated) {
      this.allChannels = res.updatedList;
    }
  }
}
