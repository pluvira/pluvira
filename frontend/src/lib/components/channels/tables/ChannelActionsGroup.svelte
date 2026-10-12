<script lang="ts">
  import { Info, GitCompare, Play } from '@lucide/svelte';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel: ChannelItem;
    showDetails?: boolean;
    showMerge?: boolean;
    showPlay?: boolean;
    onshowdetails?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    class?: string;
  }

  let {
    channel,
    showDetails = true,
    showMerge = true,
    showPlay = true,
    onshowdetails,
    onopenfailover,
    onplaystream,
    class: className = ''
  }: Props = $props();

  let backupCount = $derived(channel.backup_streams?.length || 0);
</script>

<div class="channel-actions-group inline-flex items-center gap-1 shrink-0 {className}">
  <!-- Info / Details Button -->
  {#if showDetails && onshowdetails}
    <button
      type="button"
      onclick={() => onshowdetails(channel)}
      class="inline-flex items-center justify-center p-1 rounded text-muted-foreground hover:text-foreground hover:bg-card transition-colors cursor-pointer touch-btn"
      title="View channel details"
      aria-label={`View details for ${channel.name}`}
    >
      <Info class="w-4 h-4" />
    </button>
  {/if}

  <!-- Merge / Failover Button -->
  {#if showMerge}
    {#if onopenfailover}
      <button
        type="button"
        onclick={() => onopenfailover(channel)}
        class="inline-flex items-center justify-center p-1 rounded {backupCount > 0 ? 'text-primary bg-primary/10 hover:bg-primary/20' : 'text-muted-foreground hover:text-foreground hover:bg-card'} transition-colors cursor-pointer touch-btn"
        title={backupCount > 0 ? `Failover active (${backupCount} backup streams)` : 'Configure failover & backups'}
        aria-label={`Failover configuration for ${channel.name}`}
      >
        <div class="inline-flex items-center gap-0.5">
          <GitCompare class="w-4 h-4" />
          {#if backupCount > 0}
            <span class="text-[10px] font-bold">+{backupCount}</span>
          {/if}
        </div>
      </button>
    {:else}
      <a href="#/channels?tab=merge" title="Open Merge & Failover Tool" class="inline-flex items-center justify-center p-1 rounded text-muted-foreground hover:text-foreground hover:bg-card transition-colors cursor-pointer touch-btn">
        <GitCompare class="w-4 h-4" />
      </a>
    {/if}
  {/if}

  <!-- Play Live Stream Button -->
  {#if showPlay && onplaystream}
    <button
      type="button"
      disabled={channel.is_locked}
      onclick={() => !channel.is_locked && onplaystream(channel)}
      class="inline-flex items-center justify-center p-1 rounded {channel.is_locked ? 'text-muted-foreground/30 cursor-not-allowed' : 'text-primary hover:text-primary hover:bg-primary/15 cursor-pointer'} transition-colors touch-btn"
      title={channel.is_locked ? 'Channel locked (Pro or trial required)' : 'Play live stream'}
      aria-label={channel.is_locked ? `Channel ${channel.name} is locked` : `Play stream for ${channel.name}`}
    >
      <Play class="w-4 h-4 fill-current" />
    </button>
  {/if}
</div>
