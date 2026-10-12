<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import { AnalyticsCards, HistoryTable } from '../cards';
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';

  interface Props {
    controller: SettingsController;
  }

  let { controller }: Props = $props();
  const confirmController = new ConfirmController();

  let logContainer: HTMLDivElement | null = $state(null);
  let autoScroll = $state(true);

  function handleDeleteRecord(id: string) {
    confirmController.requestConfirm('history_record', () => {
      controller.deleteHistoryRecord(id);
    });
  }

  function handleClearHistory() {
    confirmController.requestConfirm('history_all', () => {
      controller.clearAllHistory();
    });
  }

  $effect(() => {
    if (autoScroll && logContainer && controller.terminalLogs.length > 0) {
      setTimeout(() => {
        if (logContainer) {
          logContainer.scrollTop = logContainer.scrollHeight;
        }
      }, 50);
    }
  });

  onMount(() => {
    controller.loadMetricsData();
    controller.startLogPolling();
  });

  onDestroy(() => {
    controller.stopLogPolling();
  });
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  <AnalyticsCards rawStats={controller.globalStats} licenseDetails={controller.licenseData?.license} />

  <HistoryTable
    history={controller.history}
    ondeleterecord={handleDeleteRecord}
    onclearhistory={handleClearHistory}
  />

  <Card title="System Execution Logs">
    <div class="flex flex-col gap-2 w-full">
      <div class="flex items-center justify-between mb-1">
        <label class="flex items-center gap-2 cursor-pointer text-muted-foreground text-xs">
          <input type="checkbox" bind:checked={autoScroll} class="rounded text-primary" />
          <span>Auto-scroll</span>
        </label>
        <Button variant="ghost" size="sm" onclick={() => controller.terminalLogs = []} class="!py-1 text-xs touch-btn">Clear Logs</Button>
      </div>

      <div
        bind:this={logContainer}
        class="p-3 bg-black text-primary h-64 overflow-y-auto font-mono text-[10px] sm:text-xs flex flex-col gap-0.5 leading-relaxed rounded border border-border/30"
      >
        {#if controller.terminalLogs.length === 0}
          <span class="text-muted-foreground italic">No execution logs in buffer...</span>
        {:else}
          {#each controller.terminalLogs as line, i (i)}
            <div class="break-all">{line}</div>
          {/each}
        {/if}
      </div>
    </div>
  </Card>
</div>
