<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import UidBadge from '../../ui/UidBadge.svelte';
  import type { OnboardingController } from '../OnboardingController.svelte';
  import {
    Archive,
    Sparkles,
    ShieldCheck,
    ArrowLeft,
    CheckCircle2,
    RotateCw,
    ExternalLink,
    AlertTriangle,
    Key
  } from '@lucide/svelte';

  interface Props {
    controller: OnboardingController;
    onsuccess?: () => void;
    class?: string;
  }

  let { controller, onsuccess, class: className }: Props = $props();

  function handleCompleteOffline() {
    controller.completeOnboarding(onsuccess);
  }

  function handleConnectAccount() {
    controller.startCloudPairing();
  }

  function handleReopenUrl() {
    if (typeof window !== 'undefined' && controller.verificationUriComplete) {
      window.open(controller.verificationUriComplete, '_blank');
    }
  }
</script>

<div class="flex flex-col gap-3.5 {className || ''}">
  <div class="flex items-center gap-2">
    <Badge variant="primary">Cloud Pairing</Badge>
    <h3 class="text-base font-bold text-foreground">Zero-PII Cloud Link (Optional)</h3>
  </div>

  {#if controller.pairingStatus === 'pending'}
    <div class="surface-card flex flex-col items-center gap-3 rounded-lg border border-primary/40 bg-primary/5 p-4 text-center">
      <div class="flex items-center gap-2 text-primary">
        <RotateCw class="size-5 animate-spin" />
        <span class="text-sm font-semibold">Waiting for Cloud Authorization...</span>
      </div>
      <p class="text-xs text-muted-foreground">
        Confirm the pairing request in the opened browser tab or enter this code on Pluvira Portal:
      </p>
      {#if controller.userCode}
        <div class="flex items-center gap-2 rounded-md border border-border bg-card px-4 py-2 font-mono text-xl font-bold tracking-widest text-primary">
          <Key class="size-5 text-primary" />
          <span>{controller.userCode}</span>
        </div>
        <span class="text-[11px] text-muted-foreground">Valid for 10 minutes</span>
      {/if}
      <div class="flex items-center gap-2 pt-1">
        <Button variant="outline" size="sm" onclick={handleReopenUrl} class="gap-1.5 text-xs">
          <ExternalLink class="size-3.5" />
          <span>Re-open Authorization Tab</span>
        </Button>
      </div>
    </div>
  {:else if controller.pairingStatus === 'success'}
    <div class="surface-card flex flex-col items-center gap-2.5 rounded-lg border border-primary/40 bg-primary/5 p-4 text-center">
      <CheckCircle2 class="size-7 text-primary" />
      <div class="flex flex-col gap-1">
        <span class="text-sm font-bold text-foreground">Device Linked Successfully!</span>
        <p class="text-xs text-muted-foreground">Your local instance is paired with Pluvira Cloud.</p>
      </div>
      {#if controller.formattedCloudId || controller.cloudUid}
        <div class="mt-1">
          <UidBadge uid={controller.formattedCloudId || controller.cloudUid} variant="success" showLabel={true} />
        </div>
      {/if}
      <p class="text-[11px] text-muted-foreground">
        Zero-PII User ID active. Pro trial & E2EE backup snapshot ready.
      </p>
    </div>
  {:else if controller.pairingStatus === 'expired' || controller.pairingStatus === 'denied' || controller.pairingStatus === 'failed'}
    <div class="surface-card flex flex-col items-center gap-2.5 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-center">
      <AlertTriangle class="size-6 text-destructive" />
      <div class="flex flex-col gap-1">
        <span class="text-sm font-bold text-destructive">Pairing Failed or Expired</span>
        <p class="text-xs text-muted-foreground">
          {controller.pairingError || 'The pairing code expired or was rejected in the portal.'}
        </p>
      </div>
      <Button variant="outline" size="sm" onclick={handleConnectAccount} class="mt-1 gap-1.5 text-xs">
        <RotateCw class="size-3.5" />
        <span>Generate New Code</span>
      </Button>
    </div>
  {:else}
  <div class="flex flex-col gap-2.5">
    <div class="surface-card flex items-start gap-3 rounded-lg border border-border/50 p-2.5">
      <Archive class="mt-0.5 size-4 shrink-0 text-primary" />
      <div class="flex flex-col gap-0.5">
        <span class="text-xs font-semibold text-foreground">E2EE Cloud Backup</span>
        <p class="text-xs leading-normal text-muted-foreground">
          1 snapshot encrypted client-side with your passphrase. Cloud cannot read your data.
        </p>
      </div>
    </div>

    <div class="surface-card flex items-start gap-3 rounded-lg border border-border/50 p-2.5">
      <Sparkles class="mt-0.5 size-4 shrink-0 text-primary" />
      <div class="flex flex-col gap-0.5">
        <span class="text-xs font-semibold text-foreground">14-Day Pro Trial</span>
        <p class="text-xs leading-normal text-muted-foreground">
          Unlock Rust acceleration, unlimited channels, and failover clustering without credit cards.
        </p>
      </div>
    </div>

    <div class="surface-card flex items-start gap-3 rounded-lg border border-border/50 p-2.5">
      <ShieldCheck class="mt-0.5 size-4 shrink-0 text-primary" />
      <div class="flex flex-col gap-0.5">
        <span class="text-xs font-semibold text-foreground">Zero-PII Access</span>
        <p class="text-xs leading-normal text-muted-foreground">
          Authenticate via anonymous User ID and passwordless Passkeys.
        </p>
      </div>
    </div>

  </div>

  {/if}

  <div class="mt-1 flex items-center justify-between">
    <Button variant="outline" onclick={() => controller.prevStep()} disabled={controller.loading} class="gap-1.5">
      <ArrowLeft class="size-4" />
      <span>Back</span>
    </Button>

    <div class="flex items-center gap-2">
      <Button variant="ghost" onclick={handleCompleteOffline} disabled={controller.loading}>
        Proceed in Offline Mode
      </Button>

      {#if controller.pairingStatus === 'success'}
        <Button variant="primary" onclick={handleCompleteOffline} disabled={controller.loading} class="gap-1.5">
          <CheckCircle2 class="size-4" />
          <span>Continue to Dashboard</span>
        </Button>
      {:else}
        <Button variant="primary" onclick={handleConnectAccount} disabled={controller.loading || controller.pairingStatus === 'pending'} class="gap-1.5">
          {#if controller.pairingStatus === 'pending'}
            <RotateCw class="size-4 animate-spin" />
            <span>Waiting for Approval...</span>
          {:else}
            <CheckCircle2 class="size-4" />
            <span>Connect Account</span>
          {/if}
        </Button>
      {/if}
    </div>
  </div>
</div>
