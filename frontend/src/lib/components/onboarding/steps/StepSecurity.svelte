<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import Input from '../../ui/Input.svelte';
  import Switch from '../../ui/Switch.svelte';
  import type { OnboardingController } from '../OnboardingController.svelte';
  import { Info, ArrowRight, ArrowLeft } from '@lucide/svelte';

  interface Props {
    controller: OnboardingController;
    class?: string;
  }

  let { controller, class: className }: Props = $props();
</script>

<div class="flex flex-col gap-3.5 {className || ''}">
  <div class="flex items-center gap-2">
    <Badge variant="primary">Security & Access</Badge>
    <h3 class="text-base font-bold text-foreground">Set Admin Password</h3>
  </div>

  <div class="flex flex-col gap-2.5">
    <div class="surface-card flex items-center justify-between rounded-lg border border-border/40 p-3">
      <div class="flex flex-col">
        <span class="text-sm font-semibold text-foreground">Require Authentication</span>
        <span class="text-xs text-muted-foreground">Protect settings and management endpoints with a password</span>
      </div>
      <Switch
        id="onboarding-auth-enabled"
        checked={controller.authEnabled}
        onCheckedChange={(val) => { controller.authEnabled = val; }}
        disabled={controller.loading}
      />
    </div>

    {#if controller.authEnabled}
      <Input
        id="onboarding-admin-password"
        type="password"
        label="Admin Password"
        placeholder="Enter at least 6 characters"
        bind:value={controller.adminPassword}
        disabled={controller.loading}
      />

      <Input
        id="onboarding-confirm-password"
        type="password"
        label="Confirm Password"
        placeholder="Re-enter your password"
        bind:value={controller.confirmPassword}
        disabled={controller.loading}
      />
    {/if}

    <div class="surface-card flex items-start gap-2 rounded-lg border border-border/40 p-2.5 text-xs text-muted-foreground">
      <Info class="mt-0.5 size-3.5 shrink-0 text-primary" />
      <span>If skipped, Pluvira will remain freely accessible to anyone on your local home network.</span>
    </div>
  </div>

  <div class="mt-1 flex items-center justify-between">
    <Button variant="outline" onclick={() => controller.prevStep()} disabled={controller.loading} class="gap-1.5">
      <ArrowLeft class="size-4" />
      <span>Back</span>
    </Button>

    <div class="flex items-center gap-2">
      <Button variant="ghost" onclick={() => controller.skipSecurityStep()} disabled={controller.loading}>
        Skip for Now
      </Button>

      <Button
        variant="primary"
        onclick={() => controller.saveSecurityAndContinue()}
        disabled={controller.loading}
        class="gap-1.5"
      >
        <span>{controller.authEnabled ? 'Save & Continue' : 'Continue'}</span>
        <ArrowRight class="size-4" />
      </Button>
    </div>
  </div>
</div>
