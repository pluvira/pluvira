<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '../ui/Card.svelte';
  import Badge from '../ui/Badge.svelte';
  import Button from '../ui/Button.svelte';
  import UidBadge from '../ui/UidBadge.svelte';
  import { AboutController } from './AboutController.svelte';
  import {
    Info,
    Shield,
    Radio,
    Cpu,
    BookOpen,
    Copy,
    Check,
    HardDrive,
    Activity
  } from '@lucide/svelte';
  import { licenseStore } from '$lib/stores/licenseStore';

  const controller = new AboutController();

  let isPro = $derived($licenseStore.isPro);
  const isDev = Boolean((import.meta as any).env?.DEV);

  onMount(() => {
    controller.loadVersion();
  });
</script>

<div class="flex flex-col gap-6 w-full select-none text-xs">
  <Card title="About Pluvira">
    <div class="flex flex-col gap-4 w-full">
      <div class="flex items-center justify-between border-b border-border/30 pb-3">
        <div class="flex items-center gap-3">
          <div class="p-2.5 rounded-lg bg-primary/10 border border-primary/30">
            <Radio class="w-6 h-6 text-primary" />
          </div>
          <div class="flex flex-col gap-0.5">
            <div class="flex items-baseline gap-1.5 flex-wrap">
              <span class="text-lg font-extrabold text-foreground tracking-wider uppercase">Pluvira</span>
              <span class="text-xs font-mono font-bold text-muted-foreground">- {controller.formattedVersion}</span>
              {#if controller.gitHash}
                <span class="px-1.5 py-0.5 rounded bg-card border border-border/50 text-primary text-[10px] font-mono">
                  {controller.gitHash}
                </span>
              {/if}
            </div>
            <span class="text-xs text-muted-foreground">Modular Playlist, EPG & Media Management Suite</span>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          {#if controller.proVersion}
            <span class="text-xs font-mono font-bold text-primary">Pro Engine v{controller.proVersion}</span>
          {/if}
          {#if $licenseStore.badgeColor}
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold border"
              style="background-color: {$licenseStore.badgeColor}20; color: {$licenseStore.badgeTextColor || $licenseStore.badgeColor}; border-color: {$licenseStore.badgeColor}60;"
            >
              <span>{$licenseStore.tierDisplayName.toUpperCase()}</span>
            </span>
          {:else if $licenseStore.tier === 'free'}
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold border border-sky-500/40 bg-sky-500/15 text-sky-400"
            >
              <span>{$licenseStore.tierDisplayName.toUpperCase()}</span>
            </span>
          {:else}
              <Badge variant={isPro ? 'success' : 'muted'}>
              {$licenseStore.tierDisplayName.toUpperCase()}
            </Badge>
          {/if}
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="panel-box">
          <div class="flex items-center gap-2 text-foreground font-bold mb-1">
            <Shield class="w-4 h-4 text-primary" />
            <span>License & Architecture</span>
          </div>
          <p class="text-muted-foreground leading-relaxed">
            Personal Free Tier operating under BSL 1.1 with high-performance native Rust IPC extensions for Pro subscriptions (pluvira.com).
          </p>
        </div>

        <div class="panel-box">
          <div class="flex items-center gap-2 text-foreground font-bold mb-1">
            <Cpu class="w-4 h-4 text-primary" />
            <span>Storage & Memory</span>
          </div>
          <p class="text-muted-foreground leading-relaxed">
            Optimized for RAM Disk (tmpfs) zero-I/O caching, PID-isolated atomic file writes, and SQLite WAL database storage.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3 border-t border-border/30 pt-3 flex-wrap">
        <a
          href="#/settings?tab=general&sub=diagnostics"
          class="btn-outline px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 no-underline"
        >
          <Info class="w-3.5 h-3.5" />
          <span>System Diagnostics</span>
        </a>
        <a
          href="#/channels"
          class="btn-primary px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 no-underline"
        >
          <BookOpen class="w-3.5 h-3.5" />
          <span>Go to Channels Hub</span>
        </a>
      </div>
    </div>
  </Card>

  <!-- Technical Environment Card -->
  <Card title="Technical Environment">
    <div class="flex flex-col gap-4 w-full">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <!-- 1. Runtimes & Engine -->
        <div class="panel-box flex flex-col gap-1.5 !p-2.5">
          <div class="flex items-center gap-1.5 text-foreground font-bold border-b border-border/30 pb-1">
            <Cpu class="size-3.5 text-primary" />
            <span class="text-[10px] uppercase">Runtimes & Engine</span>
          </div>
          <div class="flex flex-col gap-1 text-[11px] font-mono">
            <div><span class="text-muted-foreground font-sans">Core:</span> {controller.formattedVersion}</div>
            <div><span class="text-muted-foreground font-sans">Commit:</span> {controller.gitHash || 'release'}</div>
            <div>
              <span class="text-muted-foreground font-sans">Pro Engine:</span>
              {#if controller.proVersion}
                <span class="text-primary font-bold">v{controller.proVersion}</span>
              {:else if controller.isPro}
                <span class="text-primary font-bold">{controller.formattedVersion}</span>
              {:else}
                <span class="text-muted-foreground/60 italic font-sans">Core (No Pro)</span>
              {/if}
            </div>
            <div><span class="text-muted-foreground font-sans">Edition:</span> {controller.effectiveEdition.includes('EDITION') ? controller.effectiveEdition : `${controller.effectiveEdition} EDITION`}</div>
            {#if controller.isPro && controller.licenseExpiryDate}
              <div>
                <span class="text-muted-foreground font-sans">Expires:</span>
                <span class="text-foreground font-bold">{controller.licenseExpiryDate}</span>
                {#if controller.licenseDaysRemaining !== null}
                  <span class="text-muted-foreground text-[10px]">({controller.licenseDaysRemaining}d left)</span>
                {/if}
              </div>
            {/if}
          </div>
        </div>

        <!-- 2. Storage & Database -->
        <div class="panel-box flex flex-col gap-1.5 !p-2.5">
          <div class="flex items-center gap-1.5 text-foreground font-bold border-b border-border/30 pb-1">
            <HardDrive class="size-3.5 text-primary" />
            <span class="text-[10px] uppercase">Storage & Database</span>
          </div>
          <div class="flex flex-col gap-1 text-[11px] font-mono">
            <div class="truncate" title={controller.environment?.temp_dir}><span class="text-muted-foreground font-sans">RAM Disk:</span> {controller.environment?.temp_dir || '/dev/shm/pluvira'}</div>
            <div class="truncate" title={controller.environment?.data_dir}><span class="text-muted-foreground font-sans">Data Dir:</span> {controller.environment?.data_dir || 'data/'}</div>
            <div class="truncate" title={controller.environment?.config_path}><span class="text-muted-foreground font-sans">Config:</span> {controller.environment?.config_path || 'config/config.yaml'}</div>
          </div>
        </div>

        <!-- 3. System Health & Identity -->
        <div class="panel-box flex flex-col gap-1.5 !p-2.5">
          <div class="flex items-center gap-1.5 text-foreground font-bold border-b border-border/30 pb-1">
            <Activity class="size-3.5 text-primary" />
            <span class="text-[10px] uppercase">System & Identity</span>
          </div>
          <div class="flex flex-col gap-1 text-[11px]">
            <div><span class="text-muted-foreground">Task Runner:</span> <span class="font-mono font-bold">{controller.systemStatus?.status || 'Idle'}</span></div>
            {#if isDev}
              <div><span class="text-muted-foreground">WebRTC Tunnel:</span> <span class="font-mono">{controller.webrtcStatus}</span></div>
            {/if}
            <div class="flex items-center gap-1.5">
              <span class="text-muted-foreground">HWID:</span>
              {#if controller.deviceHash}
                <button
                  type="button"
                  onclick={() => controller.copyHwid()}
                  class="font-mono text-muted-foreground hover:text-foreground font-bold flex items-center gap-1 px-1.5 py-0.5 rounded bg-card border border-border/40 hover:border-primary/40 transition-colors"
                  title="Click to copy full HWID ({controller.deviceHash})"
                >
                  <span>{controller.shortDeviceHash}</span>
                  {#if controller.hwidCopied}
                    <Check class="size-3 text-primary" />
                  {:else}
                    <Copy class="size-3 text-muted-foreground" />
                  {/if}
                </button>
              {:else}
                <span class="text-muted-foreground/60 italic font-mono">----</span>
              {/if}
            </div>
            <div class="flex items-center gap-1 mt-0.5">
              <span class="text-muted-foreground">UID:</span>
              {#if controller.cloudAccount?.uid || controller.systemStatus?.crockford_id}
                <UidBadge uid={controller.cloudAccount?.formatted_id || controller.cloudAccount?.uid || controller.systemStatus?.crockford_id} size="sm" />
              {:else}
                <span class="text-muted-foreground/60 italic font-mono">Unregistered</span>
              {/if}
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-start border-t border-border/30 pt-3">
        <Button
          variant="outline"
          size="sm"
          onclick={() => controller.copyDiagnosticsReport()}
          class="flex items-center gap-1.5 text-xs font-bold touch-btn"
          title="Copy system diagnostics to clipboard for bug reports"
        >
          {#if controller.copied}
            <Check class="size-3.5 text-primary" />
            <span class="text-primary">Copied!</span>
          {:else}
            <Copy class="size-3.5 text-muted-foreground" />
            <span>Copy Report</span>
          {/if}
        </Button>
      </div>
    </div>
  </Card>
</div>
