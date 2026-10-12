<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import { MetadataModalController } from '../utils/MetadataModalController.svelte';
  import { testImageReachability } from '../utils/ChannelsUtils';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let { channel = null, open = $bindable(), onclose, onsaved }: Props = $props();

  const controller = new MetadataModalController();

  let logoUrl = $state('');
  let testingHttp = $state(false);
  let httpStatusText = $state('');
  let httpStatusOk = $state<boolean | null>(null);

  $effect(() => {
    if (channel) {
      logoUrl = channel.logo || '';
      httpStatusText = '';
      httpStatusOk = null;
    }
  });

  async function testLogoHttp() {
    if (!logoUrl.trim()) {
      httpStatusText = 'No logo URL specified';
      httpStatusOk = false;
      return;
    }

    testingHttp = true;
    httpStatusText = 'Testing HTTP image reachability...';
    httpStatusOk = null;

    const reachable = await testImageReachability(logoUrl.trim());
    testingHttp = false;
    if (reachable) {
      httpStatusText = 'OK (Image loaded successfully)';
      httpStatusOk = true;
    } else {
      httpStatusText = 'Error: Image failed to load or unreachable';
      httpStatusOk = false;
    }
  }

  async function handleSave() {
    if (!channel) return;
    const ok = await controller.updateRewrite(channel, 'logo', logoUrl.trim());
    if (ok) {
      open = false;
      if (onsaved) onsaved();
    }
  }
</script>

<Dialog bind:open title="Edit Channel Logo URL" {onclose}>
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">Cancel</Button>
    <Button variant="primary" size="sm" disabled={controller.saving} onclick={handleSave} class="font-bold touch-btn">
      {controller.saving ? 'Saving...' : 'Apply Logo Rewrite'}
    </Button>
  {/snippet}
  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs">
      <Input label="Logo Image URL" bind:value={logoUrl} placeholder="https://example.com/logo.png" />

      <div class="panel-box !items-center !justify-center !gap-3 !p-4">
        <span class="text-[10px] font-bold text-muted-foreground uppercase">Logo Preview & Diagnosis</span>

        <div class="w-48 h-20 bg-background border border-border/30 rounded flex items-center justify-center overflow-hidden p-2">
          {#if logoUrl.trim()}
            <img src={logoUrl.trim()} alt="Preview" class="max-w-full max-h-full object-contain" />
          {:else}
            <span class="text-muted-foreground text-xs italic">No image URL</span>
          {/if}
        </div>

        {#if httpStatusText}
          <span class="text-xs font-bold text-center {httpStatusOk === true ? 'text-primary' : httpStatusOk === false ? 'text-destructive' : 'text-muted-foreground'}">
            {httpStatusText}
          </span>
        {/if}

        <Button variant="outline" size="sm" disabled={testingHttp} onclick={testLogoHttp} class="!py-1 text-xs touch-btn">
          {testingHttp ? 'Testing...' : 'Test / Preview Logo'}
        </Button>
      </div>

    </div>
  {/if}
</Dialog>
