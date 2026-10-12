<script lang="ts">
  import Dialog from './Dialog.svelte';
  import Button from './Button.svelte';
  import Checkbox from './Checkbox.svelte';
  import { AlertTriangle } from '@lucide/svelte';
  import {
    DELETE_CONFIRM_DETAILS,
    setDeleteConfirmationPreference,
    type DeleteConfirmScope
  } from './ConfirmUtils';

  interface Props {
    open?: boolean;
    scope?: DeleteConfirmScope;
    title?: string;
    message?: string;
    dontAskText?: string;
    confirmText?: string;
    confirmVariant?: 'danger' | 'primary' | 'secondary';
    onconfirm?: () => void;
    oncancel?: () => void;
    class?: string;
  }

  let {
    open = $bindable(),
    scope = 'history_record',
    title = '',
    message = '',
    dontAskText = '',
    confirmText = '',
    confirmVariant,
    onconfirm,
    oncancel,
    class: className = ''
  }: Props = $props();

  let dontAskAgain = $state(false);

  let scopeDetails = $derived(DELETE_CONFIRM_DETAILS[scope] || DELETE_CONFIRM_DETAILS.history_record);
  let dialogTitle = $derived(title || scopeDetails.title);
  let dialogMessage = $derived(message || scopeDetails.message);
  let dialogDontAskText = $derived(dontAskText || scopeDetails.dontAskText);
  let effectiveConfirmText = $derived(confirmText || scopeDetails.confirmText || 'Confirm Delete');
  let effectiveConfirmVariant = $derived(confirmVariant || scopeDetails.confirmVariant || 'danger');

  function handleConfirm() {
    if (dontAskAgain) {
      setDeleteConfirmationPreference(scope, false);
    }
    open = false;
    onconfirm?.();
  }

  function handleCancel() {
    open = false;
    oncancel?.();
  }
</script>

<Dialog bind:open title={dialogTitle} onclose={handleCancel} class="max-w-md {className}">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={handleCancel} class="touch-btn">Cancel</Button>
    <Button variant={effectiveConfirmVariant} size="sm" onclick={handleConfirm} class="font-bold touch-btn">
      {effectiveConfirmText}
    </Button>
  {/snippet}

  <div class="flex flex-col gap-4 w-full text-xs">
    <div class="flex items-start gap-3 p-3 bg-destructive/10 border border-destructive/40 rounded-md">
      <AlertTriangle class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
      <p class="text-foreground text-xs leading-relaxed font-bold">
        {dialogMessage}
      </p>
    </div>

    <div class="pt-1">
      <Checkbox
        bind:checked={dontAskAgain}
        label={dialogDontAskText}
      />
    </div>
  </div>
</Dialog>
