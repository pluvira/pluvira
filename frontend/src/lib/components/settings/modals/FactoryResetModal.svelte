<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Input from '../../ui/Input.svelte';
  import { AlertTriangle, Trash2, ArrowLeft, RotateCw } from '@lucide/svelte';
  import { FactoryResetController } from '../utils/FactoryResetController.svelte';

  interface Props {
    open?: boolean;
    onclose?: () => void;
  }

  let { open = $bindable(), onclose }: Props = $props();

  const controller = new FactoryResetController();

  function handleClose() {
    controller.reset();
    open = false;
    if (onclose) onclose();
  }

  async function handleConfirmReset() {
    await controller.executeReset(() => {
      open = false;
      if (typeof window !== 'undefined') {
        window.location.hash = '#/';
        window.location.reload();
      }
    });
  }
</script>

<Dialog {open} title="System Factory Reset" onclose={handleClose}>
  <div class="flex flex-col gap-4 text-xs text-foreground">
    {#if controller.step === 1}
      <div class="banner-error !p-3 flex items-start gap-2.5">
        <AlertTriangle class="size-4 text-destructive shrink-0 mt-0.5" />
        <div class="flex flex-col gap-1">
          <span class="font-bold text-destructive">Irreversible Action Ahead</span>
          <p class="text-muted-foreground leading-normal">
            A factory reset permanently restores Pluvira to its initial post-installation state. All local databases and configurations will be irreversibly erased.
          </p>
        </div>
      </div>

      <div class="panel-box flex flex-col gap-2">
        <span class="text-[10px] font-bold text-muted-foreground uppercase">Data Destroyed Upon Reset:</span>
        <ul class="list-disc pl-4 flex flex-col gap-1 text-muted-foreground">
          <li>All IPTV M3U sources and XMLTV guide configurations</li>
          <li>All custom channel rewrites and EPG mapping overrides</li>
          <li>Personal curated playlists and candidate stream slot pools</li>
          <li>Stream reachability history and quarantine metrics</li>
          <li>Local execution logs and scheduled background tasks</li>
          <li>Cached Pro license tokens and browser session preferences</li>
        </ul>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-border/20">
        <Button variant="secondary" size="sm" onclick={handleClose} class="touch-btn">
          Cancel
        </Button>
        <Button variant="danger" size="sm" onclick={() => controller.nextStep()} class="font-bold touch-btn">
          Proceed to Confirmation
        </Button>
      </div>
    {:else}
      <div class="banner-warning !p-3 flex items-start gap-2.5">
        <Trash2 class="size-4 text-primary shrink-0 mt-0.5" />
        <div class="flex flex-col gap-1">
          <span class="font-bold text-foreground">Step 2: Security Confirmation</span>
          <p class="text-muted-foreground leading-normal">
            To prevent accidental destruction, please type <strong class="text-foreground font-mono">RESET</strong> below to finalize.
          </p>
        </div>
      </div>

      <div class="flex flex-col gap-1.5">
        <Input
          id="factory-reset-confirm-input"
          label="Type 'RESET' to confirm:"
          placeholder="RESET"
          bind:value={controller.confirmText}
          disabled={controller.loading}
        />
        {#if controller.errorMessage}
          <span class="text-destructive font-bold text-[11px]">{controller.errorMessage}</span>
        {/if}
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-border/20">
        <Button
          variant="outline"
          size="sm"
          disabled={controller.loading}
          onclick={() => controller.prevStep()}
          class="flex items-center gap-1.5 touch-btn"
        >
          <ArrowLeft class="size-3.5" />
          <span>Back</span>
        </Button>

        <Button
          variant="danger"
          size="sm"
          disabled={!controller.isConfirmValid || controller.loading}
          onclick={handleConfirmReset}
          class="font-bold flex items-center gap-1.5 touch-btn"
        >
          {#if controller.loading}
            <RotateCw class="size-3.5 animate-spin" />
            <span>Erasing System...</span>
          {:else}
            <Trash2 class="size-3.5" />
            <span>Erase All & Reset</span>
          {/if}
        </Button>
      </div>
    {/if}
  </div>
</Dialog>
