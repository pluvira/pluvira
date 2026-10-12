<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import ChannelIdentity from '../../channels/tables/ChannelIdentity.svelte';
  import SearchResultCard from './SearchResultCard.svelte';
  import type { ChannelGroupedSearchResult } from '../utils/SearchUtils';
  import { Play, Star, ChevronDown, ChevronUp } from '@lucide/svelte';

  interface Props {
    group: ChannelGroupedSearchResult;
    queryTokens?: string[];
    compact?: boolean;
    ontogglebookmark?: (channel: any) => void;
    class?: string;
  }

  let {
    group,
    queryTokens = [],
    compact = false,
    ontogglebookmark,
    class: className = ''
  }: Props = $props();

  let isExpanded = $state(true);
  let isBookmarked = $derived(Boolean(group.channel.is_bookmarked));

  function handlePlayChannel() {
    const channelId = group.channel.id;
    window.location.hash = `#/live?channel=${encodeURIComponent(channelId)}`;
  }
</script>

<div class="surface-card border border-border/40 rounded-xl overflow-hidden shadow-xs flex flex-col gap-0 {className}">
  <!-- Group Header Banner -->
  <div class="bg-card/70 border-b border-border/30 p-2.5 flex items-center justify-between gap-2">
    <div class="flex items-center gap-2.5 min-w-0 flex-1">
      <button
        type="button"
        onclick={() => ontogglebookmark ? ontogglebookmark(group.channel) : null}
        class="cursor-pointer text-muted-foreground hover:text-primary shrink-0"
        title={isBookmarked ? 'Bookmarked in personal playlist' : 'Bookmark channel'}
        aria-label="Toggle Bookmark"
      >
        <Star class="w-4 h-4 {isBookmarked ? 'text-primary fill-primary' : ''}" />
      </button>

      <ChannelIdentity channel={group.channel} />
      {#if group.channel.group}
        <Badge variant="muted" class="text-[10px] hidden sm:inline-flex">{group.channel.group}</Badge>
      {/if}
      {#if group.channel.source}
        <span class="text-[11px] text-muted-foreground truncate">{group.channel.source}</span>
      {/if}
    </div>

    <!-- Actions & Expansion Control -->
    <div class="flex items-center gap-1.5 shrink-0">
      <Badge variant="primary" class="font-mono text-xs">
        {group.items.length} {group.items.length === 1 ? 'match' : 'matches'}
      </Badge>

      <Button
        variant="secondary"
        size="sm"
        onclick={handlePlayChannel}
        class="!p-1.5 touch-btn"
        title="Play Channel Stream"
        aria-label="Play Channel Stream"
      >
        <Play class="w-3.5 h-3.5 fill-current" />
      </Button>

      <button
        type="button"
        onclick={() => { isExpanded = !isExpanded; }}
        class="cursor-pointer p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted/30 transition-colors"
        title={isExpanded ? 'Collapse group' : 'Expand group'}
        aria-label="Toggle group collapse"
      >
        {#if isExpanded}
          <ChevronUp class="w-4 h-4" />
        {:else}
          <ChevronDown class="w-4 h-4" />
        {/if}
      </button>
    </div>
  </div>

  <!-- Group Programme Items List -->
  {#if isExpanded}
    <div class="p-2.5 flex flex-col gap-2 bg-background/30">
      {#each group.items as item, idx (item.channel.id + '_' + item.program.s + '_' + (item.program.e || '') + '_' + item.program.t + '_' + idx)}
        <SearchResultCard
          {item}
          {queryTokens}
          {compact}
          {ontogglebookmark}
        />
      {/each}
    </div>
  {/if}
</div>
