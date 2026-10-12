<script lang="ts">
  import DebouncedInput from '../../ui/DebouncedInput.svelte';
  import Badge from '../../ui/Badge.svelte';
  import type { SearchController } from '../SearchController.svelte';
  import {
    Calendar,
    SlidersHorizontal,
    RotateCcw,
    LayoutGrid,
    Rows3,
    Layers,
    CalendarDays,
    Clock,
    Star,
    X
  } from '@lucide/svelte';

  interface Props {
    controller: SearchController;
    class?: string;
  }

  let { controller, class: className = '' }: Props = $props();

  let groupOptions = $derived([
    { label: 'All Groups', value: '' },
    ...controller.availableGroups
  ]);

  let selectedGroupValue = $derived(controller.selectedGroups[0] || '');

  let dateScopeLabel = $derived.by(() => {
    if (controller.dateScope === 'today') return 'TODAY';
    if (controller.dateScope === 'three_days') return '3 DAYS';
    return 'ALL';
  });
</script>

<div class="surface-card p-2.5 flex flex-col gap-2 w-full sticky top-0 z-30 bg-background/95 backdrop-blur-xs border-b border-border/40 shadow-xs {className}">
  <!-- Top Search Input with View & Density Toggles -->
  <div class="flex items-center gap-2 w-full">
    <div class="relative flex-1" title="Search programmes by title or description">
      <DebouncedInput
        placeholder="Search programmes, events, movies, channels..."
        value={controller.query}
        delayMs={250}
        onchange={(val) => controller.setQuery(val)}
      />
    </div>

    <!-- View & Density Switchers -->
    <div class="flex items-center gap-1 shrink-0">
      <!-- Layout Mode Toggle (Timeline vs Channel-Grouped) -->
      <button
        type="button"
        onclick={() => controller.toggleViewMode()}
        class="cursor-pointer p-1.5 rounded-lg border border-border/40 bg-card text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors touch-btn"
        title={controller.viewMode === 'timeline' ? 'Switch to Channel-Grouped View' : 'Switch to Chronological Timeline View'}
        aria-label="Toggle Layout Mode"
      >
        {#if controller.viewMode === 'timeline'}
          <Layers class="w-4 h-4 text-muted-foreground" />
        {:else}
          <CalendarDays class="w-4 h-4 text-primary" />
        {/if}
      </button>

      <!-- Density Mode Toggle (Cards vs Compact Rows) -->
      <button
        type="button"
        onclick={() => controller.toggleDensityMode()}
        class="cursor-pointer p-1.5 rounded-lg border border-border/40 bg-card text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors touch-btn"
        title={controller.densityMode === 'cards' ? 'Switch to Compact Rows' : 'Switch to Detailed Cards'}
        aria-label="Toggle Density Mode"
      >
        {#if controller.densityMode === 'cards'}
          <Rows3 class="w-4 h-4 text-muted-foreground" />
        {:else}
          <LayoutGrid class="w-4 h-4 text-primary" />
        {/if}
      </button>
    </div>
  </div>

  <!-- Recent Searches Chips (if available and no active query) -->
  {#if controller.recentSearches.length > 0 && !controller.query.trim()}
    <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5 text-xs text-muted-foreground">
      <span class="text-[10px] font-bold uppercase tracking-wider shrink-0">Recent:</span>
      {#each controller.recentSearches as recent}
        <div class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted/40 border border-border/30 hover:border-primary/40 text-[11px] shrink-0">
          <button
            type="button"
            onclick={() => controller.selectRecentSearch(recent)}
            class="cursor-pointer hover:text-foreground"
          >
            {recent}
          </button>
          <button
            type="button"
            onclick={() => controller.removeRecent(recent)}
            class="cursor-pointer hover:text-destructive ml-0.5"
            aria-label="Remove recent query"
          >
            <X class="w-3 h-3" />
          </button>
        </div>
      {/each}
      <button
        type="button"
        onclick={() => controller.clearRecent()}
        class="cursor-pointer text-[10px] text-muted-foreground hover:text-destructive underline ml-1 shrink-0"
      >
        Clear
      </button>
    </div>
  {/if}

  <!-- Faceted Chips Horizontal Scrollable Bar -->
  <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5 select-none text-xs">
    <!-- Curated (My List) Clickable Toggle Badge -->
    <button
      type="button"
      onclick={() => controller.toggleCuratedOnly()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors touch-btn shrink-0 {controller.curatedOnly ? 'bg-primary/15 border-primary text-primary font-bold' : 'bg-card border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30'}"
      title={controller.curatedOnly ? 'Filtering curated channels (My List) - Click to search all channels' : 'Searching all channels - Click to filter curated channels'}
      aria-label="Toggle Curated Channels Filter"
    >
      <Star class="w-3.5 h-3.5 {controller.curatedOnly ? 'fill-current' : 'text-muted-foreground'}" />
      <span>MY LIST</span>
    </button>

    <!-- Live Only Clickable Toggle Badge -->
    <button
      type="button"
      onclick={() => controller.toggleLive()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors touch-btn shrink-0 {controller.liveOnly ? 'bg-destructive/15 border-destructive text-destructive font-bold' : 'bg-card border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30'}"
      title="Filter currently broadcasted programmes"
      aria-label="Filter Live Now"
    >
      <span class="inline-block w-2 h-2 rounded-full {controller.liveOnly ? 'bg-destructive animate-pulse' : 'bg-muted-foreground/40'}"></span>
      <span>LIVE</span>
    </button>

    <!-- Prime Time Clickable Toggle Badge -->
    <button
      type="button"
      onclick={() => controller.togglePrimeTime()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors touch-btn shrink-0 {controller.primeTimeOnly ? 'bg-primary/15 border-primary text-primary font-bold' : 'bg-card border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30'}"
      title="Filter evening prime time programmes (20:30 - 23:00)"
      aria-label="Filter Prime Time"
    >
      <Clock class="w-3.5 h-3.5" />
      <span>PRIME TIME</span>
    </button>

    <!-- Today / 3 Days / All Clickable Toggle Badge -->
    <button
      type="button"
      onclick={() => controller.toggleDateScope()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors touch-btn shrink-0 {controller.dateScope !== 'all' ? 'bg-primary/15 border-primary text-primary font-bold' : 'bg-card border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30'}"
      title="Toggle between today programmes, 3 days, and all dates"
      aria-label="Toggle Date Scope"
    >
      <Calendar class="w-3.5 h-3.5" />
      <span>{dateScopeLabel}</span>
    </button>

    <!-- Online Stream Only Clickable Toggle Badge -->
    <button
      type="button"
      onclick={() => controller.toggleOnlineOnly()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors touch-btn shrink-0 {controller.onlineOnly ? 'bg-primary/15 border-primary text-primary font-bold' : 'bg-card border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30'}"
      title="Filter channels with verified online link status"
      aria-label="Filter verified online streams"
    >
      <span class="inline-block w-2 h-2 rounded-full {controller.onlineOnly ? 'bg-primary' : 'bg-muted-foreground/40'}"></span>
      <span>ONLINE ONLY</span>
    </button>

    <!-- Group Filter Dropdown -->
    <div class="shrink-0 min-w-[130px]">
      <select
        value={selectedGroupValue}
        onchange={(e) => controller.switchGroup((e.target as HTMLSelectElement).value)}
        class="select-compact w-full text-xs cursor-pointer py-1 px-2 bg-card border border-border/40 rounded-full text-foreground"
        title="Filter by category group"
        aria-label="Filter by category group"
      >
        {#each groupOptions as opt}
          <option value={opt.value}>{opt.label}</option>
        {/each}
      </select>
    </div>

    <!-- Reset Filters Button (visible when any filter active) -->
    {#if controller.activeFilterCount > 0 || controller.query.trim()}
      <button
        type="button"
        onclick={() => controller.resetFilters()}
        class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-border/40 text-muted-foreground hover:text-destructive hover:border-destructive/40 transition-colors touch-btn shrink-0"
        title="Reset all filters to defaults"
        aria-label="Reset all filters"
      >
        <RotateCcw class="w-3 h-3" />
        <span>Reset</span>
      </button>
    {/if}

    <!-- Advanced Settings Modal Trigger -->
    <button
      type="button"
      onclick={() => controller.openAdvancedModal()}
      class="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors touch-btn shrink-0 ml-auto"
      title="Open advanced EPG search options"
      aria-label="Open advanced EPG search options"
    >
      <SlidersHorizontal class="w-3.5 h-3.5" />
      <span class="hidden sm:inline text-[11px]">Advanced</span>
      {#if controller.activeFilterCount > 0}
        <Badge variant="primary" class="!px-1.5 !py-0 text-[10px] ml-0.5">
          {controller.activeFilterCount}
        </Badge>
      {/if}
    </button>
  </div>
</div>
