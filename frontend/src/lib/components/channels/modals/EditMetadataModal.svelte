<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import type { ChannelItem, RewriteRule } from '$lib/api/types';
  import { MetadataModalController } from '../utils/MetadataModalController.svelte';
  import { RewriteRulesManager } from '../../settings/sections';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let { channel = null, open = $bindable(), onclose, onsaved }: Props = $props();

  const controller = new MetadataModalController();
  let channelRules = $state<RewriteRule[]>([]);

  $effect(() => {
    if (open && channel) {
      controller.loadChannelRules(channel).then((rules) => {
        channelRules = rules;
      });
    }
  });

  async function handleSave() {
    if (!channel) return;
    const ok = await controller.saveChannelRules(channel, channelRules);
    if (ok) {
      open = false;
      if (onsaved) onsaved();
    }
  }
</script>

<Dialog bind:open title={`Edit Individual Rewrites (${channel?.name || 'Channel'})`} {onclose} class="max-w-2xl">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)}>Cancel</Button>
    <Button variant="primary" size="sm" disabled={controller.saving} onclick={handleSave}>
      {controller.saving ? 'Saving...' : 'Save Individual Rewrites'}
    </Button>
  {/snippet}
  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs">
      {#if controller.loading}
        <div class="panel-box !items-center !justify-center !p-6">
          <span class="spinner mr-2"></span>
          <span>Loading individual rules...</span>
        </div>
      {:else}
        <RewriteRulesManager
          bind:rules={channelRules}
          description={`Individual metadata rewrite rules for '${channel.name}' (${channel.source})`}
          storageKeyPrefix={`ch_rw_${channel.id}`}
        />

      {/if}
    </div>
  {/if}
</Dialog>
