<script lang="ts">
  import Dialog from '../ui/Dialog.svelte';
  import Badge from '../ui/Badge.svelte';
  import Button from '../ui/Button.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import type { RenderedBlock } from './utils';
  import { Play } from '@lucide/svelte';

  interface Props {
    renderedBlock?: RenderedBlock | null;
    channel?: ChannelItem | null;
    open?: boolean;
    isLive?: boolean;
    onplay?: () => void;
    onclose?: () => void;
  }

  let {
    renderedBlock = null,
    channel = null,
    open = $bindable(),
    isLive = false,
    onplay,
    onclose
  }: Props = $props();

  function handlePlay() {
    open = false;
    onplay?.();
  }
</script>

<Dialog bind:open title={renderedBlock?.program.t || 'Program Details'} {onclose} class="max-w-xl">
  {#snippet footer()}
    <div class="flex items-center justify-between w-full">
      <div>
        {#if isLive && onplay}
          <Button
            variant="primary"
            size="sm"
            onclick={handlePlay}
            class="font-bold touch-btn flex items-center gap-1.5"
            title="Play Live Stream"
          >
            <Play class="w-3.5 h-3.5 fill-current" />
            <span>Play</span>
          </Button>
        {/if}
      </div>
      <Button variant="ghost" size="sm" onclick={() => (open = false)} class="font-bold touch-btn">Close</Button>
    </div>
  {/snippet}

  {#if renderedBlock}
    <div class="flex flex-col gap-4 w-full text-xs">
      <div class="flex items-center gap-3 bg-background p-3 rounded border border-border/30">
        {#if channel?.logo}
          <img src={channel.logo} alt={channel.name} class="w-12 h-8 object-contain bg-black p-0.5 rounded border border-border/30" />
        {/if}
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-foreground text-sm">{channel?.name || 'Channel'}</span>
          <div class="flex items-center gap-2 text-muted-foreground">
            <span>{renderedBlock.timeLabel}</span>
            <Badge variant="muted">{renderedBlock.durationMins} mins</Badge>
          </div>
        </div>
      </div>

      <div class="bg-background p-4 rounded border border-border/30 flex flex-col gap-2 leading-relaxed text-foreground/90">
        <span class="font-bold text-muted-foreground text-[10px] uppercase">Description</span>
        <p class="text-xs break-words">
          {renderedBlock.program.d || 'No description available for this programme.'}
        </p>
      </div>
    </div>
  {/if}
</Dialog>
