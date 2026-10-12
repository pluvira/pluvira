<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable() }: Props = $props();
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <!-- Server Settings -->
  <Card title="Server Settings">
    <div class="flex flex-col gap-4 w-full">
      <div class="w-full">
        <Input label="Device Name" bind:value={config.settings.device_name} placeholder="Pluvira" />
        <span class="text-[11px] text-muted-foreground mt-1 block">
          Broadcast as {config.settings.device_name || 'Pluvira'}._pluvira._tcp.local. on home network
        </span>
      </div>

      <div class="w-full">
        <Input label="Global User-Agent" bind:value={config.settings.user_agent} placeholder="Mozilla/5.0..." />
      </div>

      <div class="pt-2 border-t border-border/30">
        <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
        <input type="checkbox" bind:checked={config.settings.force_proxy} class="rounded text-primary" />
        <span>Force Server CORS Proxy for all video streams (bypass browser CORS)</span>
      </label>
      </div>
    </div>
  </Card>
</div>
