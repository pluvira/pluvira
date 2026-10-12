<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import { Eye, EyeOff } from '@lucide/svelte';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();
  let showPassword = $derived(controller ? controller.showPassword : false);
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <Card title="Authentication">
    <div class="flex flex-col gap-3 w-full">
      {#if config.auth}
        <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
          <input type="checkbox" bind:checked={config.auth.enabled} class="rounded text-primary" />
          <span>Enable Authentication</span>
        </label>

        {#if config.auth.enabled}
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full mt-2 pt-3 border-t border-border animate-fade-in items-end">
            <Input label="Admin Username" bind:value={config.auth.username} placeholder="admin" />
            <div class="flex items-end gap-1.5 w-full">
              <div class="flex-1">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  label="Admin Password"
                  bind:value={config.auth.password}
                  placeholder="admin password..."
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onclick={() => (controller ? controller.toggleShowPassword() : undefined)}
                class="h-[36px] px-2.5 shrink-0 touch-btn"
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {#if showPassword}
                  <EyeOff class="w-4 h-4" />
                {:else}
                  <Eye class="w-4 h-4" />
                {/if}
              </Button>
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </Card>
</div>
