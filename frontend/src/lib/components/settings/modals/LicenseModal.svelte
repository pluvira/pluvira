<script lang="ts">
  import { untrack } from 'svelte';
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import UidBadge from '../../ui/UidBadge.svelte';
  import LicenseStatusBadge from '../../ui/LicenseStatusBadge.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import { LicenseModalController, type LicenseModalTab } from '../utils/LicenseModalController.svelte';
  import {
    ShieldCheck,
    Sparkles,
    Key,
    RotateCw,
    ExternalLink,
    AlertTriangle,
    Globe,
    CheckCircle2
  } from '@lucide/svelte';

  interface Props {
    open?: boolean;
    initialTab?: LicenseModalTab;
    onclose?: () => void;
    class?: string;
  }

  let { open = $bindable(), initialTab, onclose, class: className = '' }: Props = $props();

  const controller = new LicenseModalController();

  $effect(() => {
    if (open) {
      if (initialTab) {
        controller.setTab(initialTab);
      }
      untrack(() => {
        controller.loadLicenseDetails();
      });
    } else {
      controller.stopPairingPolling();
    }
    return () => {
      controller.stopPairingPolling();
    };
  });

  const tabSegments: SegmentOption<LicenseModalTab>[] = [
    { value: 'status', label: 'Status', icon: ShieldCheck },
    { value: 'manual', label: 'Token Key', icon: Key },
    { value: 'sync', label: 'Cloud Sync', icon: Globe },
    { value: 'trial', label: '14d Trial', icon: Sparkles }
  ];

  function handleClose() {
    controller.stopPairingPolling();
    open = false;
    onclose?.();
  }

  function handleReopenTab() {
    if (typeof window !== 'undefined' && controller.verificationUriComplete) {
      window.open(controller.verificationUriComplete, '_blank', 'noopener,noreferrer');
    }
  }
</script>

<Dialog {open} title="{controller.tierDisplayName} Licensing & Activation" onclose={handleClose} class={className}>
  <div class="flex flex-col gap-4 text-xs text-foreground min-h-[380px]">
    <!-- Tab Selector -->
    <SegmentedControl
      options={tabSegments}
      value={controller.activeTab}
      onchange={(val) => controller.setTab(val)}
    />

    {#if controller.errorMessage}
      <div class="p-2.5 rounded bg-destructive/10 border border-destructive/30 text-destructive flex items-center gap-2">
        <AlertTriangle class="w-4 h-4 shrink-0" />
        <span class="text-xs">{controller.errorMessage}</span>
      </div>
    {/if}

    {#if controller.activeTab === 'status'}
      <!-- TAB 1: STATUS & DIAGNOSTICS -->
      <div class="flex flex-col gap-3">
        {#if controller.managedByEnv}
          <div class="p-2.5 rounded bg-primary/10 border border-primary/30 flex items-center justify-between text-primary">
            <span class="font-bold">Managed via Environment (PLUVIRA_PRO_LICENSE_TOKEN)</span>
            <Badge variant="primary">ENV VAR</Badge>
          </div>
        {/if}

        {#if controller.licenseDetails?.license_status === 'grace_period'}
          <div class="p-2.5 rounded bg-primary/10 border border-primary/30 text-primary flex items-center gap-2">
            <AlertTriangle class="w-4 h-4 shrink-0" />
            <span class="text-xs">
              Running in Offline Leeway. Offline grace expires in {controller.licenseDetails.grace_hours_remaining ?? 48} hours. Reconnect to internet to renew active lease.
            </span>
          </div>
        {/if}

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">Runtime Edition</span>
            <div class="flex items-center gap-1.5 mt-1">
              <LicenseStatusBadge
                status="valid"
                compact={true}
                isPro={controller.isPro}
                tier={controller.tier}
                displayName={controller.tierDisplayName}
                compactName={controller.compactName}
                badgeIcon={controller.badgeIcon}
                badgeColor={controller.badgeColor}
                badgeTextColor={controller.badgeTextColor}
              />
              {#if controller.proVersion}
                <span class="text-[11px] font-mono text-primary font-bold">v{controller.proVersion}</span>
              {/if}
            </div>
          </div>

          <div class="panel-box">
            <span class="text-[10px] font-bold text-muted-foreground uppercase">License State</span>
            <div class="flex items-center gap-1.5 mt-1">
              <LicenseStatusBadge
                status={controller.licenseDetails?.license_status}
                errorCode={controller.licenseDetails?.error_code}
                daysRemaining={controller.daysRemaining}
                isTrial={controller.isTrial}
                isPro={controller.isPro}
                tier={controller.tier}
                displayName={controller.tierDisplayName}
                compactName={controller.compactName}
                badgeIcon={controller.badgeIcon}
                badgeColor={controller.badgeColor}
                badgeTextColor={controller.badgeTextColor}
              />
            </div>
          </div>

        </div>

        <div class="panel-mono !p-3 flex flex-col gap-2">
          {#if controller.crockfordId}
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground font-bold">User ID:</span>
              <div class="flex items-center gap-1.5">
                <UidBadge uid={controller.crockfordId} />
              </div>
            </div>
          {/if}

          {#if controller.isPro}
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 border-t border-border/20 pt-2 text-[11px]">
              <div class="flex flex-col gap-0.5">
                <span class="text-muted-foreground font-bold">Stream Views:</span>
                <span class="text-foreground font-sans font-bold">{controller.maxIps} concurrent</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-muted-foreground font-bold">Failover Slots:</span>
                <span class="text-foreground font-sans font-bold">{controller.maxSlots} slots</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-muted-foreground font-bold">Cloud Backup:</span>
                <span class="text-foreground font-sans font-bold">{controller.backupMaxSlots ?? 5} snapshots</span>
              </div>
            </div>
          {/if}

          <div class="flex flex-col gap-1 border-t border-border/20 pt-2">
            <span class="text-muted-foreground font-bold">Active Pro Modules:</span>
            <div class="flex items-center gap-1 flex-wrap mt-0.5">
              {#if controller.modules.length > 0}
                {#each controller.modules as mod (mod)}
                  <Badge variant="success">{mod}</Badge>
                {/each}
              {:else}
                <span class="text-muted-foreground italic">No proprietary modules unlocked</span>
              {/if}
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <Button
            variant="outline"
            size="sm"
            disabled={controller.actionLoading}
            onclick={() => controller.refreshHandshake()}
            class="text-xs touch-btn"
          >
            <RotateCw class="w-3.5 h-3.5 mr-1.5 {controller.actionLoading ? 'animate-spin' : ''}" />
            <span>Verify Online Handshake</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onclick={() => controller.openPortalSync()}
            class="text-xs text-primary touch-btn"
          >
            <span>Customer Portal</span>
            <ExternalLink class="w-3.5 h-3.5 ml-1.5" />
          </Button>
        </div>
      </div>
    {:else if controller.activeTab === 'manual'}
      <!-- TAB 2: MANUAL JWT TOKEN (MODE 2) -->
      <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <span class="font-bold text-foreground">Ed25519 Cryptographic License Token</span>
          <p class="text-muted-foreground text-[11px]">
            Paste the raw signed JWT token received from portal.pluvira.com or commercial subscription invoices.
          </p>
        </div>

        <textarea
          bind:value={controller.manualToken}
          disabled={controller.actionLoading || controller.managedByEnv}
          placeholder="eyJhbGciOiJFZERTQ..."
          class="textarea-base font-mono text-[11px] h-32 w-full p-2.5 resize-none {controller.managedByEnv ? 'opacity-50 cursor-not-allowed' : ''}"
        ></textarea>

        {#if controller.managedByEnv}
          <div class="p-2 rounded bg-muted/20 border border-border/40 text-muted-foreground text-[11px]">
            Token configuration is locked because an environment variable (PLUVIRA_PRO_LICENSE_TOKEN) is active.
          </div>
        {/if}

        {#if controller.uuidError}
          <div class="p-2.5 rounded bg-primary/10 border border-primary/30 text-primary flex items-center gap-2">
            <AlertTriangle class="w-4 h-4 shrink-0" />
            <span class="text-xs">You entered a License Key (UUID). Please paste the cryptographic Ed25519 Token (starts with 'eyJhbGciOi...').</span>
          </div>
        {/if}

        <div class="flex items-center justify-end gap-2 pt-2">
          <Button
            variant="primary"
            size="sm"
            disabled={controller.actionLoading || controller.managedByEnv || !controller.manualToken.trim()}
            onclick={() => controller.activateToken()}
            class="font-bold touch-btn"
          >
            <Key class="w-3.5 h-3.5 mr-1.5" />
            <span>{controller.actionLoading ? 'Verifying...' : 'Verify & Activate Token'}</span>
          </Button>
        </div>
      </div>
    {:else if controller.activeTab === 'sync'}
      <!-- TAB 3: RFC 8628 CLOUD PAIRING (1-CLICK) -->
      <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <span class="font-bold text-foreground">RFC 8628 Device Authorization & Pairing</span>
          <p class="text-muted-foreground text-[11px]">
            Connect your self-hosted instance to Pluvira Cloud via 1-click device authorization.
          </p>
        </div>

        {#if controller.isCloudLinked}
          <div class="surface-card p-3.5 flex flex-col gap-3 border border-primary/30 bg-primary/5 rounded-lg">
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-start gap-2.5">
                <CheckCircle2 class="w-5 h-5 text-primary shrink-0 mt-0.5" />
                <div class="flex flex-col gap-0.5">
                  <span class="font-bold text-foreground">Cloud Account Linked</span>
                  <p class="text-[11px] text-muted-foreground">
                    Instance paired with centralized Zero-PII User ID.
                  </p>
                </div>
              </div>
              <Badge variant="success">PAIRED</Badge>
            </div>

            {#if controller.crockfordId}
              <div class="flex items-center justify-between p-2 rounded bg-card border border-border/40 font-mono">
                <span class="text-xs text-muted-foreground font-semibold">User ID:</span>
                <div class="flex items-center gap-1.5">
                  <UidBadge uid={controller.crockfordId} />
                </div>
              </div>
            {/if}

            <div class="flex items-center justify-between border-t border-border/30 pt-3">
              <Button
                variant="danger"
                size="sm"
                disabled={controller.actionLoading}
                onclick={() => controller.unlinkAccount()}
                class="text-xs touch-btn"
              >
                <span>Unlink Account</span>
              </Button>

              <Button
                variant="primary"
                size="sm"
                disabled={controller.actionLoading}
                onclick={() => controller.syncFromCloud()}
                class="text-xs font-bold touch-btn"
              >
                <RotateCw class="w-3.5 h-3.5 mr-1.5 {controller.actionLoading ? 'animate-spin' : ''}" />
                <span>Sync License with Pluvira Cloud</span>
              </Button>
            </div>
          </div>
        {:else if controller.pairingStatus === 'pending'}
          <div class="surface-card p-4 flex flex-col items-center gap-3 border border-primary/40 bg-primary/5 rounded-lg text-center">
            <div class="flex items-center gap-2 text-primary">
              <RotateCw class="w-5 h-5 animate-spin" />
              <span class="text-sm font-semibold">Waiting for Cloud Authorization...</span>
            </div>
            <p class="text-xs text-muted-foreground">
              Confirm the pairing request in the opened browser tab or enter this code on Pluvira Portal:
            </p>
            {#if controller.userCode}
              <div class="flex items-center gap-2 rounded-md border border-border bg-card px-4 py-2 font-mono text-xl font-bold tracking-widest text-primary">
                <Key class="w-5 h-5 text-primary" />
                <span>{controller.userCode}</span>
              </div>
              <span class="text-[11px] text-muted-foreground">Valid for 10 minutes</span>
            {/if}
            <div class="flex items-center gap-2 pt-1">
              <Button variant="outline" size="sm" onclick={handleReopenTab} class="gap-1.5 text-xs">
                <ExternalLink class="w-3.5 h-3.5" />
                <span>Re-open Authorization Tab</span>
              </Button>
              <Button variant="ghost" size="sm" onclick={() => controller.cancelPairingFlow()} class="text-xs">
                <span>Cancel</span>
              </Button>
            </div>
          </div>
        {:else if controller.pairingStatus === 'expired' || controller.pairingStatus === 'denied' || controller.pairingStatus === 'failed'}
          <div class="surface-card p-3.5 flex flex-col items-center gap-2.5 border border-destructive/40 bg-destructive/5 rounded-lg text-center">
            <AlertTriangle class="w-6 h-6 text-destructive" />
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold text-destructive">Pairing Failed or Expired</span>
              <p class="text-xs text-muted-foreground">
                {controller.pairingError || 'The pairing code expired or was rejected in the portal.'}
              </p>
            </div>
            <Button variant="outline" size="sm" onclick={() => controller.startPairingFlow()} class="mt-1 gap-1.5 text-xs">
              <RotateCw class="w-3.5 h-3.5" />
              <span>Generate New Code</span>
            </Button>
          </div>
        {:else}
        <div class="surface-card p-3.5 flex flex-col gap-3 border border-border/40 rounded-lg">
          <div class="flex items-start gap-3">
            <Globe class="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div class="flex flex-col gap-1">
              <span class="font-bold text-foreground">Zero-Touch License Provisioning</span>
              <p class="text-[11px] text-muted-foreground leading-relaxed">
                Authenticates with Logto IAM using Passkeys or passwordless OAuth2 to pair your anonymous User ID and retrieve active subscriptions.
              </p>
            </div>
          </div>

          <div class="flex items-center justify-end border-t border-border/30 pt-3">
            <Button
              variant="primary"
              size="sm"
              disabled={controller.actionLoading}
              onclick={() => controller.startPairingFlow()}
              class="text-xs font-bold touch-btn gap-1.5"
            >
              <Key class="w-3.5 h-3.5" />
              <span>{controller.actionLoading ? 'Connecting...' : 'Connect Pluvira Account'}</span>
            </Button>
          </div>
        </div>
        {/if}

        <div class="p-2.5 rounded bg-muted/20 border border-border/30 text-muted-foreground text-[11px] flex items-center gap-2">
          <ShieldCheck class="w-4 h-4 text-primary shrink-0" />
          <span>Active leases can be purged or reallocated directly on portal.pluvira.com in 1 click.</span>
        </div>
      </div>
    {:else if controller.activeTab === 'trial'}
      <!-- TAB 4: 14-DAY PRO TRIAL (MODE 1) -->
      <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <span class="font-bold text-foreground">14-Day Free Pro Trial</span>
          <p class="text-muted-foreground text-[11px]">
            Test all proprietary Pro engine capabilities on-demand with zero credit card required.
          </p>
        </div>

        <div class="surface-card p-3.5 flex flex-col gap-3 border border-border/40 rounded-lg">
          <div class="flex items-start gap-3">
            <Sparkles class="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div class="flex flex-col gap-1.5">
              <span class="font-bold text-foreground">Included Trial Features</span>
              <ul class="flex flex-col gap-1 text-[11px] text-muted-foreground list-disc pl-4">
                <li>Bypass 25-channel curated cap in "My List"</li>
                <li>7 stream failover backup slots per channel (vs 2 in Free)</li>
                <li>Rust-accelerated auto-merge deduplication & batch link testing</li>
                <li>Turbo native streaming XMLTV ingestion (&lt;2s)</li>
              </ul>
            </div>
          </div>

          {#if controller.isTrial}
            <div class="banner-warning !p-2.5 flex items-center justify-between">
              <span class="font-bold text-foreground">Trial active: {controller.daysRemaining} days remaining</span>
              <Badge variant="warning">TRIAL ACTIVE</Badge>
            </div>
          {:else if controller.isPro}
            <div class="p-2.5 rounded bg-primary/10 border border-primary/30 text-primary font-bold">
              Full Pro License is currently active on this instance.
            </div>
          {:else if controller.isTrialClaimed}
            <div class="p-2.5 rounded bg-muted/20 border border-border/40 text-muted-foreground flex items-center justify-between">
              <span>The 14-day trial has already been claimed on this system.</span>
              <Badge variant="muted">EXHAUSTED</Badge>
            </div>
            <div class="flex items-center justify-end border-t border-border/30 pt-3">
              <Button
                variant="outline"
                size="sm"
                disabled={true}
                class="font-bold touch-btn opacity-50 cursor-not-allowed"
              >
                <span>Trial Already Claimed</span>
              </Button>
            </div>
          {:else}
            <div class="flex items-center justify-end border-t border-border/30 pt-3">
              <Button
                variant="primary"
                size="sm"
                disabled={controller.actionLoading}
                onclick={() => controller.claimTrial()}
                class="font-bold touch-btn"
              >
                <Sparkles class="w-3.5 h-3.5 mr-1.5" />
                <span>{controller.actionLoading ? 'Claiming Trial...' : 'Activate 14-Day Free Trial'}</span>
              </Button>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  {#snippet footer()}
    <div class="flex items-center justify-between w-full">
      <span class="text-[11px] text-muted-foreground font-mono">
        Pluvira Core &copy; 2026 | BSL 1.1
      </span>
      <Button variant="secondary" size="sm" onclick={handleClose} class="touch-btn">
        Close
      </Button>
    </div>
  {/snippet}
</Dialog>
