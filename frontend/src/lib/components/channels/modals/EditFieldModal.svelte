<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import type { ChannelItem, ChannelRewritePayload } from '$lib/api/types';
  import { MetadataModalController } from '../utils/MetadataModalController.svelte';

  interface Props {
    channel?: ChannelItem | null;
    field?: ChannelRewritePayload['field'];
    fieldLabel?: string;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let {
    channel = null,
    field = 'name',
    fieldLabel = 'Attribute',
    open = $bindable(),
    onclose,
    onsaved
  }: Props = $props();

  const controller = new MetadataModalController();

  let fieldValue = $state('');

  $effect(() => {
    if (channel && field) {
      fieldValue = String(channel[field as keyof ChannelItem] || '');
    }
  });

  async function handleSave() {
    if (!channel || !field) return;
    const ok = await controller.updateRewrite(channel, field, fieldValue.trim());
    if (ok) {
      open = false;
      if (onsaved) onsaved();
    }
  }
</script>

<Dialog bind:open title={`Edit ${fieldLabel}`} {onclose}>
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">Cancel</Button>
    <Button variant="primary" size="sm" disabled={controller.saving} onclick={handleSave} class="font-bold touch-btn">
      {controller.saving ? 'Saving...' : 'Apply Rewrite'}
    </Button>
  {/snippet}
  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs">
      <div class="panel-mono !p-3">
        <span class="text-muted-foreground font-bold text-[10px] uppercase">Original RAW Value:</span>
        <span class="text-foreground font-mono text-xs break-all">
          {(channel.original_data && channel.original_data[field as keyof typeof channel.original_data]) || '—'}
        </span>
      </div>

      <Input label={`New ${fieldLabel}`} bind:value={fieldValue} placeholder="Enter new value..." />

    </div>
  {/if}
</Dialog>
