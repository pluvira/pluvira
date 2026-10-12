<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import UidBadge from '../../ui/UidBadge.svelte';
  import LicenseStatusBadge from '../../ui/LicenseStatusBadge.svelte';
  import { RotateCw, Key, ExternalLink, ShieldCheck, Sparkles, Archive, Globe } from '@lucide/svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { LicenseModal, FactoryResetModal } from '../modals';
  import { getCloudUrl } from '$lib/utils/cloudUrls';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();

  let showLicenseModal = $state(false);
  let showResetModal = $state(false);
  let initialLicenseTab = $state<'status' | 'manual' | 'sync' | 'trial'>('status');
  const isDev = Boolean((import.meta as any).env?.DEV);

  function handleClearCache() {
    controller?.clearCache();
  }

  function handleResetConfirmations() {
    controller?.resetConfirmations();
  }

  function handleOpenPortal() {
    if (typeof window !== 'undefined') {
      window.open(getCloudUrl('portal'), '_blank', 'noopener,noreferrer');
    }
  }

  function handleCloseLicenseModal() {
    controller?.loadLicenseDetails();
  }

  function formatExpiry(timestamp?: number | null): string {
    if (!timestamp) return 'No active expiration';
    try {
      return new Date(timestamp * 1000).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  }
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <!-- Identity & Cloud Pairing Card -->
  <Card title="Identity & Cloud Pairing">
    {#snippet actions()}
      {#if controller?.isRegistered}
        <Badge variant="success">REGISTERED</Badge>
      {:else}
        <Badge variant="muted">UNREGISTERED (OFFLINE)</Badge>
      {/if}
    {/snippet}

    <div class="flex flex-col gap-3 w-full">
      {#if controller?.isRegistered}
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-card border border-border/40 rounded-lg">
          <div class="flex flex-col gap-1">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Device User ID</span>
            <UidBadge uid={controller.formattedCrockfordId} size="lg" />
          </div>
          {#if controller.systemStatus?.device_hash}
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Appliance Fingerprint</span>
              <span class="text-xs font-mono text-muted-foreground font-bold" title="Volume anchor: data/.instance_id ({controller.systemStatus.device_hash})">
                {controller.systemStatus.device_hash.slice(0, 8)}...
              </span>
            </div>
          {/if}
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onclick={handleOpenPortal}
              class="flex items-center gap-1.5 text-xs font-bold touch-btn"
              title="Open customer portal"
            >
              <Globe class="size-3.5 text-primary" />
              <span>Customer Portal</span>
              <ExternalLink class="size-3 text-muted-foreground" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onclick={() => {
                initialLicenseTab = 'sync';
                showLicenseModal = true;
              }}
              class="flex items-center gap-1.5 text-xs font-bold touch-btn"
              title="Manage cloud pairing"
            >
              <Key class="size-3.5 text-muted-foreground" />
              <span>Pairing Settings</span>
            </Button>
          </div>
        </div>
      {:else}
        <div class="flex flex-col gap-3">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            <div class="panel-box flex flex-col gap-1 !p-2.5">
              <div class="flex items-center gap-1.5">
                <Sparkles class="size-3.5 text-primary" />
                <span class="text-[11px] font-bold text-foreground">14-Day Pro Trial</span>
              </div>
              <p class="text-[10px] text-muted-foreground leading-normal">
                Unlock Rust hardware acceleration, unlimited channels, and failover clustering without credit card.
              </p>
            </div>

            <div class="panel-box flex flex-col gap-1 !p-2.5">
              <div class="flex items-center gap-1.5">
                <Archive class="size-3.5 text-primary" />
                <span class="text-[11px] font-bold text-foreground">E2EE Cloud Backup</span>
              </div>
              <p class="text-[10px] text-muted-foreground leading-normal">
                1 snapshot encrypted client-side with AES-256-GCM using your passphrase.
              </p>
            </div>

            <div class="panel-box flex flex-col gap-1 !p-2.5">
              <div class="flex items-center gap-1.5">
                <ShieldCheck class="size-3.5 text-primary" />
                <span class="text-[11px] font-bold text-foreground">Zero-PII Fleet Portal</span>
              </div>
              <p class="text-[10px] text-muted-foreground leading-normal">
                Self-service fleet diagnostics and 1-click IP lease management without email.
              </p>
            </div>
          </div>

          {#if controller?.systemStatus?.device_hash}
            <div class="flex items-center justify-between px-2.5 py-1.5 bg-card/40 border border-border/20 rounded-md">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Appliance Fingerprint</span>
              <span class="text-xs font-mono text-muted-foreground font-bold" title="Volume anchor: data/.instance_id ({controller.systemStatus.device_hash})">
                {controller.systemStatus.device_hash.slice(0, 8)}...
              </span>
            </div>
          {/if}

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 bg-card/60 border border-border/30 rounded-lg">
            <span class="text-xs text-muted-foreground">
              Connect your local instance to pluvira.com to generate your anonymous User ID.
            </span>
            <div class="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onclick={handleOpenPortal}
                class="flex items-center gap-1.5 text-xs touch-btn"
              >
                <span>Visit Portal</span>
                <ExternalLink class="size-3" />
              </Button>
              <Button
                variant="primary"
                size="sm"
                onclick={() => {
                  initialLicenseTab = 'sync';
                  showLicenseModal = true;
                }}
                class="font-bold flex items-center gap-1.5 text-xs touch-btn"
              >
                <Key class="size-3.5" />
                <span>Pair Cloud / License</span>
              </Button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </Card>

  <!-- Pro License Diagnostics Card -->
  <Card title={$licenseStore.tierDisplayName || "Pro Edition"}>
    <div class="flex flex-col gap-4 w-full">
      {#if controller?.licenseData}
        {@const lic = controller.licenseData.license ?? {}}
        {#if lic.update_recommended}
          <div class="banner-warning !p-2.5 flex items-center justify-between">
            <span class="text-xs font-bold text-foreground">Update Available for pluvira-pro</span>
            <Badge variant="warning">UPDATE AVAILABLE</Badge>
          </div>
        {/if}
        {#if lic.license_status === 'grace_period'}
          <div class="banner-warning !p-2.5 flex items-center justify-between">
            <span class="text-xs font-bold text-foreground">
              Running in Offline Leeway. Offline grace expires in {lic.grace_hours_remaining ?? 48} hours. Reconnect to internet to renew active lease.
            </span>
            <Badge variant="warning">OFFLINE LEEWAY</Badge>
          </div>
        {/if}
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Runtime Edition</span>
            <div class="flex items-center gap-2 mt-0.5">
              <LicenseStatusBadge
                status="valid"
                compact={true}
                isPro={controller.licenseData.edition === 'pro'}
                tier={lic.tier || $licenseStore.tier}
                displayName={lic.display_name_full || $licenseStore.tierDisplayName}
                compactName={lic.compact_name || $licenseStore.compactName}
                badgeIcon={lic.badge_icon || $licenseStore.badgeIcon}
                badgeColor={lic.badge_color || $licenseStore.badgeColor}
                badgeTextColor={lic.badge_text_color || $licenseStore.badgeTextColor}
              />
              {#if lic.pro_version}
                <span class="text-xs font-mono text-primary font-bold">v{lic.pro_version}</span>
              {/if}
            </div>
          </div>

          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">License Lifecycle</span>
            <div class="flex items-center gap-2 mt-0.5">
              <LicenseStatusBadge
                status={lic.license_status}
                errorCode={lic.error_code}
                daysRemaining={lic.days_remaining}
                isTrial={lic.is_trial ?? lic.trial}
                isPro={controller.licenseData.edition === 'pro'}
                tier={lic.tier}
                displayName={lic.display_name_full || $licenseStore.tierDisplayName}
                compactName={lic.compact_name || $licenseStore.compactName}
                badgeIcon={lic.badge_icon || $licenseStore.badgeIcon}
                badgeColor={lic.badge_color || $licenseStore.badgeColor}
                badgeTextColor={lic.badge_text_color || $licenseStore.badgeTextColor}
              />
            </div>
          </div>

          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Expiration & Validity</span>
            <div class="flex items-center gap-2 mt-0.5">
              {#if lic.expires_at}
                <span class="text-xs font-mono font-bold text-foreground">{formatExpiry(lic.expires_at)}</span>
                {#if lic.days_remaining !== null && lic.days_remaining !== undefined}
                  <span class="text-[11px] text-muted-foreground font-mono">({lic.days_remaining}d left)</span>
                {/if}
              {:else}
                <span class="text-xs text-muted-foreground italic">No active expiration</span>
              {/if}
            </div>
          </div>

          {#if controller.licenseData.edition === 'pro'}
            <div class="panel-box">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Stream Views (IPs)</span>
              <span class="text-xs font-mono font-bold text-foreground mt-0.5">{lic.max_ips ?? $licenseStore.maxIps} concurrent</span>
            </div>
            <div class="panel-box">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Failover Slots</span>
              <span class="text-xs font-mono font-bold text-foreground mt-0.5">{lic.max_slots ?? 7} slots per channel</span>
            </div>
            <div class="panel-box">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Cloud Backup Vault</span>
              <span class="text-xs font-mono font-bold text-foreground mt-0.5">{lic.backup_max_slots ?? 5} snapshots</span>
            </div>
          {/if}

          <div class="panel-box col-span-full">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Unlocked Pro Modules</span>
            <div class="flex items-center gap-1.5 flex-wrap mt-0.5">
              {#if lic.modules && lic.modules.length > 0}
                {#each lic.modules as mod (mod)}
                  <Badge variant="success">{mod}</Badge>
                {/each}
              {:else}
                <span class="text-xs text-muted-foreground italic">No proprietary modules active</span>
              {/if}
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-border/30 pt-3">
          <Button
            variant="outline"
            size="sm"
            disabled={Boolean(controller?.loadingLicense)}
            onclick={() => controller?.loadLicenseDetails(true)}
            class="text-xs !py-1.5 flex items-center gap-1.5 touch-btn"
            title="Re-verify Pro license"
          >
            <RotateCw class="w-3.5 h-3.5 {controller?.loadingLicense ? 'animate-spin' : ''}" />
            <span>Verify License</span>
          </Button>
          <Button
            variant="primary"
            size="sm"
            onclick={() => (showLicenseModal = true)}
            class="text-xs !py-1.5 flex items-center gap-1.5 touch-btn font-bold"
            title="Open license manager and activation dialog"
          >
            <Key class="w-3.5 h-3.5" />
            <span>Manage License</span>
          </Button>
        </div>
      {:else}
        <div class="panel-box !items-center !justify-center !p-4">
          <span class="text-muted-foreground italic">Loading license diagnostics...</span>
        </div>
      {/if}
    </div>
  </Card>

  <!-- Remote Management Tunnel Card -->
  {#if isDev}
  <Card title="Remote Management Tunnel">
    <div class="flex flex-col gap-3 w-full">
      <span class="text-xs text-muted-foreground">
        Zero-Knowledge Peer-to-Peer encrypted tunnel for remote management over untrusted networks without port forwarding.
      </span>

      {#if $licenseStore.isPro}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Tunnel Status</span>
            <div class="flex items-center gap-2 mt-0.5">
              <Badge variant={$licenseStore.webrtcActive ? 'success' : 'warning'}>
                {$licenseStore.webrtcActive ? 'ACTIVE / CONNECTED' : 'STANDBY (READY)'}
              </Badge>
            </div>
          </div>

          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Encryption Standard</span>
            <span class="text-xs font-mono text-primary font-bold mt-0.5">AES-256-GCM (E2EE)</span>
          </div>

          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Signaling Relay</span>
            <span class="text-xs font-mono text-foreground mt-0.5">SaaS Blind Conduit (DSA Art. 12)</span>
          </div>
        </div>
      {:else}
        <div class="panel-box !p-4 !items-center !justify-center gap-1.5">
          <Badge variant="muted">PRO FEATURE</Badge>
          <span class="text-xs text-muted-foreground text-center">
            WebRTC P2P remote encrypted tunnel is available exclusively in Pluvira Pro.
          </span>
        </div>
      {/if}
    </div>
  </Card>
  {/if}

  <!-- Maintenance Operations -->
  <Card title="Maintenance">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
      <div class="panel-box justify-between gap-3">
        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">Cache Storage</span>
          <span class="text-muted-foreground text-[11px]">Manually clear the active in-memory / RAM disk cache if necessary.</span>
        </div>
        <div class="flex justify-end">
          <Button
            variant="danger"
            size="sm"
            disabled={Boolean(controller?.clearingCache)}
            onclick={handleClearCache}
            class="font-bold text-xs touch-btn"
          >
            <RotateCw class="w-3.5 h-3.5 {controller?.clearingCache ? 'animate-spin' : ''}" />
            <span>{controller?.clearingCache ? 'Clearing...' : 'Clear System Cache'}</span>
          </Button>
        </div>
      </div>

      <div class="panel-box justify-between gap-3">
        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">Confirmation Prompts</span>
          <span class="text-muted-foreground text-[11px]">Reset all remembered "Don't ask again" delete confirmation preferences across all views.</span>
        </div>
        <div class="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onclick={handleResetConfirmations}
            class="font-bold text-xs touch-btn"
          >
            <span>Reset Delete Confirmations</span>
          </Button>
        </div>
      </div>
    </div>
  </Card>

  <!-- Danger Zone: Factory Reset -->
  <Card title="Danger Zone">
    <div class="flex flex-col gap-3 w-full">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <Badge variant="error">DANGER ZONE</Badge>
            <span class="font-bold text-destructive">Factory Reset System</span>
          </div>
          <p class="text-xs text-muted-foreground">
            Permanently erase all playlists, guides, databases, and local preferences, restoring Pluvira to fresh post-install defaults.
          </p>
        </div>
        <Button
          variant="danger"
          size="sm"
          onclick={() => (showResetModal = true)}
          class="font-bold text-xs shrink-0 !py-1.5 touch-btn"
        >
          FACTORY RESET
        </Button>
      </div>
    </div>
  </Card>
</div>

<LicenseModal
  bind:open={showLicenseModal}
  initialTab={initialLicenseTab}
  onclose={handleCloseLicenseModal}
/>
<FactoryResetModal bind:open={showResetModal} />
