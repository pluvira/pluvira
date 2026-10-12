<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import LiveBadge from '../../channels/badges/LiveBadge.svelte';
  import ChannelIdentity from '../../channels/tables/ChannelIdentity.svelte';
  import type { SearchResultItem } from '../utils/SearchUtils';
  import { Play, Sparkles, Star, Clock } from '@lucide/svelte';

  interface Props {
    item?: SearchResultItem | null;
    open?: boolean;
    ontogglebookmark?: (channel: any) => void;
    onclose?: () => void;
  }

  let {
    item,
    open = $bindable(),
    ontogglebookmark,
    onclose
  }: Props = $props();

  function handleClose() {
    if (onclose) onclose();
    else open = false;
  }

  function handlePlay() {
    if (item) {
      const channelId = item.channel.id;
      const dateStr = item.startDate.toISOString().split('T')[0];
      const timeEpoch = item.startDate.getTime();
      window.location.hash = `#/live?channel=${encodeURIComponent(channelId)}&date=${encodeURIComponent(dateStr)}&time=${timeEpoch}`;
      handleClose();
    }
  }

  let isBookmarked = $derived(Boolean(item?.channel?.is_bookmarked));
</script>

<Dialog
  {open}
  title="Programme Details"
  onclose={handleClose}
>
  {#if item}
    <div class="flex flex-col gap-3.5 text-sm">
      <!-- Channel & Match Score Header -->
      <div class="flex items-center justify-between gap-2 p-2.5 bg-muted/20 border border-border/30 rounded-lg">
        <div class="flex items-center gap-2.5 min-w-0">
          <ChannelIdentity channel={item.channel} />
          {#if item.channel.group}
            <Badge variant="muted" class="text-[10px]">{item.channel.group}</Badge>
          {/if}
          {#if item.channel.source}
            <span class="text-[11px] text-muted-foreground truncate">{item.channel.source}</span>
          {/if}
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onclick={() => ontogglebookmark ? ontogglebookmark(item.channel) : null}
            class="cursor-pointer p-1.5 text-muted-foreground hover:text-primary rounded-lg hover:bg-muted/30"
            title={isBookmarked ? 'Bookmarked' : 'Bookmark'}
            aria-label="Toggle Bookmark"
          >
            <Star class="w-4 h-4 {isBookmarked ? 'text-primary fill-primary' : ''}" />
          </button>

          <Badge variant="muted" class="font-mono text-xs flex items-center gap-1 text-muted-foreground">
            <Sparkles class="w-3 h-3" />
            <span>{item.score}</span>
          </Badge>
        </div>
      </div>

      <!-- Title & Time Schedule -->
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-2">
          <h2 class="text-base font-bold text-foreground leading-snug">
            {item.program.t}
          </h2>
          {#if item.isLive}
            <LiveBadge />
          {/if}
        </div>

        <div class="flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <Clock class="w-3.5 h-3.5 text-primary" />
          <span>{item.timeLabel}</span>
          <span>•</span>
          <span>{item.durationMins} minutes</span>
        </div>
      </div>

      <!-- Full Synopsis Description -->
      <div class="p-3 bg-muted/10 border border-border/20 rounded-lg flex flex-col gap-1">
        <span class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Synopsis</span>
        <p class="text-xs text-foreground/90 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
          {item.program.d || 'No additional programme description provided.'}
        </p>
      </div>

      <!-- Action Footer -->
      <div class="flex items-center justify-end gap-2 pt-2 border-t border-border/20">
        <Button
          variant="ghost"
          size="sm"
          onclick={handleClose}
          class="text-xs touch-btn"
        >
          Close
        </Button>

          {#if item.isLive}
            <Button
              variant="primary"
              size="sm"
              onclick={handlePlay}
              class="text-xs font-bold flex items-center gap-1.5 touch-btn"
            >
              <Play class="w-3.5 h-3.5 fill-current" />
              <span>Play Stream</span>
            </Button>
        {/if}
      </div>
    </div>
  {/if}
</Dialog>
