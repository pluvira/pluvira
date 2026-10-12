<script lang="ts">
  import { onMount } from 'svelte';
  import { LiveController } from './LiveController.svelte';
  import VideoPlayer from '../player/VideoPlayer.svelte';
  import ProgramInfo from './ProgramInfo.svelte';
  import TimelineHeader from './TimelineHeader.svelte';
  import ProgramBlock from './ProgramBlock.svelte';
  import ProgramDetailsModal from './ProgramDetailsModal.svelte';
  import ChannelModalsHost from '../channels/modals/ChannelModalsHost.svelte';
  import DebouncedInput from '../ui/DebouncedInput.svelte';
  import Button from '../ui/Button.svelte';
  import { videoPlayerStore } from '$lib/components/player/VideoPlayerStore';
  import {
    getTimelineBounds,
    calculateBlockPosition,
    TIMELINE_ZOOM_LEVELS,
    isProgrammeCurrentlyLive,
    type RenderedBlock
  } from './utils';
  import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, Play, Tv, Calendar, Info, Star } from '@lucide/svelte';
  import SegmentedControl, { type SegmentOption } from '../ui/SegmentedControl.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import type { TvMobileTab } from './utils';

  const controller = new LiveController();

  let isSearchActive = $derived(Boolean(controller.channelQuery?.trim()));

  const mobileTabOptions: SegmentOption<TvMobileTab>[] = [
    { value: 'epg', label: 'TV Guide', icon: Calendar },
    { value: 'details', label: 'Details', icon: Info }
  ];

  let activeBlock = $state<RenderedBlock | null>(null);
  let selectedProgramChannel = $state<ChannelItem | null>(null);
  let isProgramBlockLive = $state(false);
  let showDetailsModal = $state(false);
  let timelineContainerEl = $state<HTMLDivElement | null>(null);

  const zoomValues = TIMELINE_ZOOM_LEVELS.map((z) => z.value).reverse();

  $effect(() => {
    const offset = controller.scrollOffsetPx;
    if (timelineContainerEl) {
      timelineContainerEl.scrollLeft = offset;
    }
  });

  function handleProgramClick(block: RenderedBlock, ch: ChannelItem) {
    activeBlock = block;
    selectedProgramChannel = ch;
    isProgramBlockLive = isProgrammeCurrentlyLive(block.program, new Date());
    showDetailsModal = true;
  }

  function handlePlayFromModal() {
    if (selectedProgramChannel) {
      controller.selectChannel(selectedProgramChannel);
    }
  }

  onMount(() => {
    controller.loadTvData().then(() => {
      controller.scrollTimeline('now');
    });

    const unsubscribePlayer = videoPlayerStore.onStatusUpdate((evt) => {
      controller.handleStreamStatusUpdate(evt);
    });

    return () => {
      unsubscribePlayer();
    };
  });
</script>

<div class="flex flex-col gap-4 w-full select-none">
  <!-- Top Section: Sticky 16:9 Player on Mobile + Split View on Desktop -->
  <div class="flex flex-col md:flex-row gap-4 w-full md:items-stretch">
    <div class="w-full md:w-7/12 lg:w-7/12 xl:w-8/12 flex flex-col sticky top-0 z-30 md:static bg-background shrink-0">
      <VideoPlayer channel={controller.activeChannel} embedded={true} />

      <!-- Mobile Segmented Navigation Bar -->
      <div class="md:hidden w-full pt-2">
        <SegmentedControl
          options={mobileTabOptions}
          bind:value={controller.activeMobileTab}
          onchange={(t) => controller.setMobileTab(t)}
        />
      </div>
    </div>

    <!-- Desktop Programme Info Sidebar -->
    <div class="hidden md:flex md:w-5/12 lg:w-5/12 xl:w-4/12 flex-col relative min-h-0 flex-1">
      <div class="absolute inset-0 flex flex-col min-h-0 overflow-hidden">
        <ProgramInfo
        class="h-full max-h-full"
        channel={controller.activeChannel}
        programmes={controller.getProgrammesForChannel(controller.activeChannel)}
        onshowdetails={(ch) => controller.openDetailsModal(ch)}
        oneditmetadata={(ch) => controller.openEditModal(ch)}
        oneditmapping={(ch) => controller.openMappingModal(ch)}
        ontoggleinclusion={(ch) => controller.toggleChannelInclusion(ch)}
        onopenfailover={(ch) => controller.openMergeSheet(ch)}
        onselectprogram={(b) => handleProgramClick(b, controller.activeChannel!)}
      />
      </div>
    </div>
  </div>

  <!-- Mobile Tab: Dedicated Programme Details -->
  {#if controller.activeMobileTab === 'details'}
    <div class="md:hidden flex flex-col w-full h-[380px] animate-fade-in">
      <ProgramInfo
        class="h-full"
        channel={controller.activeChannel}
        programmes={controller.getProgrammesForChannel(controller.activeChannel)}
        onshowdetails={(ch) => controller.openDetailsModal(ch)}
        oneditmetadata={(ch) => controller.openEditModal(ch)}
        oneditmapping={(ch) => controller.openMappingModal(ch)}
        ontoggleinclusion={(ch) => controller.toggleChannelInclusion(ch)}
        onopenfailover={(ch) => controller.openMergeSheet(ch)}
        onselectprogram={(b) => handleProgramClick(b, controller.activeChannel!)}
      />
    </div>
  {/if}

  <!-- EPG Timeline Controls & Grid (Desktop always visible, Mobile visible when activeMobileTab === 'epg') -->
  <div class="w-full flex-col gap-4 {controller.activeMobileTab === 'epg' ? 'flex' : 'hidden md:flex'}">

  <!-- Middle Section: Minimal Toolbar -->
  <div class="surface-card p-2.5 flex flex-wrap items-center justify-between gap-3 w-full sticky top-0 z-30 bg-background/95 backdrop-blur-xs">
    <!-- Left: Channel Scope Toggle & Search -->
    <div class="flex items-center gap-2 flex-wrap min-w-0">
      <Button
        variant={controller.channelScope === 'curated' ? 'primary' : 'outline'}
        size="sm"
        onclick={() => controller.toggleChannelScope()}
        class="!p-2 shrink-0 touch-btn"
        title={controller.channelScope === 'curated' ? 'Scope: Curated List (Click to show all channels)' : 'Scope: All Channels (Click to show curated list)'}
        aria-label={controller.channelScope === 'curated' ? 'Show all channels' : 'Show curated list'}
      >
        <Star class="w-4 h-4 {controller.channelScope === 'curated' ? 'fill-current' : 'text-muted-foreground'}" />
      </Button>

      <div class="w-40 sm:w-56" title="Search channels by name">
        <DebouncedInput
          placeholder="Search channels..."
          bind:value={controller.channelQuery}
          delayMs={250}
          onchange={() => controller.applyFilters()}
        />
      </div>
    </div>

    <!-- Center/Left: Timeline Controls [ <- NOW -> ] -->
    <div class="flex items-center gap-1 bg-card border border-border/40 p-0.5 rounded-md shadow-xs shrink-0">
      <Button
        variant="ghost"
        size="sm"
        onclick={() => controller.scrollTimeline('prev')}
        class="!p-1.5 text-xs text-muted-foreground hover:text-foreground"
        title="PREV"
        aria-label="PREV"
      >
        <ChevronLeft class="w-4 h-4" />
      </Button>
      <Button
        variant="primary"
        size="sm"
        onclick={() => controller.scrollTimeline('now')}
        class="!py-1 !px-3 text-xs font-bold"
        title="NOW"
        aria-label="NOW"
      >
        NOW
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onclick={() => controller.scrollTimeline('next')}
        class="!p-1.5 text-xs text-muted-foreground hover:text-foreground"
        title="NEXT"
        aria-label="NEXT"
      >
        <ChevronRight class="w-4 h-4" />
      </Button>
    </div>

    <!-- Right: Zoom Slider Only -->
    <div class="flex items-center shrink-0">
      <input
        id="tv-timeline-zoom-select"
        type="range"
        min="0"
        max="5"
        step="1"
        value={zoomValues.indexOf(controller.hoursVisible)}
        oninput={(e) => controller.setZoom(zoomValues[parseInt((e.target as HTMLInputElement).value, 10)] || 6)}
        class="select-compact w-24 sm:w-28 accent-primary cursor-pointer"
        title={`Zoom: ${controller.hoursVisible} Hours`}
        aria-label="Timeline zoom"
      />
    </div>
  </div>

  <!-- Bottom Section: Synchronized Pluto TV Live Grid -->
  {#if controller.loading && controller.allChannels.length === 0}
    <div class="state-empty">
      <span class="spinner mr-3"></span>
      <span class="text-sm font-bold">Loading Live TV Guide...</span>
    </div>
  {:else if controller.filteredChannels.length === 0}
    <div class="state-empty">
      <Tv class="w-8 h-8 mb-2 text-muted-foreground" />
      <span class="text-sm font-bold">
        {#if controller.channelScope === 'curated'}
          No bookmarked channels in curated list. Switch to all channels or bookmark channels from catalog.
        {:else}
          No channels found matching the selected filters.
        {/if}
      </span>
    </div>
  {:else}
    <div
      bind:this={timelineContainerEl}
      bind:clientWidth={controller.containerWidth}
      class="surface-card w-full max-h-[calc(100dvh-300px)] md:max-h-[400px] lg:max-h-[440px] overflow-auto relative !p-0 border border-border/40 shadow-card select-none"
    >
      <div class="flex flex-col relative w-max min-w-full">
        <!-- Sticky Header Row (pinned top) -->
        <div class="flex items-center sticky top-0 z-30 border-b border-border/30 bg-background">
          <!-- Top-Left Corner Pin (pinned top & left) -->
          <div class="sticky left-0 z-40 w-24 sm:w-28 md:w-36 lg:w-44 max-w-[25%] shrink-0 h-9 bg-card border-r border-border/30 flex items-center justify-between px-1.5 sm:px-2.5">
            <span class="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Channels</span>
            {#if controller.totalPages > 1}
              <div class="flex items-center gap-1">
                <span class="text-[10px] text-muted-foreground font-mono">{controller.page}/{controller.totalPages}</span>
                <button
                  type="button"
                  disabled={controller.page <= 1}
                  onclick={() => controller.prevPage()}
                  class="p-0.5 text-muted-foreground hover:text-foreground disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                  title="Previous Page"
                  aria-label="Previous Page"
                >
                  <ChevronUp class="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  disabled={controller.page >= controller.totalPages}
                  onclick={() => controller.nextPage()}
                  class="p-0.5 text-muted-foreground hover:text-foreground disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                  title="Next Page"
                  aria-label="Next Page"
                >
                  <ChevronDown class="w-3.5 h-3.5" />
                </button>
              </div>
            {/if}
          </div>
          <!-- Timeline Header Ruler -->
          <div class="relative h-9" style="width: {controller.timelineWidth}px;">
            <TimelineHeader
              bind:timelineWidth={controller.timelineWidth}
              rowCount={controller.paginatedChannels.length}
              selectedDateStr={controller.selectedDateStr}
            />
          </div>
        </div>

        <!-- Channel & EPG Synchronized Rows -->
        {#each controller.paginatedChannels as ch, chIdx ((ch.id || ch.name) + '_' + chIdx)}
          {@const [windowStart, windowEnd] = getTimelineBounds(controller.selectedDateStr, 3)}
          {@const isActive = controller.activeChannel?.id === ch.id}
          {@const channelProgs = controller.getProgrammesForChannel(ch)}
          <div class="flex items-stretch h-16 border-b border-border/20 relative {isActive ? 'bg-primary/5' : 'hover:bg-muted/30'}">
            <!-- Left Channel Button (pinned horizontally via sticky left-0, 2-row layout) -->
            <div
              role="button"
              tabindex="0"
              onclick={() => controller.selectChannel(ch)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') controller.selectChannel(ch); }}
              class="sticky left-0 z-20 w-24 sm:w-28 md:w-36 lg:w-44 max-w-[25%] shrink-0 h-full p-1 sm:p-1.5 border-r border-border/30 bg-background text-left transition-colors flex flex-col justify-center gap-0.5 sm:gap-1 cursor-pointer {isActive ? 'bg-primary/20 border-l-4 border-l-primary text-foreground' : 'hover:bg-card text-foreground/80'}"
              title={`Play ${ch.name}`}
            >
              <div class="flex items-center justify-between gap-1 w-full overflow-hidden">
                <div class="flex items-center gap-1.5 min-w-0">
                  {#if ch.logo}
                    <img src={ch.logo} alt={ch.name} class="h-6 w-9 object-contain bg-black rounded p-0.5 border border-border/30 shrink-0" />
                  {/if}
                </div>
                {#if isActive}
                  <Play class="w-3.5 h-3.5 text-primary fill-primary shrink-0" />
                {/if}
              </div>
              <span class="text-xs font-bold text-foreground truncate w-full block" title={ch.name}>{ch.name}</span>
            </div>

            <!-- Right EPG Programme Blocks Track -->
            <div class="relative h-full overflow-hidden" style="width: {controller.timelineWidth}px;">
              {#if channelProgs.length > 0}
                {#each channelProgs as prog, idx (prog.s + '_' + (prog.e || '') + '_' + prog.t + '_' + idx)}
                  {@const block = calculateBlockPosition(prog, windowStart, windowEnd, controller.timelineWidth)}
                  {#if block}
                    {@const blockWithScore = { ...block, matchScore: 0 }}
                    <ProgramBlock block={blockWithScore} {isSearchActive} onclick={(b) => handleProgramClick(b, ch)} />
                  {/if}
                {/each}
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
  </div>

  <ProgramDetailsModal
    renderedBlock={activeBlock}
    channel={selectedProgramChannel}
    isLive={isProgramBlockLive}
    onplay={handlePlayFromModal}
    bind:open={showDetailsModal}
  />

  <ChannelModalsHost
    channel={controller.selectedModalChannel}
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
    onplaystream={(ch) => controller.selectChannel(ch)}
    onopenfailover={(ch) => controller.openMergeSheet(ch)}
    onsaved={() => controller.loadTvData()}
  />
</div>
