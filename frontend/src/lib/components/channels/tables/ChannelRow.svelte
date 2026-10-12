<script lang="ts">
  import ChannelIdentity from './ChannelIdentity.svelte';
  import ChannelMetadata from './ChannelMetadata.svelte';
  import ChannelStatusCluster from './ChannelStatusCluster.svelte';
  import ChannelActionsGroup from './ChannelActionsGroup.svelte';
  import Checkbox from '../../ui/Checkbox.svelte';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel: ChannelItem;
    selectable?: boolean;
    isSelected?: boolean;
    showLogo?: boolean;
    showName?: boolean;
    showSource?: boolean;
    showGroup?: boolean;
    showBookmark?: boolean;
    showLinkStatus?: boolean;
    showEpg?: boolean;
    showInclusion?: boolean;
    showDetails?: boolean;
    showMerge?: boolean;
    showPlay?: boolean;
    ontoggleselect?: (channel: ChannelItem) => void;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    ontogglebookmark?: (channel: ChannelItem) => void;
    onshowdetails?: (channel: ChannelItem) => void;
    oneditmetadata?: (channel: ChannelItem) => void;
    oneditlogo?: (channel: ChannelItem) => void;
    oneditname?: (channel: ChannelItem) => void;
    oneditgroup?: (channel: ChannelItem) => void;
    onediturl?: (channel: ChannelItem) => void;
    onedituseragent?: (channel: ChannelItem) => void;
    oneditmapping?: (channel: ChannelItem) => void;
    ontestlink?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
    testingLink?: boolean;
    class?: string;
  }

  let {
    channel,
    selectable = false,
    isSelected = false,
    showLogo = true,
    showName = true,
    showSource = true,
    showGroup = true,
    showBookmark = true,
    showLinkStatus = true,
    showEpg = true,
    showInclusion = true,
    showDetails = true,
    showMerge = true,
    showPlay = true,
    ontoggleselect,
    ontoggleinclusion,
    ontogglebookmark,
    onshowdetails,
    oneditmetadata,
    oneditlogo,
    oneditname,
    oneditgroup,
    oneditmapping,
    ontestlink,
    onplaystream,
    onopenfailover,
    testingLink = false,
    class: className = ''
  }: Props = $props();

  let isRowSelected = $derived(isSelected);
  let isLocked = $derived(Boolean(channel.is_locked));
  let isModified = $derived(Boolean(channel.is_modified));
  let hasMetadataVisible = $derived(showSource || (showGroup && Boolean(channel.group)));
</script>

<div
  class="channel-row group flex flex-col md:grid md:grid-cols-[minmax(220px,1.2fr)_minmax(140px,0.8fr)_auto_auto] md:items-center gap-1.5 md:gap-4 p-2.5 md:px-3 md:py-2 bg-card/40 hover:bg-card/90 rounded-md md:rounded-none border border-border/30 md:border-0 md:border-b md:border-border/30 transition-all {isRowSelected ? '!bg-primary/10 border-primary/40' : ''} {isLocked ? 'border-amber-500/20 bg-amber-500/5' : ''} {isModified ? 'channel-row-modified' : ''} {className}"
>
  <!-- Mobile Line 1: Checkbox + Identity (Left) & Status Cluster (Right) -->
  <div class="flex items-center justify-between gap-2 w-full min-w-0 md:contents">
    <div class="flex items-center gap-2.5 min-w-0 flex-1">
      {#if selectable}
        <div class="shrink-0 flex items-center">
          <Checkbox
            checked={isRowSelected}
            onCheckedChange={() => ontoggleselect?.(channel)}
            aria-label={`Select channel ${channel.name}`}
          />
        </div>
      {/if}

      <ChannelIdentity
        {channel}
        {showLogo}
        {showName}
        {oneditlogo}
        {oneditname}
        class="flex-1 min-w-0"
      />
    </div>

    <!-- Status Cluster (Right on Mobile, Column 3 on Desktop) -->
    <div class="shrink-0 md:order-3">
      <ChannelStatusCluster
        {channel}
        {showBookmark}
        {showLinkStatus}
        {showEpg}
        {showInclusion}
        {ontogglebookmark}
        {ontestlink}
        {oneditmapping}
        {ontoggleinclusion}
        {testingLink}
      />
    </div>
  </div>

  <!-- Mobile Line 2: Metadata (Left) & Actions Group (Right) -->
  <div class="flex items-center justify-between gap-2 w-full min-w-0 pt-1.5 border-t border-border/20 md:border-0 md:pt-0 md:contents">
    <!-- Metadata (Column 2 on Desktop) -->
    <div class="min-w-0 flex-1 md:order-2">
      {#if hasMetadataVisible}
        <ChannelMetadata
          {channel}
          {showSource}
          {showGroup}
          {oneditgroup}
          {oneditmetadata}
        />
      {/if}
    </div>

    <!-- Actions Group (Column 4 on Desktop) -->
    <div class="shrink-0 md:order-4">
      <ChannelActionsGroup
        {channel}
        {showDetails}
        {showMerge}
        {showPlay}
        {onshowdetails}
        {onopenfailover}
        {onplaystream}
      />
    </div>
  </div>
</div>
