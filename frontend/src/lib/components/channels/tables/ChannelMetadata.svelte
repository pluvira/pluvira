<script lang="ts">
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel: ChannelItem;
    showSource?: boolean;
    showGroup?: boolean;
    oneditgroup?: (channel: ChannelItem) => void;
    oneditmetadata?: (channel: ChannelItem) => void;
    class?: string;
  }

  let {
    channel,
    showSource = true,
    showGroup = true,
    oneditgroup,
    oneditmetadata,
    class: className = ''
  }: Props = $props();
</script>

<div class="channel-metadata flex items-center gap-1.5 text-xs text-muted-foreground truncate min-w-0 {className}">
  {#if showSource}
    <span class="font-bold text-foreground/80 truncate shrink-0">{channel.source}</span>
  {/if}
  {#if showSource && showGroup && channel.group}
    <span class="text-muted-foreground/60">•</span>
  {/if}
  {#if showGroup && channel.group}
    <button
      type="button"
      onclick={() => (oneditgroup ? oneditgroup(channel) : oneditmetadata?.(channel))}
      class="hover:text-foreground hover:underline transition-colors cursor-pointer truncate"
      title={`Click to edit group: ${channel.group}`}
    >
      {channel.group}
    </button>
  {/if}
</div>
