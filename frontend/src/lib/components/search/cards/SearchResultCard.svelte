<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import LiveBadge from '../../channels/badges/LiveBadge.svelte';
  import ChannelIdentity from '../../channels/tables/ChannelIdentity.svelte';
  import type { SearchResultItem } from '../utils/SearchUtils';
  import { highlightQueryMatches } from '../utils/SearchUtils';
  import SearchProgramModal from '../modals/SearchProgramModal.svelte';
  import { Play, Star, Sparkles, Info } from '@lucide/svelte';

  interface Props {
    item: SearchResultItem;
    queryTokens?: string[];
    compact?: boolean;
    ontogglebookmark?: (channel: any) => void;
    class?: string;
  }

  let {
    item,
    queryTokens = [],
    compact = false,
    ontogglebookmark,
    class: className = ''
  }: Props = $props();

  let isExpanded = $state(false);
  let showInfoModal = $state(false);

  let targetLiveHref = $derived.by(() => {
    const channelId = item.channel.id;
    const dateStr = item.startDate.toISOString().split('T')[0];
    const timeEpoch = item.startDate.getTime();
    return `#/live?channel=${encodeURIComponent(channelId)}&date=${encodeURIComponent(dateStr)}&time=${timeEpoch}`;
  });

  function handlePlayStream() {
    window.location.hash = targetLiveHref;
  }

  let isBookmarked = $derived(Boolean(item.channel.is_bookmarked));
  let highlightedTitle = $derived(highlightQueryMatches(item.program.t, queryTokens));
  let highlightedDesc = $derived(highlightQueryMatches(item.program.d || '', queryTokens));
</script>

{#if compact}
  <!-- Compact Row View -->
  <div class="surface-card p-2 flex items-center justify-between gap-2.5 transition-all hover:border-primary/40 border border-border/30 rounded-lg shadow-xs {className}">
    <div class="flex items-center gap-2.5 min-w-0 flex-1">
      <button
        type="button"
        onclick={() => ontogglebookmark ? ontogglebookmark(item.channel) : null}
        class="cursor-pointer text-muted-foreground hover:text-primary shrink-0"
        title={isBookmarked ? 'Bookmarked in personal playlist' : 'Bookmark channel'}
        aria-label="Toggle Bookmark"
      >
        <Star class="w-4 h-4 {isBookmarked ? 'text-primary fill-primary' : ''}" />
      </button>

      <div class="flex flex-col min-w-0">
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-bold text-foreground truncate">
            {@html highlightedTitle}
          </span>
          {#if item.isLive}
            <LiveBadge class="!py-0 !px-1.5 text-[9px]" />
          {/if}
        </div>
        <div class="flex items-center gap-2 text-[11px] text-muted-foreground font-mono truncate">
          <span>{item.channel.name}</span>
          <span>•</span>
          <span>{item.timeLabel}</span>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-1.5 shrink-0">
      <Badge variant="muted" class="text-[10px] font-mono hidden sm:inline-flex items-center gap-1 text-muted-foreground" title={`Score: ${item.score}`}>
        <Sparkles class="w-2.5 h-2.5" />
        <span>{item.score}</span>
      </Badge>
      <Button
        variant="ghost"
        size="sm"
        onclick={() => { showInfoModal = true; }}
        class="!p-1.5 text-muted-foreground hover:text-foreground touch-btn"
        title="Programme Details"
        aria-label="Programme Details"
      >
        <Info class="w-3.5 h-3.5" />
      </Button>
      {#if item.isLive}
        <Button
          variant="primary"
          size="sm"
          onclick={handlePlayStream}
          class="!py-1 !px-2 text-xs font-bold flex items-center gap-1 touch-btn"
          title="Play Now"
          aria-label="Play Now"
        >
          <Play class="w-3 h-3 fill-current" />
          <span class="hidden md:inline">Play Now</span>
        </Button>
      {/if}
    </div>
  </div>
{:else}
  <!-- Detailed Card View -->
  <div class="surface-card p-3 flex flex-col gap-2 transition-all hover:border-primary/40 border border-border/30 rounded-lg shadow-xs {className}">
    <!-- Top Row: Channel Identity, Star Bookmark, Badges and Score -->
    <div class="flex items-center justify-between gap-2 flex-wrap text-xs">
      <div class="flex items-center gap-2 min-w-0">
        <button
          type="button"
          onclick={() => ontogglebookmark ? ontogglebookmark(item.channel) : null}
          class="cursor-pointer text-muted-foreground hover:text-primary shrink-0"
          title={isBookmarked ? 'Bookmarked in personal playlist' : 'Bookmark channel'}
          aria-label="Toggle Bookmark"
        >
          <Star class="w-3.5 h-3.5 {isBookmarked ? 'text-primary fill-primary' : ''}" />
        </button>

        <ChannelIdentity channel={item.channel} />
        {#if item.channel.group}
          <Badge variant="muted" class="text-[10px] hidden sm:inline-flex">{item.channel.group}</Badge>
        {/if}
      </div>

      <div class="flex items-center gap-1.5 shrink-0">
        {#if item.isLive}
          <LiveBadge />
        {/if}
        <Badge variant="muted" class="font-mono text-[10px] flex items-center gap-1 text-muted-foreground" title={`Score: ${item.score}`}>
          <Sparkles class="w-2.5 h-2.5" />
          <span>{item.score}</span>
        </Badge>
      </div>
    </div>

    <!-- Middle Row: Programme Title and Schedule -->
    <div class="flex flex-col gap-0.5">
      <h2 class="text-sm font-bold text-foreground leading-snug break-words">
        {@html highlightedTitle}
      </h2>
      <div class="flex items-center gap-2 text-xs text-muted-foreground font-mono">
        <span>{item.timeLabel}</span>
        <span>•</span>
        <span>{item.durationMins} mins</span>
      </div>
    </div>

    <!-- Description Preview if available -->
    {#if item.program.d}
      <div class="text-xs text-muted-foreground/90 leading-relaxed">
        <span class={isExpanded ? '' : 'line-clamp-2'}>
          {@html highlightedDesc}
        </span>
        {#if item.program.d.length > 180}
          <button
            type="button"
            onclick={() => { isExpanded = !isExpanded; }}
            class="text-[11px] text-primary hover:underline font-semibold cursor-pointer ml-1 inline-block"
          >
            {isExpanded ? 'Show less' : 'Show more'}
          </button>
        {/if}
      </div>
    {/if}

    <!-- Actions Footer -->
    <div class="pt-1.5 border-t border-border/20 flex items-center justify-between gap-2">
      <Button
        variant="ghost"
        size="sm"
        onclick={() => { showInfoModal = true; }}
        class="!py-1 !px-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 touch-btn"
        title="Programme Details"
        aria-label="Programme Details"
      >
        <Info class="w-3.5 h-3.5" />
        <span>Details</span>
      </Button>

      <div class="flex items-center gap-1.5">
        {#if item.isLive}
          <Button
            variant="primary"
            size="sm"
            onclick={handlePlayStream}
            class="!py-1 !px-3 text-xs font-bold flex items-center gap-1.5 touch-btn"
            title="Play live stream now"
          >
            <Play class="w-3.5 h-3.5 fill-current" />
            <span>Play Now</span>
          </Button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<SearchProgramModal
  bind:open={showInfoModal}
  {item}
  {ontogglebookmark}
/>
