<script lang="ts">
  import ActionableIndicator from '../../ui/ActionableIndicator.svelte';
  import { Calendar, Star, Eye, EyeOff, Lock } from '@lucide/svelte';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel: ChannelItem;
    showBookmark?: boolean;
    showLinkStatus?: boolean;
    showEpg?: boolean;
    showInclusion?: boolean;
    ontogglebookmark?: (channel: ChannelItem) => void;
    ontestlink?: (channel: ChannelItem) => void;
    oneditmapping?: (channel: ChannelItem) => void;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    testingLink?: boolean;
    class?: string;
  }

  let {
    channel,
    showBookmark = true,
    showLinkStatus = true,
    showEpg = true,
    showInclusion = true,
    ontogglebookmark,
    ontestlink,
    oneditmapping,
    ontoggleinclusion,
    testingLink = false,
    class: className = ''
  }: Props = $props();

  let linkDotColor = $derived.by(() => {
    if (channel.link_status === 'online') return 'bg-success';
    if (channel.link_status === 'offline') return 'bg-destructive';
    return 'bg-muted-foreground/40';
  });

  let linkStatusLabel = $derived.by(() => {
    if (channel.link_status === 'online') return 'Stream link is online';
    if (channel.link_status === 'offline') return 'Stream link is offline';
    return 'Stream link status unchecked';
  });
</script>

<div class="channel-status-cluster inline-flex items-center gap-1 shrink-0 {className}">
  <!-- Padlock Indicator for Locked Channels (Position 26+ in Free Tier) -->
  {#if channel.is_locked}
    <ActionableIndicator
      label="Channel locked: Pro or 14-day trial required for channels 26+"
      variant="warning"
    >
      <Lock class="w-4 h-4 text-amber-500" />
    </ActionableIndicator>
  {/if}

  <!-- Bookmark Star Indicator -->
  {#if showBookmark && ontogglebookmark}
    <ActionableIndicator
      label={channel.is_bookmarked ? 'Remove from curated playlist' : 'Bookmark in curated playlist'}
      variant={channel.is_bookmarked ? 'primary' : 'muted'}
      onclick={() => ontogglebookmark(channel)}
    >
      <Star class="w-4 h-4 {channel.is_bookmarked ? 'fill-current text-primary' : 'text-muted-foreground/40 hover:text-primary'}" />
    </ActionableIndicator>
  {/if}

  <!-- Link Status Dot Indicator -->
  {#if showLinkStatus}
    <ActionableIndicator
      label={linkStatusLabel}
      loading={testingLink}
      onclick={() => ontestlink?.(channel)}
    >
      <span class="w-3 h-3 rounded-full {linkDotColor} transition-transform hover:scale-125 inline-block"></span>
    </ActionableIndicator>
  {/if}

  <!-- EPG Calendar -->
  {#if showEpg}
    {#if channel.is_mapped}
      <ActionableIndicator
        label={`EPG Mapped: ${channel.epg_id || 'Yes'}`}
        variant="success"
        onclick={() => oneditmapping?.(channel)}
      >
        <Calendar class="w-4 h-4 text-success" />
      </ActionableIndicator>
    {:else if oneditmapping}
      <ActionableIndicator
        label="No EPG mapping (Click to map)"
        variant="muted"
        onclick={() => oneditmapping(channel)}
      >
        <Calendar class="w-4 h-4 text-muted-foreground/30 hover:text-muted-foreground" />
      </ActionableIndicator>
    {/if}
  {/if}

  <!-- Visibility Toggle Indicator (Check/Ban legacy compatible) -->
  {#if showInclusion && ontoggleinclusion}
    <ActionableIndicator
      label={channel.is_included ? 'Visible in catalog (Click to hide)' : 'Hidden from catalog (Click to show)'}
      variant={channel.is_included ? 'success' : 'danger'}
      onclick={() => ontoggleinclusion(channel)}
    >
      {#if channel.is_included}
        <Eye class="w-4 h-4 text-success" />
      {:else}
        <EyeOff class="w-4 h-4 text-destructive" />
      {/if}
    </ActionableIndicator>
  {/if}
</div>
