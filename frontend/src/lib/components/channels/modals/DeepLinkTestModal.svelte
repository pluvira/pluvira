<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import { ScannerMappingController } from '../utils/ScannerMappingController.svelte';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let { channel = null, open = $bindable(), onclose, onsaved }: Props = $props();

  const controller = new ScannerMappingController();

  function handleClose() {
    open = false;
    onsaved?.();
    onclose?.();
  }

  $effect(() => {
    if (open && channel) {
      controller.runDeepLinkTest(channel).then(() => {
        onsaved?.();
      });
    }
  });
</script>

<Dialog bind:open title="Deep Stream Link Diagnosis" onclose={handleClose} class="max-w-3xl">
  {#snippet footer()}
    <Button variant="primary" size="sm" onclick={handleClose} class="font-bold touch-btn">Close</Button>
  {/snippet}

  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs font-mono">
      <div class="panel-mono !p-3">
        <span class="text-muted-foreground font-bold text-[10px] uppercase">Target Stream URL:</span>
        <span class="text-primary break-all text-xs">{channel.url}</span>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-background rounded border border-border/30">
        <span class="font-bold text-foreground truncate">{controller.testStatus}</span>
        <Button
          variant="primary"
          size="sm"
          disabled={controller.testing}
          onclick={() => controller.runDeepLinkTest(channel!)}
          class="shrink-0 touch-btn"
        >
          {controller.testing ? 'Testing...' : 'Re-Run Diagnosis'}
        </Button>
      </div>

      <div class="bg-black text-primary p-3 rounded border border-border/30 h-56 md:h-64 overflow-y-auto flex flex-col gap-1 leading-relaxed">
        {#if controller.traceLogs.length === 0}
          <span class="text-muted-foreground italic">Initializing stream diagnosis trace...</span>
        {:else}
          {#each controller.traceLogs as log, i (i)}
            <div class="break-all">{log}</div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</Dialog>
