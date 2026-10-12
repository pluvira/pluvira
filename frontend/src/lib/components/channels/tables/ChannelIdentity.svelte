<script lang="ts">
  import { Camera } from '@lucide/svelte';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel: ChannelItem;
    showLogo?: boolean;
    showName?: boolean;
    oneditlogo?: (channel: ChannelItem) => void;
    oneditname?: (channel: ChannelItem) => void;
    class?: string;
  }

  let {
    channel,
    showLogo = true,
    showName = true,
    oneditlogo,
    oneditname,
    class: className = ''
  }: Props = $props();

  let isHidden = $derived(!channel.is_included);
  let isExcluded = $derived(isHidden);
  let isLocked = $derived(Boolean(channel.is_locked));
  let isModified = $derived(Boolean(channel.is_modified));
</script>

<div class="channel-identity flex items-center gap-2.5 min-w-0 {isHidden ? 'opacity-40' : ''} {isLocked ? 'opacity-70' : ''} {className}">
  <!-- Channel Logo (Optional) -->
  {#if showLogo}
    <button
      type="button"
      onclick={() => oneditlogo?.(channel)}
      class="w-9 h-7 bg-background border border-border/30 rounded flex items-center justify-center overflow-hidden shrink-0 cursor-pointer hover:border-foreground transition-colors"
      title="Click to edit logo"
      aria-label={`Edit logo for ${channel.name}`}
    >
      {#if channel.logo}
        <img src={channel.logo} alt={channel.name} class="w-full h-full object-contain" />
      {:else}
        <Camera class="w-3.5 h-3.5 text-muted-foreground" />
      {/if}
    </button>
  {/if}

  <!-- Name (Optional) -->
  {#if showName}
    <div class="flex items-center gap-1.5 min-w-0">
      <button
        type="button"
        onclick={() => oneditname?.(channel)}
        class="text-left font-bold text-foreground hover:text-primary transition-colors cursor-pointer truncate {isExcluded ? 'line-through text-muted-foreground' : ''}"
        title={`Click to edit name: ${channel.name}${isModified ? ' (Rewritten by rules)' : ''}`}
      >
        {channel.name}
      </button>
      {#if isModified}
        <span
          class="w-1.5 h-1.5 rounded-full bg-primary shrink-0"
          title="Metadata transformed by rewrite rules"
          aria-label="Modified by rewrite rules"
        ></span>
      {/if}
    </div>
  {/if}
</div>
