<script lang="ts">
  import { onMount } from 'svelte';
  import { ChannelsController } from './ChannelsController.svelte';
  import { videoPlayerStore } from '$lib/components/player/VideoPlayerStore';
  import FilterBar from './bars/FilterBar.svelte';
  import BulkActionsBar from './bars/BulkActionsBar.svelte';
  import ChannelsTable from './tables/ChannelsTable.svelte';
  import ChannelModalsHost from './modals/ChannelModalsHost.svelte';
  import VisibleColumnsModal from './modals/VisibleColumnsModal.svelte';
  import BulkInputModal from './modals/BulkInputModal.svelte';
  import BulkTestModal from './modals/BulkTestModal.svelte';
  import VideoPlayer from '../player/VideoPlayer.svelte';
  import Button from '../ui/Button.svelte';
  import SegmentedControl, { type SegmentOption } from '../ui/SegmentedControl.svelte';
  import ChannelFilterSheet from './modals/ChannelFilterSheet.svelte';
  import MergeView from './merge/MergeView.svelte';
  import SourcesTable from './tables/SourcesTable.svelte';
  import EpgSourcesTable from './tables/EpgSourcesTable.svelte';
  import { Eye, Filter, Tv, GitCompare, Radio, Trash2, X, RotateCcw, Star, Folder, Calendar, Sparkles } from '@lucide/svelte';
  import AutoAssignEpgModal from './modals/AutoAssignEpgModal.svelte';
  import Dialog from '../ui/Dialog.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import {
    formatBslChannelsQuota,
    isChannelsQuotaExceeded,
    formatBslCuratedQuota,
    isCuratedQuotaExceeded
  } from '$lib/utils/bslUtils';
  import ProTrialModal from './modals/ProTrialModal.svelte';
  import Badge from '../ui/Badge.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import type { ChannelsHubTab } from './utils/ChannelsUtils';

  const controller = new ChannelsController();
  let isPro = $derived($licenseStore.isPro);

  function handlePurgeQuarantined() {
    controller.showPurgeModal = true;
  }
  let isChannelCapReached = $derived(isChannelsQuotaExceeded(controller.allChannels.length, isPro));
  let curatedCount = $derived(controller.allChannels.filter((c) => c.is_bookmarked).length);
  let isCuratedCapReached = $derived(isCuratedQuotaExceeded(curatedCount, isPro));

  const hubTabOptions: SegmentOption<ChannelsHubTab>[] = [
    { value: 'channels', label: 'Channels', icon: Tv },
    { value: 'merge', label: 'Merge', icon: GitCompare },
    { value: 'sources', label: 'Health', icon: Radio }
  ];

  $effect(() => {
    if (controller.activeTab === 'sources') {
      controller.loadSourcesAnalytics();
    }
  });

  function refreshData() { controller.loadChannels(); }

  function handlePlayStream(ch: ChannelItem) { videoPlayerStore.playChannel(ch); }
  function handleApplyBulkInput(val: string) { controller.applyBulkInput(val); }

  let selectedChannelsForTest = $derived(controller.allChannels.filter((ch) => controller.selectedRows.has(ch.id)));
  let isAllFilteredSelected = $derived(controller.filteredChannels.length > 0 && controller.filteredChannels.every((ch) => controller.selectedRows.has(ch.id)));
  let isPartiallySelected = $derived(controller.selectedRows.size > 0 && !isAllFilteredSelected);

  function handleToggleSelectAll(selectAll: boolean) {
    controller.filteredChannels.forEach((ch) => selectAll ? controller.selectedRows.add(ch.id) :
      controller.selectedRows.delete(ch.id));
    controller.selectedRows = new Set(controller.selectedRows);
  }

  import { playlistStore } from '$lib/stores/playlistStore';

  onMount(() => {
    refreshData();
    playlistStore.loadPlaylists();
    const unsub = videoPlayerStore.onStatusUpdate((evt) => controller.handleStreamStatusUpdate(evt));
    return () => unsub();
  });
</script>

<div class="flex flex-col gap-4 w-full">
  <!-- Sticky Top Hub Header (Sub-Tabs + Tab-specific sticky controls) -->
  <div class="sticky top-0 z-30 bg-background/95 backdrop-blur-xs pb-1 flex flex-col gap-2">
    <!-- Top Hub Sub-Tabs Navigation Bar -->
    <div class="w-full flex items-center justify-between gap-2">
      <div class="flex-1">
        <SegmentedControl
          options={hubTabOptions}
          bind:value={controller.activeTab}
          onchange={(t) => controller.setActiveTab(t)}
        />
      </div>
      {#if !isPro}
        <div class="flex items-center gap-1.5 shrink-0 hidden sm:inline-flex">
          <button
            type="button"
            onclick={() => isCuratedCapReached && controller.openTrialModal()}
            class="cursor-pointer"
          >
            <Badge variant={isCuratedCapReached ? 'warning' : 'muted'} class="text-[10px] flex items-center gap-1 font-mono" title={formatBslCuratedQuota(curatedCount, isPro)}>
              <Star class="w-3 h-3 text-warning" />
              <span>{curatedCount}/25</span>
            </Badge>
          </button>
          <Badge variant={isChannelCapReached ? 'warning' : 'muted'} class="text-[10px] flex items-center gap-1 font-mono" title={formatBslChannelsQuota(controller.allChannels.length, isPro)}>
            <Folder class="w-3 h-3 text-muted-foreground" />
            <span>{controller.allChannels.length}/2500</span>
          </Badge>
        </div>
      {/if}
    </div>

    {#if controller.activeTab === 'channels'}
    <!-- Unified Compact Filter Bar & Active Filter Ribbon -->
    <div class="flex flex-col gap-2 w-full surface-card p-2">
      <div class="flex items-center justify-between gap-2 w-full">
        <div class="flex-1 min-w-0">
          <FilterBar
            bind:searchQuery={controller.filters.searchQuery}
            delayMs={300}
            onsearch={() => controller.applyFilters()}
            class="!p-0 !border-0 !bg-transparent !shadow-none"
          />
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onclick={() => controller.openAutoAssignModal()}
            class="h-[36px] flex items-center gap-1.5 font-bold text-xs touch-btn"
            title="Auto-Assign EPG to channels"
            aria-label="Auto-Assign EPG to channels"
          >
            <Calendar class="w-3.5 h-3.5 text-primary" />
            <Sparkles class="w-3.5 h-3.5 text-primary" />
            <span class="hidden sm:inline">Auto-Assign EPG</span>
            {#if controller.unmappedChannelsCount > 0}
              <Badge variant="muted" class="text-[10px] ml-0.5">
                {controller.unmappedChannelsCount}
              </Badge>
            {/if}
          </Button>

          {#if controller.quarantinedCount > 0}
            <Button
              variant="danger"
              size="sm"
              onclick={handlePurgeQuarantined}
              class="h-[36px] text-xs flex items-center gap-1.5 px-2.5 font-bold touch-btn"
              title="Purge all offline quarantined streams"
              aria-label="Purge all offline quarantined streams"
            >
              <Trash2 class="w-3.5 h-3.5" />
              <span class="hidden sm:inline">Purge KO</span>
              <span>({controller.quarantinedCount})</span>
            </Button>
          {/if}

          <Button
            variant="outline"
            size="sm"
            onclick={() => (controller.showColumnsModal = true)}
            class="h-[36px] flex items-center gap-1.5 font-bold text-xs touch-btn"
            title="Customize visible columns"
            aria-label="Customize visible columns"
          >
            <Eye class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">Columns</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onclick={() => (controller.showFilterSheet = true)}
            class="h-[36px] flex items-center gap-1.5 font-bold text-xs touch-btn"
            title="Filter channels"
            aria-label="Filter channels"
          >
            <Filter class="w-3.5 h-3.5" />
            <span>Filters {controller.activeFilterCount > 0 ? `(${controller.activeFilterCount})` : ''}</span>
          </Button>
        </div>
      </div>

      <!-- Active Filter Chips Ribbon -->
      {#if controller.activeFilterCount > 0}
        <div class="flex items-center gap-1.5 flex-wrap pt-1 border-t border-border/20 text-xs">
          {#if controller.filters.searchQuery?.trim()}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/30 text-primary text-[11px] font-medium">
              <span>Query: "{controller.filters.searchQuery}"</span>
              <button type="button" onclick={() => controller.removeFilter('searchQuery')} class="hover:text-foreground cursor-pointer" title="Remove search query" aria-label="Remove search query">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          {#each controller.filters.selectedGroups || [] as grp}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>Group: {grp || '(Empty)'}</span>
              <button type="button" onclick={() => controller.removeGroupFilter(grp)} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove group filter" aria-label="Remove group filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/each}

          {#each controller.filters.selectedSources || [] as src}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>Source: {src}</span>
              <button type="button" onclick={() => controller.removeSourceFilter(src)} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove source filter" aria-label="Remove source filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/each}

          {#if controller.filters.linkStatus && controller.filters.linkStatus !== 'all'}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>Link: {controller.filters.linkStatus.toUpperCase()}</span>
              <button type="button" onclick={() => controller.removeFilter('linkStatus')} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove link status filter" aria-label="Remove link status filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          {#if controller.filters.inclusionStatus && controller.filters.inclusionStatus !== 'all'}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>Inclusion: {controller.filters.inclusionStatus === 'included' ? 'Included Only' : 'Excluded Only'}</span>
              <button type="button" onclick={() => controller.removeFilter('inclusionStatus')} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove inclusion filter" aria-label="Remove inclusion filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          {#if controller.filters.epgStatus && controller.filters.epgStatus !== 'all'}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>EPG: {controller.filters.epgStatus === 'mapped' ? 'Mapped Only' : 'Unmapped Only'}</span>
              <button type="button" onclick={() => controller.removeFilter('epgStatus')} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove EPG filter" aria-label="Remove EPG filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          {#if controller.filters.corsStatus && controller.filters.corsStatus !== 'all'}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>CORS: {controller.filters.corsStatus === 'cors_ok' ? 'CORS OK' : 'Requires Proxy'}</span>
              <button type="button" onclick={() => controller.removeFilter('corsStatus')} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove CORS filter" aria-label="Remove CORS filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          {#if controller.filters.bookmarkStatus && controller.filters.bookmarkStatus !== 'all'}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-card border border-border text-foreground text-[11px]">
              <span>Favorites: {controller.filters.bookmarkStatus === 'bookmarked' ? 'Favorites (★)' : controller.filters.bookmarkStatus.replace('playlist:', 'List: ')}</span>
              <button type="button" onclick={() => controller.removeFilter('bookmarkStatus')} class="text-muted-foreground hover:text-foreground cursor-pointer" title="Remove favorites filter" aria-label="Remove favorites filter">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/if}

          <button
            type="button"
            onclick={() => controller.resetFilters()}
            class="text-[11px] text-muted-foreground hover:text-destructive flex items-center gap-1 cursor-pointer pl-1"
          >
            <RotateCcw class="w-3 h-3" />
            <span>Clear all</span>
          </button>
        </div>
      {/if}
    </div>
    {/if}
  </div>

  {#if controller.activeTab === 'merge'}
    <div class="w-full animate-fade-in">
      <MergeView />
    </div>
  {:else if controller.activeTab === 'sources'}
    <div class="flex flex-col gap-4 w-full animate-fade-in">
      <div class="flex items-center justify-between gap-2 surface-card p-2">
        <span class="text-xs font-bold text-muted-foreground uppercase tracking-wider pl-1">Sources & Link Health Analytics</span>
        <div class="flex items-center gap-1">
          <Button
            variant={controller.healthViewMode === 'normal' ? 'primary' : 'ghost'}
            size="sm"
            onclick={() => controller.setHealthViewMode('normal')}
            class="!py-1 !px-2.5 text-xs font-bold"
          >
            Normal
          </Button>
          <Button
            variant={controller.healthViewMode === 'full' ? 'primary' : 'ghost'}
            size="sm"
            onclick={() => controller.setHealthViewMode('full')}
            class="!py-1 !px-2.5 text-xs font-bold"
          >
            Full View
          </Button>
        </div>
      </div>
      <SourcesTable
        sourcesStats={controller.sourcesStats}
        isCompact={controller.healthViewMode === 'normal'}
        ontogglesource={(name) => controller.toggleSource(name)}
        onrefreshsource={(names) => controller.refreshSources(names)}
      />
      <EpgSourcesTable
        epgSourcesStats={controller.epgSourcesStats}
        isCompact={controller.healthViewMode === 'normal'}
        ontoggleepgsource={(name) => controller.toggleEpgSource(name)}
        onrefreshepgsource={(names) => controller.refreshEpgSources(names)}
      />
    </div>
  {:else}
  <BulkActionsBar
    selectedCount={controller.selectedRows.size}
    allSelected={isAllFilteredSelected}
    isIndeterminate={isPartiallySelected}
    onToggleSelectAll={handleToggleSelectAll}
    onIncludeAll={() => controller.bulkSetInclusion(true)}
    onExcludeAll={() => controller.bulkSetInclusion(false)}
    onTestAll={() => (controller.showBulkTestModal = true)}
    onEditGroup={() => controller.openBulkGroupModal()}
    onEditUserAgent={() => controller.openBulkUserAgentModal()}
    onResetRewrites={() => controller.bulkResetRewrites()}
    onClearSelection={() => {
      controller.selectedRows.clear();
      controller.selectedRows = new Set();
    }}
  />

  {#if controller.loading && controller.allChannels.length === 0}
    <div class="state-empty">
      <span class="spinner mr-3"></span>
      <span class="text-sm font-bold">Loading processed channels...</span>
    </div>
  {:else}
    <ChannelsTable
      channels={controller.filteredChannels}
      bind:visibleColumns={controller.visibleColumns}
      bind:selectedKeys={controller.selectedRows}
      ontoggleinclusion={(ch) => controller.toggleChannelInclusion(ch)}
      ontogglebookmark={(ch) => controller.toggleBookmark(ch)}
      onshowdetails={(ch) => controller.openDetailsModal(ch)}
      oneditmetadata={(ch) => controller.openEditMetadataModal(ch)}
      oneditlogo={(ch) => controller.openLogoModal(ch)}
      oneditname={(ch) => controller.openFieldModal(ch, 'name', 'Channel Name')}
      oneditgroup={(ch) => controller.openFieldModal(ch, 'group', 'Channel Group')}
      onediturl={(ch) => controller.openFieldModal(ch, 'url', 'Stream URL')}
      onedituseragent={(ch) => controller.openFieldModal(ch, 'user_agent', 'User-Agent')}
      ontestlink={(ch) => controller.openScannerModal(ch)}
      oneditmapping={(ch) => controller.openMappingModal(ch)}
      onplaystream={handlePlayStream}
      onopenfailover={(ch) => controller.openMergeSheet(ch)}
    />
  {/if}

  <ChannelFilterSheet
    bind:open={controller.showFilterSheet}
    filters={controller.filters}
    availableGroups={controller.availableGroups}
    availableSources={controller.availableSources}
    onapply={(draft) => controller.applyDraftFilters(draft)}
  />
  {/if}

  <ChannelModalsHost
    channel={controller.activeChannel}
    bind:showDetailsModal={controller.showDetailsModal}
    bind:showEditModal={controller.showEditModal}
    bind:showLogoModal={controller.showLogoModal}
    bind:showFieldModal={controller.showFieldModal}
    bind:showScannerModal={controller.showScannerModal}
    bind:showMappingModal={controller.showMappingModal}
    bind:showMergeSheet={controller.showMergeSheet}
    selectedMergeChannel={controller.selectedMergeChannel}
    bind:field={controller.field}
    bind:fieldLabel={controller.activeFieldLabel}
    ontoggleinclusion={(ch) => controller.toggleChannelInclusion(ch)}
    onplaystream={handlePlayStream}
    onopenfailover={(ch) => controller.openMergeSheet(ch)}
    onsaved={refreshData}
  />
  <VisibleColumnsModal
    bind:visibleColumns={controller.visibleColumns}
    bind:open={controller.showColumnsModal}
    ontogglecolumn={(key, vis) => controller.toggleColumn(key, vis)}
  />

  <BulkInputModal
    title={controller.bulkModal.title}
    label={controller.bulkModal.label}
    suggestions={controller.bulkModal.suggestions}
    bind:open={controller.bulkModal.open}
    onapply={handleApplyBulkInput}
  />
  <BulkTestModal channels={selectedChannelsForTest} bind:open={controller.showBulkTestModal} onsaved={refreshData} />
  <ProTrialModal bind:open={controller.showTrialModal} onactivate={() => controller.activateProTrial()} onactivated={refreshData} />
  <AutoAssignEpgModal
    bind:open={controller.showAutoAssignModal}
    unmappedCount={controller.unmappedChannelsCount}
    autoAssigning={controller.autoAssigning}
    onassign={(scope, thresh, ow) => controller.runAutoAssignEpg(scope, thresh, ow)}
    onupgradepro={() => controller.openTrialModal()}
  />

  <Dialog bind:open={controller.showPurgeModal} title={`Purge Quarantined Streams (${controller.quarantinedCount})`} class="max-w-2xl">
    {#snippet footer()}
      <div class="flex items-center justify-end gap-2 w-full">
        <Button variant="ghost" size="sm" onclick={() => (controller.showPurgeModal = false)} class="touch-btn">Cancel</Button>
        <Button variant="danger" size="sm" onclick={() => controller.purgeQuarantined()} class="touch-btn">
          Confirm Purge ({controller.quarantinedCount})
        </Button>
      </div>
    {/snippet}

    <div class="flex flex-col gap-3 w-full text-xs">
      <div class="p-3 bg-destructive/10 border border-destructive/30 rounded flex items-start gap-2.5 text-destructive-foreground">
        <Trash2 class="w-4 h-4 text-destructive shrink-0 mt-0.5" />
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-foreground">Purge Offline Quarantined Streams</span>
          <span class="text-muted-foreground">The following {controller.quarantinedCount} offline stream(s) will be purged and reset:</span>
        </div>
      </div>

      <div class="surface-darkest p-2 rounded border border-border/40 max-h-56 overflow-y-auto flex flex-col gap-1">
        {#each controller.quarantinedChannels as ch (ch.id)}
          <div class="flex items-center justify-between text-foreground border-b border-border/20 py-1.5 px-1 gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="w-2 h-2 rounded-full bg-destructive shrink-0"></span>
              <span class="font-bold truncate text-xs">{ch.name}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[10px] font-mono text-muted-foreground">{ch.source}</span>
              <Badge variant="error" class="text-[10px]">KO</Badge>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </Dialog>

  {#each $videoPlayerStore as activeStream (activeStream.id)}
    <VideoPlayer stream={activeStream} />
  {/each}
</div>
