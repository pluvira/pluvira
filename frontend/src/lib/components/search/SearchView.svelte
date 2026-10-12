<script lang="ts">
  import { onMount } from 'svelte';
  import { SearchController } from './SearchController.svelte';
  import SearchStickyCard from './bars/SearchStickyCard.svelte';
  import SearchResultCard from './cards/SearchResultCard.svelte';
  import SearchResultGroup from './cards/SearchResultGroup.svelte';
  import SearchFilterSheet from './modals/SearchFilterSheet.svelte';
  import Button from '../ui/Button.svelte';
  import { videoPlayerStore } from '$lib/components/player/VideoPlayerStore';
  import { Search as SearchIcon, ChevronLeft, ChevronRight, Sparkles } from '@lucide/svelte';
  import { SUGGESTED_SEARCH_TOPICS } from './utils';

  const controller = new SearchController();

  onMount(() => {
    controller.loadSearchData();
    const unsubscribe = videoPlayerStore.onStatusUpdate((evt) => {
      controller.handleStreamStatusUpdate(evt);
    });
    return () => {
      unsubscribe();
    };
  });

  let queryTokens = $derived(controller.query.trim().split(/\s+/).filter(Boolean));
</script>

<div class="flex flex-col gap-3 w-full select-none" data-testid="search-view">
  <!-- Sticky Search Header Card (without page title h1) -->
  <SearchStickyCard {controller} />

  <!-- Search Results Feed -->
  {#if controller.loading}
    <div class="state-empty">
      <span class="spinner mr-3"></span>
      <span class="text-sm font-bold">Loading EPG guide data...</span>
    </div>
  {:else if controller.results.length === 0}
    <div class="state-empty py-12 flex flex-col items-center justify-center text-center">
      <SearchIcon class="w-10 h-10 mb-3 text-muted-foreground/60" />
      <span class="text-sm font-bold text-foreground">No programmes found matching the active search criteria.</span>
      <span class="text-xs text-muted-foreground mt-1 max-w-md">
        Try typing keywords or choose one of the suggested categories below:
      </span>

      <div class="flex items-center justify-center gap-1.5 flex-wrap mt-4 max-w-md">
        {#each SUGGESTED_SEARCH_TOPICS as topic}
          <button
            type="button"
            onclick={() => controller.setQuery(topic)}
            class="cursor-pointer inline-flex items-center gap-1 px-3 py-1 rounded-full bg-card border border-border/40 hover:border-primary/50 text-xs text-muted-foreground hover:text-foreground transition-all touch-btn shadow-2xs"
          >
            <Sparkles class="w-3 h-3 text-primary" />
            <span>{topic}</span>
          </button>
        {/each}
      </div>
    </div>
  {:else}
    <!-- Status Header with Inline Pagination -->
    <div class="flex items-center justify-between px-1 text-xs text-muted-foreground">
      <span class="truncate">
        <strong>{controller.results.length}</strong> {controller.results.length === 1 ? 'programme' : 'programmes'}
        {#if controller.viewMode === 'grouped'}
          <span>across <strong>{controller.groupedResults.length}</strong> {controller.groupedResults.length === 1 ? 'channel' : 'channels'}</span>
        {/if}
      </span>

      {#if controller.totalPages > 1}
        <div class="flex items-center gap-1.5 shrink-0 bg-card/60 px-2 py-0.5 rounded-md border border-border/30">
          <button
            type="button"
            disabled={controller.page <= 1}
            onclick={() => controller.prevPage()}
            class="cursor-pointer p-0.5 rounded hover:bg-muted/40 disabled:opacity-30 disabled:cursor-not-allowed text-foreground"
            aria-label="Previous Page"
            title="Previous Page"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
          </button>

          <span class="font-mono text-[11px] text-foreground font-semibold">
            {controller.page} / {controller.totalPages}
          </span>

          <button
            type="button"
            disabled={controller.page >= controller.totalPages}
            onclick={() => controller.nextPage()}
            class="cursor-pointer p-0.5 rounded hover:bg-muted/40 disabled:opacity-30 disabled:cursor-not-allowed text-foreground"
            aria-label="Next Page"
            title="Next Page"
          >
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>
      {/if}
    </div>

    <!-- Timeline Mode Display -->
    {#if controller.viewMode === 'timeline'}
      {#if controller.densityMode === 'compact'}
        <div class="flex flex-col gap-1.5 w-full">
          {#each controller.paginatedResults as item, idx (item.channel.id + '_' + item.program.s + '_' + (item.program.e || '') + '_' + item.program.t + '_' + idx)}
            <SearchResultCard
              {item}
              {queryTokens}
              compact={true}
              ontogglebookmark={(ch) => controller.toggleBookmark(ch)}
            />
          {/each}
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
          {#each controller.paginatedResults as item, idx (item.channel.id + '_' + item.program.s + '_' + (item.program.e || '') + '_' + item.program.t + '_' + idx)}
            <SearchResultCard
              {item}
              {queryTokens}
              compact={false}
              ontogglebookmark={(ch) => controller.toggleBookmark(ch)}
            />
          {/each}
        </div>
      {/if}
    {:else}
      <!-- Channel-Grouped Mode Display -->
      <div class="flex flex-col gap-3 w-full">
        {#each controller.paginatedGroupedResults as group, gIdx ((group.channel.id || group.channel.name) + '_' + gIdx)}
          <SearchResultGroup
            {group}
            {queryTokens}
            compact={controller.densityMode === 'compact'}
            ontogglebookmark={(ch) => controller.toggleBookmark(ch)}
          />
        {/each}
      </div>
    {/if}

    <!-- Pagination Controls Footer -->
    {#if controller.totalPages > 1}
      <div class="flex items-center justify-between gap-2 p-2 mt-2 surface-card border border-border/30 rounded-lg text-xs">
        <Button
          variant="outline"
          size="sm"
          disabled={controller.page <= 1}
          onclick={() => controller.prevPage()}
          class="touch-btn flex items-center gap-1 text-xs"
          aria-label="Previous Page"
        >
          <ChevronLeft class="w-3.5 h-3.5" />
          <span>Prev</span>
        </Button>

        <span class="text-muted-foreground font-mono">
          Page <strong>{controller.page}</strong> of <strong>{controller.totalPages}</strong>
        </span>

        <Button
          variant="outline"
          size="sm"
          disabled={controller.page >= controller.totalPages}
          onclick={() => controller.nextPage()}
          class="touch-btn flex items-center gap-1 text-xs"
          aria-label="Next Page"
        >
          <span>Next</span>
          <ChevronRight class="w-3.5 h-3.5" />
        </Button>
      </div>
    {/if}
  {/if}

  <!-- Advanced Search Filter Sheet -->
  <SearchFilterSheet
    {controller}
    bind:open={controller.showAdvancedModal}
  />
</div>
