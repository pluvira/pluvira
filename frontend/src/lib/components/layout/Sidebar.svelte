<script lang="ts">
  import { SidebarController } from './SidebarController.svelte';
  import Badge from '../ui/Badge.svelte';
  import Button from '../ui/Button.svelte';
  import LicenseStatusBadge from '../ui/LicenseStatusBadge.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { playlistStore } from '$lib/stores/playlistStore';
  import { unreadBulletinCount } from '$lib/stores/bulletinStore';
  import type { EditionType, LicenseDetails } from '$lib/api/types';
  import { LicenseModal } from '../settings/modals';
  import BulletinDrawer from './BulletinDrawer.svelte';
  import {
    Tv,
    Settings,
    LogOut,
    Menu,
    ChevronLeft,
    Radio,
    Info,
    Sparkles,
    Search,
    RotateCw,
    Layers,
    Calendar,
    ListMusic,
    Bell,
    X
  } from '@lucide/svelte';

  interface Props {
    currentPath?: string;
    isOpen?: boolean;
    isCollapsed?: boolean;
    isRunning?: boolean;
    authEnabled?: boolean;
    isPro?: boolean;
    edition?: EditionType;
    licenseDetails?: LicenseDetails | null;
    onlogout?: () => void; onTriggerUpdate?: (mode: string) => void; onOpenTerminal?: () => void;
  }

  const sidebarController = new SidebarController();

  let {
    currentPath = '#/live',
    isOpen = $bindable(),
    isCollapsed = $bindable(),
    isRunning = false,
    authEnabled = true,
    isPro = false,
    edition = 'core',
    licenseDetails = null,
    onlogout, onTriggerUpdate, onOpenTerminal
  }: Props = $props();

  let effectiveLicense = $derived($licenseStore.isLoaded ? $licenseStore.licenseDetails : licenseDetails);
  let effectiveEdition = $derived($licenseStore.isLoaded ? $licenseStore.edition : edition);
  let effectiveIsPro = $derived($licenseStore.isLoaded ? $licenseStore.isPro : isPro);
  let isRail = $derived(Boolean(isCollapsed ?? sidebarController.isCollapsed) && !isOpen);
  let activePlaylistName = $derived($playlistStore.playlists.find((p) => p.id === $playlistStore.activePlaylistId)?.name || 'My List');
  let unreadCount = $derived($unreadBulletinCount);

  function toggleCollapse() { sidebarController.toggleCollapse(); isCollapsed = sidebarController.isCollapsed; }

  const primaryNavItems = [
    { path: '#/live', label: 'Live TV', icon: Radio },
    { path: '#/search', label: 'Search', icon: Search },
    { path: '#/channels', label: 'Channels', icon: Tv }
  ];

  const systemNavItems = [
    { path: '#/settings', label: 'Config', icon: Settings },
    { path: '#/about', label: 'About', icon: Info }
  ];
</script>

{#if isOpen}
  <div
    role="button"
    tabindex="0"
    onclick={() => { isOpen = false; }}
    onkeydown={(e) => { if (e.key === 'Escape') isOpen = false; }}
    class="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden cursor-pointer"
    aria-label="Close sidebar overlay"
  ></div>
{/if}

<aside
  class="bg-card border-r border-border/30 shrink-0 flex flex-col transition-all duration-fast select-none {isOpen ? 'fixed inset-y-0 left-0 z-50 h-screen shadow-2xl' : 'hidden md:flex md:static h-[calc(100vh-3rem)]'} {isRail ? 'w-16 min-w-16 max-w-16' : 'w-52 min-w-52 max-w-52'}"
>
  <!-- Mobile Drawer Header -->
  <div class="p-3 border-b border-border/30 flex items-center justify-between md:hidden">
    <span class="text-primary text-xl font-extrabold tracking-wider uppercase">Pluvira</span>
    <button
      type="button"
      onclick={() => { isOpen = false; }}
      class="text-muted-foreground hover:text-foreground p-1 rounded-md cursor-pointer touch-btn"
      aria-label="Close sidebar"
    >
      <X class="w-5 h-5" />
    </button>
  </div>

  <!-- Top Collapse Button in Desktop Mode -->
  <div class="p-2 border-b border-border/30 hidden md:flex items-center {isRail ? 'justify-center' : 'justify-end'}">
    <button
      type="button"
      onclick={toggleCollapse}
      class="text-muted-foreground hover:text-foreground p-1.5 rounded cursor-pointer transition-colors text-xs font-bold flex items-center justify-center hover:bg-background"
      title={isRail ? 'Expand sidebar' : 'Collapse sidebar to icons'}
      aria-label="Toggle sidebar collapse"
    >
      {#if isRail}
        <Menu class="w-5 h-5" />
      {:else}
        <ChevronLeft class="w-5 h-5" />
      {/if}
    </button>
  </div>

  <nav class="p-2 flex-1 min-h-0 flex flex-col justify-between overflow-y-auto">
    <div class="flex flex-col gap-1">
      <!-- Active Curated Playlist Selector -->
      {#if !isRail}
        <div class="mb-1 p-2 rounded-md bg-background/50 border border-border/30 flex flex-col gap-1.5">
          <div class="flex items-center justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            <span class="flex items-center gap-1.5">
              <ListMusic class="w-3.5 h-3.5 text-primary shrink-0" />
              Playlist
            </span>
            {#if effectiveIsPro && $playlistStore.playlists.length > 1}
              <span class="text-[9px] px-1 py-0.2 bg-primary/20 text-primary rounded font-mono">
                {$playlistStore.playlists.length}
              </span>
            {/if}
          </div>
          {#if effectiveIsPro && $playlistStore.playlists.length > 1}
            <select
              value={$playlistStore.activePlaylistId}
              onchange={(e) => sidebarController.handlePlaylistChange((e.target as HTMLSelectElement).value)}
              class="bg-card text-foreground text-xs font-bold border border-border/40 px-2 py-1 rounded focus:outline-none cursor-pointer w-full"
              title="Switch active curated playlist"
              aria-label="Active curated playlist"
            >
              {#each $playlistStore.playlists as pl (pl.id)}
                <option value={pl.id} class="bg-card text-foreground">{pl.name}</option>
              {/each}
            </select>
          {:else}
            <div class="text-xs font-bold text-foreground/90 truncate px-1" title="Active Curated Playlist">
              {activePlaylistName}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Primary Media Navigation -->
      {#each primaryNavItems as item (item.path)}
        {@const isActive = currentPath.startsWith(item.path)}
        {@const IconComponent = item.icon}
        <a
          href={item.path}
          title={item.label}
          onclick={() => { isOpen = false; }}
          class="flex items-center gap-3 px-3 py-2 rounded-md font-bold text-sm transition-colors decoration-none {isRail ? 'justify-center !px-0' : ''} {isActive ? 'bg-primary text-primary-foreground' : 'text-foreground/80 hover:bg-background hover:text-foreground'}"
        >
          <IconComponent class="w-5 h-5 flex-shrink-0" />
          {#if !isRail}
            <span class="truncate">{item.label}</span>
          {/if}
        </a>
      {/each}

      <!-- Divider between Channels and Config -->
      <div class="my-2 border-t border-border/30"></div>

      <!-- System Navigation (Config & About) -->
      {#each systemNavItems as item (item.path)}
        {@const isActive = currentPath.startsWith(item.path)}
        {@const IconComponent = item.icon}
        <a
          href={item.path}
          title={item.label}
          onclick={() => { isOpen = false; }}
          class="flex items-center gap-3 px-3 py-2 rounded-md font-bold text-sm transition-colors decoration-none {isRail ? 'justify-center !px-0' : ''} {isActive ? 'bg-primary text-primary-foreground' : 'text-foreground/80 hover:bg-background hover:text-foreground'}"
        >
          <IconComponent class="w-5 h-5 flex-shrink-0" />
          {#if !isRail}
            <span class="truncate">{item.label}</span>
          {/if}
        </a>
      {/each}

      <!-- Edition Badge & Upgrade CTA directly under About with separator -->
      <div class="my-2 border-t border-border/30"></div>
      <div class="flex flex-col gap-1.5 px-1 py-1 {isRail ? 'items-center px-0' : ''}">
        <div class="flex items-center {isRail ? 'justify-center' : 'justify-between gap-1'}">
          {#if effectiveLicense}
            {#if effectiveLicense.license_status === 'valid'}
              <button
                type="button"
                onclick={() => sidebarController.openLicenseModal()}
                class="cursor-pointer bg-transparent border-0 p-0 text-left"
                title="{$licenseStore.tierDisplayName} Active"
              >
                <LicenseStatusBadge
                  status="valid"
                  isPro={effectiveIsPro}
                  tier={$licenseStore.tier}
                  displayName={$licenseStore.tierDisplayName}
                  compactName={$licenseStore.compactName}
                  compact={isRail}
                  badgeIcon={$licenseStore.badgeIcon}
                  badgeColor={$licenseStore.badgeColor}
                  badgeTextColor={$licenseStore.badgeTextColor}
                />
              </button>
            {:else if effectiveLicense.license_status === 'grace_period'}
              <button
                type="button"
                onclick={() => sidebarController.openLicenseModal()}
                class="cursor-pointer"
                title="Pluvira is currently disconnected from the internet. Pro features remain active locally for up to 48 hours. Reconnect to restore remote WebRTC access and telemetry sync."
              >
                <Badge variant="warning">
                  {isRail ? 'OFF' : 'OFFLINE (PRO)'}
                </Badge>
              </button>
            {:else if effectiveLicense.license_status === 'expiring_soon'}
              <button
                type="button"
                onclick={() => sidebarController.openLicenseModal()}
                class="cursor-pointer"
                title={`License expires in ${effectiveLicense.days_remaining ?? 0} days - Click to renew`}
              >
                <Badge variant="warning">
                  {isRail ? 'EXP' : `${$licenseStore.tierDisplayName} (${effectiveLicense.days_remaining ?? 0}d)`}
                </Badge>
              </button>
            {:else if effectiveLicense.license_status === 'expired' || effectiveLicense.error_code === 'LICENSE_EXPIRED'}
              <button
                type="button"
                onclick={() => sidebarController.openLicenseModal()}
                class="cursor-pointer"
                title="License Expired - Click to renew"
              >
                <Badge variant="error">
                  {isRail ? 'EXP' : 'EXPIRED'}
                </Badge>
              </button>
            {:else if $licenseStore.tier === 'free'}
              <LicenseStatusBadge
                status="valid"
                tier="free"
                displayName={$licenseStore.tierDisplayName}
                compactName={$licenseStore.compactName}
                compact={isRail}
                badgeIcon={$licenseStore.badgeIcon}
                badgeColor={$licenseStore.badgeColor}
                badgeTextColor={$licenseStore.badgeTextColor}
              />
            {:else}
              <Badge variant="muted">CORE</Badge>
            {/if}
          {:else if effectiveIsPro}
            <LicenseStatusBadge
              status="valid"
              isPro={true}
              tier={$licenseStore.tier}
              displayName={$licenseStore.tierDisplayName}
              compactName={$licenseStore.compactName}
              compact={isRail}
              badgeIcon={$licenseStore.badgeIcon}
              badgeColor={$licenseStore.badgeColor}
              badgeTextColor={$licenseStore.badgeTextColor}
            />
          {:else if $licenseStore.tier === 'free'}
            <LicenseStatusBadge
              status="valid"
              tier="free"
              displayName={$licenseStore.tierDisplayName}
              compactName={$licenseStore.compactName}
              compact={isRail}
              badgeIcon={$licenseStore.badgeIcon}
              badgeColor={$licenseStore.badgeColor}
              badgeTextColor={$licenseStore.badgeTextColor}
            />
          {:else}
            <Badge variant="muted">CORE</Badge>
          {/if}

          {#if !isRail && isRunning}
            <button
              type="button"
              onclick={() => { if (onOpenTerminal) onOpenTerminal(); }}
              class="flex items-center gap-1.5 text-xs cursor-pointer hover:opacity-80 transition-opacity"
              title="Update in progress - Click to view live progress & logs"
            >
              <span class="inline-block w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span class="text-[10px] font-bold text-primary uppercase">RUNNING</span>
            </button>
          {/if}
        </div>

        {#if !effectiveIsPro || effectiveEdition === 'core' || (effectiveLicense && (effectiveLicense.license_status === 'unlicensed' || effectiveLicense.license_status === 'expired' || effectiveLicense.error_code === 'LICENSE_EXPIRED'))}
          <Button
            variant="outline"
            size="sm"
            onclick={() => sidebarController.openLicenseModal()}
            class="!py-1 !px-2 text-xs font-bold text-primary border-primary/50 hover:bg-primary/10 flex items-center justify-center gap-1 w-full {isRail ? '!px-1' : ''}"
            title="Upgrade to Pro Edition"
          >
            <Sparkles class="w-3.5 h-3.5 text-primary shrink-0" />
            {#if !isRail}
              <span>UPGRADE</span>
            {/if}
          </Button>
        {/if}
      </div>
    </div>

    <!-- Bottom Quick Actions Cluster -->
    <div class="mt-auto shrink-0 flex flex-col gap-1.5 pt-2 border-t border-border/30">
      <!-- Sync Catalog Trigger with Popover Menu -->
      <div class="relative">
        <button
          type="button"
          onclick={() => {
            if (isRunning && onOpenTerminal) {
              onOpenTerminal();
            } else {
              sidebarController.toggleSyncMenu();
            }
          }}
          class="flex items-center gap-3 px-3 py-2 rounded-md font-bold text-sm text-foreground/80 hover:bg-background hover:text-foreground transition-colors w-full cursor-pointer touch-btn text-left justify-start {isRail ? '!justify-center !px-0' : ''}"
          title="Sync Catalog & Update Feeds"
          aria-label="Sync Catalog"
        >
          <RotateCw class="w-5 h-5 text-primary shrink-0 {isRunning ? 'animate-spin' : ''}" />
          {#if !isRail}
            <span class="truncate">Sync Catalog</span>
          {/if}
        </button>

        {#if sidebarController.showSyncMenu}
          <div class="surface-card absolute {isRail ? 'left-full ml-2 bottom-0 w-44' : 'bottom-full mb-1 inset-x-0'} z-50 p-1.5 flex flex-col gap-1 shadow-2xl border border-border/60 rounded-md">
            <span class="text-[9px] font-extrabold text-muted-foreground uppercase px-2 py-0.5 tracking-wider">Sync Options</span>
            <button
              type="button"
              disabled={isRunning}
              onclick={() => { isOpen = false; sidebarController.triggerSync('full', onTriggerUpdate); }}
              class="flex items-center gap-2 text-left px-2 py-1.5 text-xs rounded hover:bg-primary/20 hover:text-primary font-bold cursor-pointer transition-colors"
            >
              <Layers class="w-3.5 h-3.5 text-primary shrink-0" />
              <span>Full Sync (All)</span>
            </button>
            <button
              type="button"
              disabled={isRunning}
              onclick={() => { isOpen = false; sidebarController.triggerSync('epg', onTriggerUpdate); }}
              class="flex items-center gap-2 text-left px-2 py-1.5 text-xs rounded hover:bg-primary/20 hover:text-primary font-bold cursor-pointer transition-colors"
            >
              <Calendar class="w-3.5 h-3.5 text-primary shrink-0" />
              <span>EPG Guides Only</span>
            </button>
            <button
              type="button"
              disabled={isRunning}
              onclick={() => { isOpen = false; sidebarController.triggerSync('m3u', onTriggerUpdate); }}
              class="flex items-center gap-2 text-left px-2 py-1.5 text-xs rounded hover:bg-primary/20 hover:text-primary font-bold cursor-pointer transition-colors"
            >
              <Tv class="w-3.5 h-3.5 text-primary shrink-0" />
              <span>M3U Channels Only</span>
            </button>
          </div>
        {/if}
      </div>

      <!-- Notices Trigger (Permanent & Neutral on 0) -->
      <button
        type="button"
        onclick={() => { isOpen = false; sidebarController.openBulletinDrawer(); }}
        class="flex items-center gap-3 px-3 py-2 rounded-md font-bold text-sm text-foreground/80 hover:bg-background hover:text-foreground transition-colors w-full cursor-pointer touch-btn text-left justify-start relative {isRail ? '!justify-center !px-0' : ''}"
        title={unreadCount > 0 ? `${unreadCount} unread system notice(s)` : 'Notices'}
        aria-label="Notices"
      >
        <div class="relative flex items-center justify-center shrink-0">
          <Bell class="w-5 h-5 {unreadCount > 0 ? 'text-primary' : 'text-muted-foreground/70'}" />
          {#if isRail && unreadCount > 0}
            <span class="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          {/if}
        </div>
        {#if !isRail}
          <span class="truncate flex-1">Notices</span>
          {#if unreadCount > 0}
            <span class="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[9px] font-extrabold text-primary-foreground animate-pulse">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          {/if}
        {/if}
      </button>

      {#if authEnabled}
        <div class="pt-1 border-t border-border/20">
          <button
            type="button"
            onclick={() => { isOpen = false; if (onlogout) onlogout(); }}
            class="flex items-center gap-3 px-3 py-1.5 rounded-md font-bold text-xs text-muted-foreground hover:bg-background hover:text-primary transition-colors cursor-pointer w-full text-left {isRail ? 'justify-center !px-0' : ''}"
            title="Sign out of your session"
          >
            <LogOut class="w-4 h-4 flex-shrink-0" />
            {#if !isRail}
              <span class="truncate">Logout</span>
            {/if}
          </button>
        </div>
      {/if}

      {#if !isRail}
        <div class="pt-1.5 pb-0.5 text-[10px] text-muted-foreground/60 text-center select-none truncate">
          Pluvira &copy; 2026
        </div>
      {/if}
    </div>
  </nav>
</aside>

<LicenseModal bind:open={sidebarController.showLicenseModal} />
<BulletinDrawer bind:open={sidebarController.showBulletinDrawer} />
