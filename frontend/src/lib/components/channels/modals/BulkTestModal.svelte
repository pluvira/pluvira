<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import { ScannerMappingController } from '../utils/ScannerMappingController.svelte';
  import { RotateCw, CheckCircle2, AlertTriangle, Clock, Play, Square } from '@lucide/svelte';

  interface Props {
    channels?: ChannelItem[];
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let { channels = [], open = $bindable(), onclose, onsaved }: Props = $props();

  const controller = new ScannerMappingController();

  $effect(() => {
    if (open && channels.length > 0) {
      controller.initBatch(channels);
    } else {
      controller.cleanupBatch();
    }
  });

  function handleStartBatchTest() {
    controller.startBatchTest(channels).then(() => {
      onsaved?.();
    });
  }

  function handleStopBatchTest() {
    controller.stopScanner();
    onsaved?.();
  }

  function handleClose() {
    controller.cleanupBatch();
    open = false;
    onsaved?.();
    onclose?.();
  }

  function formatTime(sec: number): string {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins}:${s < 10 ? '0' : ''}${s}`;
  }
</script>

<Dialog bind:open title={`Batch Link Test (${channels.length} Channels)`} onclose={handleClose} class="max-w-2xl">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={handleClose} class="touch-btn">Close</Button>
  {/snippet}

  <div class="flex flex-col gap-4 w-full text-xs">
    <!-- Header Controls & Status -->
    <div class="surface-darkest p-3 rounded border border-border/40 flex flex-col gap-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          {#if controller.testing}
            <RotateCw class="w-4 h-4 text-primary animate-spin" />
          {:else if controller.batchProgress.tested > 0}
            <CheckCircle2 class="w-4 h-4 text-primary" />
          {:else}
            <Clock class="w-4 h-4 text-muted-foreground" />
          {/if}
          <span class="font-bold text-foreground text-sm">{controller.testStatus}</span>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <Button variant="primary" size="sm" disabled={controller.testing} onclick={handleStartBatchTest} class="touch-btn flex items-center gap-1">
            <Play class="w-3.5 h-3.5" />
            <span>{controller.testing ? 'Scanning...' : 'START BATCH TEST'}</span>
          </Button>
          <Button variant="danger" size="sm" disabled={!controller.testing} onclick={handleStopBatchTest} class="touch-btn flex items-center gap-1">
            <Square class="w-3.5 h-3.5" />
            <span>STOP</span>
          </Button>
        </div>
      </div>

      <!-- Metrics Badges & Progress Bar -->
      <div class="flex flex-col gap-2 pt-1 border-t border-border/20">
        <div class="flex items-center justify-between flex-wrap gap-2 text-[11px]">
          <div class="flex items-center gap-2 flex-wrap">
            <Badge variant="muted">Total: {controller.batchProgress.total}</Badge>
            <Badge variant="primary">Tested: {controller.batchProgress.tested}</Badge>
            <Badge variant="success">Online: {controller.batchProgress.online}</Badge>
            <Badge variant="error">Offline: {controller.batchProgress.offline}</Badge>
          </div>
          <span class="text-muted-foreground font-mono">Elapsed: {formatTime(controller.elapsedSeconds)}</span>
        </div>

        <div class="w-full bg-background rounded-full h-2 overflow-hidden border border-border/30">
          <div
            class="bg-primary h-full transition-all duration-300"
            style="width: {controller.batchProgress.percent}%"
          ></div>
        </div>
      </div>
    </div>

    <!-- Live Channels Test Progress List -->
    <div class="surface-darkest p-3 rounded border border-border/40 max-h-64 overflow-y-auto flex flex-col gap-1.5">
      <span class="text-muted-foreground font-bold mb-1">Target Channels in Batch:</span>
      {#each controller.batchItems as ch (ch.id)}
        <div class="flex items-center justify-between text-foreground border-b border-border/20 py-1.5 gap-2">
          <div class="flex items-center gap-2 min-w-0">
            {#if ch.testState === 'online'}
              <CheckCircle2 class="w-3.5 h-3.5 text-primary shrink-0" />
            {:else if ch.testState === 'offline'}
              <AlertTriangle class="w-3.5 h-3.5 text-destructive shrink-0" />
            {:else if controller.testing}
              <RotateCw class="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
            {:else}
              <Clock class="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            {/if}
            <span class="font-bold truncate text-xs">{ch.name}</span>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[10px] font-mono text-muted-foreground">{ch.source}</span>
            {#if ch.testState === 'online'}
              <Badge variant="success" class="text-[10px]">OK</Badge>
            {:else if ch.testState === 'offline'}
              <Badge variant="error" class="text-[10px]">KO</Badge>
            {:else if controller.testing}
              <Badge variant="primary" class="text-[10px]">Scanning</Badge>
            {:else}
              <Badge variant="muted" class="text-[10px]">Pending</Badge>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </div>
</Dialog>
