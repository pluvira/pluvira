<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Button from '../ui/Button.svelte';
  import { LicenseModal } from '../settings/modals';
  import BulletinDrawer from './BulletinDrawer.svelte';
  import { Menu, Radio, RotateCw, WifiOff, Bell } from '@lucide/svelte';
  import { bulletinStore, unreadBulletinCount } from '$lib/stores/bulletinStore';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { connectionStore } from '$lib/stores/connectionStore';
  import Dialog from '../ui/Dialog.svelte';
  import Badge from '../ui/Badge.svelte';

  interface Props {
    isRunning?: boolean;
    onTriggerUpdate?: (mode: string) => void;
    isPro?: boolean;
    toggleSidebar?: () => void;
    onOpenTerminal?: () => void;
  }

  let {
    isRunning = false,
    isPro = false,
    toggleSidebar,
    onOpenTerminal
  }: Props = $props();

  let showConnectionModal = $state(false);
  let showLicenseModal = $state(false);
  let showBulletins = $state(false);
  let isRetrying = $state(false);
  let unreadCount = $derived($unreadBulletinCount);
  let effectiveIsPro = $derived($licenseStore.isLoaded ? $licenseStore.isPro : isPro);
  let webrtcActive = $derived($licenseStore.isLoaded ? $licenseStore.webrtcActive : false);
  let webrtcStatus = $derived($licenseStore.isLoaded ? $licenseStore.webrtcStatus : 'disabled');
  let isConnected = $derived($connectionStore.isConnected);
  const isDev = Boolean((import.meta as any).env?.DEV);

  onMount(() => {
    connectionStore.startHeartbeat(15000);
    bulletinStore.fetchBulletins();
  });

  onDestroy(() => {
    connectionStore.stopHeartbeat();
  });

  async function handleRetryConnection() {
    isRetrying = true;
    const ok = await connectionStore.checkHeartbeat();
    isRetrying = false;
    if (ok) {
      showConnectionModal = false;
    }
  }
</script>

<header class="surface-header h-12 px-2.5 sm:px-4 flex items-center justify-between sticky top-0 z-40">
  <div class="flex items-center gap-3">
    <button
      type="button"
      onclick={toggleSidebar}
      class="text-muted-foreground hover:text-foreground p-1 rounded-md cursor-pointer transition-colors md:hidden touch-btn"
      aria-label="Toggle Sidebar"
    >
      <Menu class="w-6 h-6" />
    </button>

    <a href="#/" class="flex items-center gap-2 no-underline">
      <img src="favicon.svg" alt="Pluvira Icon" class="max-h-6 w-auto object-contain"/>
      <span class="text-primary text-xl font-extrabold tracking-wider uppercase">Pluvira</span>
    </a>
  </div>

  <div class="flex items-center gap-2 sm:gap-3">
    {#if !isConnected}
      <button
        type="button"
        onclick={() => (showConnectionModal = true)}
        class="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-destructive/20 hover:bg-destructive/30 border border-destructive/40 text-destructive text-xs animate-pulse cursor-pointer transition-colors touch-btn"
        title="Backend connection lost. Click for diagnostics."
        aria-label="Backend offline. Open diagnostics"
      >
        <WifiOff class="w-3.5 h-3.5" />
        <span class="text-[10px] font-bold uppercase hidden sm:inline">Offline</span>
      </button>
    {/if}

    {#if isDev && effectiveIsPro && webrtcActive && webrtcStatus === 'connected'}
      <button
        type="button"
        onclick={() => (showLicenseModal = true)}
        class="surface-card flex items-center gap-1.5 px-2 py-0.5 text-xs cursor-pointer hover:border-primary/50 transition-colors"
        title="WebRTC E2EE Remote Tunnel: Connected & Active - Click for License"
        aria-label="WebRTC E2EE Remote Tunnel Status"
      >
        <Radio class="w-3.5 h-3.5 text-green-400 animate-pulse" />
        <span class="text-[10px] font-bold text-green-400 hidden sm:inline">
          E2EE ONLINE
        </span>
      </button>
    {/if}

    {#if isRunning}
      <button
        type="button"
        onclick={() => { if (onOpenTerminal) onOpenTerminal(); }}
        class="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-primary/20 hover:bg-primary/30 border border-primary/40 text-primary text-xs cursor-pointer transition-colors touch-btn"
        title="Update in progress - Click to view live progress & logs"
        aria-label="View update progress"
      >
        <RotateCw class="w-3.5 h-3.5 animate-spin" />
        <span class="text-[10px] font-bold uppercase hidden sm:inline">Syncing...</span>
      </button>
    {/if}

    <!-- Bulletin Bell Indicator (Always visible: neutral on 0, active badge on > 0) -->
    <button
      type="button"
      onclick={() => (showBulletins = true)}
      class="relative p-1.5 rounded-md text-muted-foreground hover:text-foreground transition-colors cursor-pointer touch-btn"
      title={unreadCount > 0 ? `${unreadCount} unread system notice(s)` : 'System announcements'}
      aria-label="System announcements"
    >
      <Bell class="w-4 h-4 {unreadCount > 0 ? 'text-primary' : 'text-muted-foreground/60'}" />
      {#if unreadCount > 0}
        <span
          class="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[9px] font-extrabold text-primary-foreground animate-pulse"
        >
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      {/if}
    </button>
  </div>
</header>

<LicenseModal bind:open={showLicenseModal} />
<BulletinDrawer bind:open={showBulletins} />

<Dialog
  open={showConnectionModal}
  title="Backend Connection Status"
  onclose={() => (showConnectionModal = false)}
>
  <div class="flex flex-col gap-4 text-sm text-foreground">
    <!-- Status Banner -->
    <div class="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/30">
      <div class="flex items-center gap-2">
        <WifiOff class="w-5 h-5 text-destructive shrink-0" />
        <div>
          <h4 class="font-bold text-destructive">Backend Offline</h4>
          <p class="text-xs text-muted-foreground">The application cannot communicate with the server daemon.</p>
        </div>
      </div>
      <Badge variant="error">FAILED</Badge>
    </div>

    <!-- Error Diagnostic Box -->
    <div class="surface-card p-3 flex flex-col gap-2">
      <span class="text-xs font-bold text-muted-foreground uppercase">Diagnostic Details</span>
      <div class="panel-mono text-xs p-2 rounded flex flex-col gap-1 overflow-x-auto">
        {#if $connectionStore.lastStatusCode !== null}
          <div><span class="text-muted-foreground">Status Code:</span> <span class="text-destructive font-bold">{$connectionStore.lastStatusCode || '0 (No Response)'}</span></div>
        {/if}
        {#if $connectionStore.lastFailedUrl}
          <div><span class="text-muted-foreground">Endpoint:</span> <span class="text-foreground font-mono">{$connectionStore.lastFailedUrl}</span></div>
        {/if}
        <div><span class="text-muted-foreground">Failure:</span> <span class="text-foreground">{$connectionStore.lastErrorMessage || 'Network connection failed'}</span></div>
        <div><span class="text-muted-foreground">Failures Count:</span> <span class="text-foreground">{$connectionStore.consecutiveFailures}</span></div>
      </div>
    </div>

    <!-- Troubleshooting Tips -->
    {#if $connectionStore.troubleshootingTips.length > 0}
      <div class="flex flex-col gap-2">
        <span class="text-xs font-bold text-muted-foreground uppercase">Troubleshooting Tips</span>
        <ul class="flex flex-col gap-1.5 pl-4 list-disc text-xs text-muted-foreground">
          {#each $connectionStore.troubleshootingTips as tip}
            <li>{tip}</li>
          {/each}
        </ul>
      </div>
    {/if}
  </div>

  {#snippet footer()}
    <div class="flex items-center justify-end gap-2 w-full">
      <Button
        variant="secondary"
        size="sm"
        onclick={() => (showConnectionModal = false)}
      >
        Close
      </Button>
      <Button
        variant="primary"
        size="sm"
        disabled={isRetrying}
        onclick={handleRetryConnection}
      >
        <RotateCw class="w-3.5 h-3.5 mr-1.5 {isRetrying ? 'animate-spin' : ''}" />
        {isRetrying ? 'Checking...' : 'Retry Connection'}
      </Button>
    </div>
  {/snippet}
</Dialog>
