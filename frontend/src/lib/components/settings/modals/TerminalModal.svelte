<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import { TerminalController } from '../utils/TerminalController.svelte';
  import { UpdateProgressController } from '../utils/UpdateProgressController.svelte';
  import {
    CheckCircle2,
    AlertTriangle,
    RotateCw,
    ChevronDown,
    ChevronUp,
    Terminal,
    Clock
  } from '@lucide/svelte';

  interface Props {
    open?: boolean;
    title?: string;
    onclose?: () => void;
  }

  let { open = $bindable(), title = 'System Update Progress', onclose }: Props = $props();

  let logContainer: HTMLDivElement | null = $state(null);
  let autoScroll = $state(true);
  let showRawConsole = $state(false);

  const controller = new TerminalController();
  const progressController = new UpdateProgressController();

  function clearLogs() {
    progressController.clearLogs();
  }

  function handleStop() {
    controller.stopPolling();
    progressController.stopMonitoring();
    open = false;
    if (onclose) onclose();
  }

  $effect(() => {
    if (open) {
      progressController.startMonitoring(true);
    } else {
      controller.stopPolling();
      progressController.stopMonitoring();
    }
    return () => {
      controller.stopPolling();
      progressController.stopMonitoring();
    };
  });

  $effect(() => {
    if (autoScroll && logContainer && progressController.rawLogs.length > 0) {
      setTimeout(() => {
        if (logContainer) {
          logContainer.scrollTop = logContainer.scrollHeight;
        }
      }, 50);
    }
  });

  let summary = $derived(progressController.progress.summary);
  function formatEpgStats(epg: { channels?: number; programmes?: number }): string {
    const parts: string[] = [];
    if (epg.channels && epg.channels > 0) {
      parts.push(`${epg.channels} channels`);
    }
    if (epg.programmes && epg.programmes > 0) {
      const progStr = epg.programmes >= 1000
        ? `${(epg.programmes / 1000).toFixed(1)}k prog`
        : `${epg.programmes} prog`;
      parts.push(progStr);
    }
    return parts.length > 0 ? `(${parts.join(', ')})` : '';
  }

  let isCompletedSuccess = $derived(
    !progressController.isRunning && summary?.status === 'success'
  );
  let isFailed = $derived(
    !progressController.isRunning && summary?.status === 'failed'
  );

  let rewritesPhase = $derived(
    progressController.progress.phases.rewrites || { title: 'Metadata Cascading Rewrites', status: 'pending' }
  );
  let dbCachePhase = $derived(
    progressController.progress.phases.database_cache || { title: 'Data Persistence & Cache Refresh', status: 'pending' }
  );
</script>

<Dialog bind:open {title} {onclose} class="max-w-2xl">
  <div class="flex flex-col gap-4 w-full text-foreground">
    <!-- Top HUD Status Banner -->
    <div class="flex items-center justify-between p-3 rounded-lg bg-card border border-border/40">
      <div class="flex items-center gap-2.5">
        {#if progressController.isRunning}
          <RotateCw class="w-5 h-5 text-primary animate-spin" />
          <div>
            <h4 class="font-bold text-foreground text-sm">Update in progress...</h4>
            <p class="text-xs text-muted-foreground">Downloading playlists, processing metadata and indexing</p>
          </div>
        {:else if isCompletedSuccess}
          <CheckCircle2 class="w-5 h-5 text-primary" />
          <div>
            <h4 class="font-bold text-primary text-sm">Update completed successfully</h4>
            <p class="text-xs text-muted-foreground">All channels and EPG guides have been synchronized</p>
          </div>
        {:else if isFailed}
          <AlertTriangle class="w-5 h-5 text-destructive" />
          <div>
            <h4 class="font-bold text-destructive text-sm">Update failed or interrupted</h4>
            <p class="text-xs text-muted-foreground">{summary?.error_message || 'An error occurred during execution.'}</p>
          </div>
        {:else}
          <Clock class="w-5 h-5 text-muted-foreground" />
          <div>
            <h4 class="font-bold text-foreground text-sm">Ready for update</h4>
            <p class="text-xs text-muted-foreground">Waiting for process start</p>
          </div>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs font-mono px-2 py-1 rounded bg-background border border-border/40 text-muted-foreground">
          {progressController.elapsedSeconds}s
        </span>
        {#if progressController.isRunning}
          <Button variant="danger" size="sm" onclick={handleStop} class="!py-1 text-xs font-bold touch-btn">STOP</Button>
        {/if}
      </div>
    </div>

    <!-- Completion Metrics Summary Card -->
    {#if isCompletedSuccess && summary}
      <div class="p-3.5 rounded-lg bg-primary/10 border border-primary/30 flex flex-col gap-2">
        <div class="flex items-center gap-2 text-primary text-xs font-bold uppercase tracking-wider">
          <CheckCircle2 class="w-4 h-4" /> Update Results
        </div>
        <div class="grid grid-cols-3 gap-2 text-center text-xs">
          <div class="p-2 rounded bg-card/60 border border-border/20">
            <span class="text-muted-foreground block text-[11px]">Total Channels</span>
            <span class="text-foreground font-bold text-sm">{summary.total_channels}</span>
          </div>
          <div class="p-2 rounded bg-card/60 border border-border/20">
            <span class="text-muted-foreground block text-[11px]">EPG Mapped</span>
            <span class="text-primary font-bold text-sm">{summary.matched_channels}</span>
          </div>
          <div class="p-2 rounded bg-card/60 border border-border/20">
            <span class="text-muted-foreground block text-[11px]">Total Duration</span>
            <span class="text-foreground font-bold text-sm">{summary.duration}s</span>
          </div>
        </div>
      </div>
    {/if}

    <!-- Granular Stepper: M3U, EPG, Rewrites, DB Storage -->
    <div class="surface-card p-3.5 flex flex-col gap-3">
      <!-- 1. M3U Sources Downloads -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Download M3U Sources</span>
        {#if progressController.m3uSources.length === 0}
          <div class="text-xs text-muted-foreground italic pl-2">No active M3U sources configured.</div>
        {:else}
          <div class="flex flex-col gap-1 pl-1">
            {#each progressController.m3uSources as src (src.name)}
              <div class="flex items-center justify-between text-xs py-0.5">
                <div class="flex items-center gap-2 truncate">
                  {#if src.status === 'running'}
                    <RotateCw class="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
                    <span class="text-foreground">downloading from '{src.name}' ...</span>
                  {:else if src.status === 'success'}
                    <span class="w-2 h-2 rounded-full bg-primary shrink-0"></span>
                    <span class="text-foreground">downloading from '{src.name}' ...</span>
                  {:else if src.status === 'failed'}
                    <span class="w-2 h-2 rounded-full bg-destructive shrink-0"></span>
                    <span class="text-destructive font-medium">downloading from '{src.name}' ...</span>
                  {:else if src.status === 'skipped'}
                    <span class="w-2 h-2 rounded-full bg-muted-foreground/40 shrink-0"></span>
                    <span class="text-muted-foreground truncate">'{src.name}' ({src.reason === 'disabled' ? 'disabled' : 'not in mode'})</span>
                  {:else}
                    <span class="w-2 h-2 rounded-full bg-muted-foreground/30 shrink-0"></span>
                    <span class="text-muted-foreground">waiting for '{src.name}'</span>
                  {/if}
                </div>

                <div class="shrink-0 ml-2">
                  {#if src.status === 'success'}
                    <span class="text-primary font-bold font-mono">OK {src.channels ? `(${src.channels} channels)` : ''}</span>
                  {:else if src.status === 'failed'}
                    <span class="text-destructive font-bold font-mono">KO</span>
                  {:else if src.status === 'running'}
                    <span class="text-primary font-mono animate-pulse">...</span>
                  {:else if src.status === 'skipped'}
                    <span class="text-muted-foreground text-[11px] uppercase font-mono">Skipped</span>
                  {:else}
                    <span class="text-muted-foreground text-[11px]">pending</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <div class="border-t border-border/20"></div>

      <!-- 2. EPG Sources Downloads -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Download EPG Guides</span>
        {#if progressController.epgSources.length === 0}
          <div class="text-xs text-muted-foreground italic pl-2">No active EPG guides configured.</div>
        {:else}
          <div class="flex flex-col gap-1 pl-1">
            {#each progressController.epgSources as epg (epg.name)}
              <div class="flex items-center justify-between text-xs py-0.5">
                <div class="flex items-center gap-2 truncate">
                  {#if epg.status === 'running'}
                    <RotateCw class="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
                    <span class="text-foreground">downloading from '{epg.name}' ...</span>
                  {:else if epg.status === 'success'}
                    <span class="w-2 h-2 rounded-full bg-primary shrink-0"></span>
                    <span class="text-foreground">downloading from '{epg.name}' ...</span>
                  {:else if epg.status === 'failed'}
                    <span class="w-2 h-2 rounded-full bg-destructive shrink-0"></span>
                    <span class="text-destructive font-medium">downloading from '{epg.name}' ...</span>
                  {:else if epg.status === 'skipped'}
                    <span class="w-2 h-2 rounded-full bg-muted-foreground/40 shrink-0"></span>
                    <span class="text-muted-foreground truncate">'{epg.name}' ({epg.reason === 'disabled' ? 'disabled' : 'not in mode'})</span>
                  {:else}
                    <span class="w-2 h-2 rounded-full bg-muted-foreground/30 shrink-0"></span>
                    <span class="text-muted-foreground">waiting for '{epg.name}'</span>
                  {/if}
                </div>

                <div class="shrink-0 ml-2">
                  {#if epg.status === 'success'}
                    <span class="text-primary font-bold font-mono">OK {formatEpgStats(epg)}</span>
                  {:else if epg.status === 'failed'}
                    <span class="text-destructive font-bold font-mono">KO</span>
                  {:else if epg.status === 'running'}
                    <span class="text-primary font-mono animate-pulse">...</span>
                  {:else if epg.status === 'skipped'}
                    <span class="text-muted-foreground text-[11px] uppercase font-mono">Skipped</span>
                  {:else}
                    <span class="text-muted-foreground text-[11px]">pending</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <div class="border-t border-border/20"></div>

      <!-- 3. Metadata Cascading Rewrites Phase -->
      <div class="flex items-center justify-between text-xs py-0.5 pl-1">
        <div class="flex items-center gap-2">
          {#if rewritesPhase.status === 'running'}
            <RotateCw class="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
            <span class="text-foreground">Metadata Cascading Rewrites ...</span>
          {:else if rewritesPhase.status === 'success'}
            <span class="w-2 h-2 rounded-full bg-primary shrink-0"></span>
            <span class="text-foreground">Metadata Cascading Rewrites ...</span>
          {:else if rewritesPhase.status === 'failed'}
            <span class="w-2 h-2 rounded-full bg-destructive shrink-0"></span>
            <span class="text-destructive font-medium">Metadata Cascading Rewrites ...</span>
          {:else}
            <span class="w-2 h-2 rounded-full bg-muted-foreground/30 shrink-0"></span>
            <span class="text-muted-foreground">Metadata Cascading Rewrites</span>
          {/if}
        </div>

        <div class="shrink-0 ml-2">
          {#if rewritesPhase.status === 'success'}
            <span class="text-primary font-bold font-mono">OK</span>
          {:else if rewritesPhase.status === 'failed'}
            <span class="text-destructive font-bold font-mono">KO</span>
          {:else if rewritesPhase.status === 'running'}
            <span class="text-primary font-mono animate-pulse">...</span>
          {:else}
            <span class="text-muted-foreground text-[11px]">pending</span>
          {/if}
        </div>
      </div>

      <!-- 4. Database Storage & Cache Refresh Phase -->
      <div class="flex items-center justify-between text-xs py-0.5 pl-1">
        <div class="flex items-center gap-2">
          {#if dbCachePhase.status === 'running'}
            <RotateCw class="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
            <span class="text-foreground">Data Persistence & Cache Refresh ...</span>
          {:else if dbCachePhase.status === 'success'}
            <span class="w-2 h-2 rounded-full bg-primary shrink-0"></span>
            <span class="text-foreground">Data Persistence & Cache Refresh ...</span>
          {:else if dbCachePhase.status === 'failed'}
            <span class="w-2 h-2 rounded-full bg-destructive shrink-0"></span>
            <span class="text-destructive font-medium">Data Persistence & Cache Refresh ...</span>
          {:else}
            <span class="w-2 h-2 rounded-full bg-muted-foreground/30 shrink-0"></span>
            <span class="text-muted-foreground">Data Persistence & Cache Refresh</span>
          {/if}
        </div>

        <div class="shrink-0 ml-2">
          {#if dbCachePhase.status === 'success'}
            <span class="text-primary font-bold font-mono">OK</span>
          {:else if dbCachePhase.status === 'failed'}
            <span class="text-destructive font-bold font-mono">KO</span>
          {:else if dbCachePhase.status === 'running'}
            <span class="text-primary font-mono animate-pulse">...</span>
          {:else}
            <span class="text-muted-foreground text-[11px]">pending</span>
          {/if}
        </div>
      </div>
    </div>

    <!-- Collapsible Raw Terminal Output -->
    <div class="flex flex-col gap-2">
      <button
        type="button"
        onclick={() => (showRawConsole = !showRawConsole)}
        class="flex items-center justify-between text-xs text-muted-foreground hover:text-foreground p-2 rounded bg-card/40 border border-border/30 cursor-pointer touch-btn"
      >
        <span class="flex items-center gap-2 font-bold">
          <Terminal class="w-3.5 h-3.5 text-primary" />
          {showRawConsole ? 'Hide Raw Console Logs' : 'Show Raw Console Logs'} ({progressController.formattedLogs.length})
        </span>
        {#if showRawConsole}
          <ChevronUp class="w-4 h-4" />
        {:else}
          <ChevronDown class="w-4 h-4" />
        {/if}
      </button>

      {#if showRawConsole}
        <div class="flex flex-col gap-2 p-2 rounded bg-card/60 border border-border/40">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-1">
              <span class="text-muted-foreground text-[11px]">Filter:</span>
              <button
                type="button"
                onclick={() => progressController.setLogFilter('all')}
                class="px-2 py-0.5 rounded text-[11px] font-bold {progressController.logFilter === 'all' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}"
              >
                All
              </button>
              <button
                type="button"
                onclick={() => progressController.setLogFilter('errors')}
                class="px-2 py-0.5 rounded text-[11px] font-bold {progressController.logFilter === 'errors' ? 'bg-destructive text-destructive-foreground' : 'text-muted-foreground hover:text-foreground'}"
              >
                Errors Only
              </button>
              <button
                type="button"
                onclick={() => progressController.setLogFilter('warnings')}
                class="px-2 py-0.5 rounded text-[11px] font-bold {progressController.logFilter === 'warnings' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'}"
              >
                Warnings & Errors
              </button>
            </div>

            <div class="flex items-center gap-2">
              <label class="flex items-center gap-1.5 cursor-pointer text-muted-foreground text-[11px]">
                <input type="checkbox" bind:checked={autoScroll} class="rounded text-primary" />
                <span>Auto-scroll</span>
              </label>
              <Button variant="ghost" size="sm" onclick={clearLogs} class="!py-0.5 !px-2 text-xs touch-btn">Clear</Button>
            </div>
          </div>

          <div
            bind:this={logContainer}
            class="p-2.5 bg-black text-xs font-mono h-48 overflow-y-auto flex flex-col gap-0.5 rounded border border-border/30"
          >
            {#if progressController.formattedLogs.length === 0}
              <span class="text-muted-foreground italic text-center py-4">No execution logs in buffer...</span>
            {:else}
              {#each progressController.formattedLogs as logItem (logItem.id)}
                <div class="break-all {logItem.level === 'error' ? 'text-destructive font-bold' : logItem.level === 'warning' ? 'text-primary' : logItem.level === 'debug' ? 'text-muted-foreground/60' : 'text-foreground'}">
                  {logItem.raw}
                </div>
              {/each}
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>
</Dialog>
