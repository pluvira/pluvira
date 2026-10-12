<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import AccordionCard from '../../ui/AccordionCard.svelte';
  import RewriteRulesManager from './RewriteRulesManager.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { Zap } from '@lucide/svelte';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();

  const confirmController = new ConfirmController();
  let isPro = $derived($licenseStore.isPro);

  function addMappingOverride() {
    controller?.submitNewMappingOverride();
  }

  function removeMappingOverride(key: string, index?: number) {
    confirmController.requestConfirm('override_rule', () => {
      controller?.removeMappingOverride(key);
      if (controller && controller.expandedOverridesIdx === index) {
        controller.setExpandedOverridesIdx(null);
      }
    });
  }

  function moveMappingOverride(index: number, direction: number) {
    controller?.moveMappingOverride(index, direction);
    const newIndex = index + direction;
    if (controller?.expandedOverridesIdx === index) controller.setExpandedOverridesIdx(newIndex);
    else if (controller?.expandedOverridesIdx === newIndex) controller.setExpandedOverridesIdx(index);
  }
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  <!-- Global Metadata Rewrites -->
  <Card title="Global Metadata Rewrites">
    {#snippet actions()}
      {#if isPro}
        <Badge variant="primary" title="Accelerated with native Rust Turbo Cascade Rewrite engine">
          <Zap class="w-3 h-3 mr-1 inline" />TURBO REWRITES
        </Badge>
      {/if}
    {/snippet}
    <div class="flex flex-col gap-3">
      <RewriteRulesManager
        bind:rules={config.settings.rewrites}
        description="Rules applied sequentially to transform channel name, group, logo, URL, and User-Agent"
        storageKeyPrefix="gt_rewrites"
      />
    </div>
  </Card>

  <!-- Manual EPG Mapping Overrides Map Editor -->
  <Card title="Manual EPG Mapping Overrides">
    <div class="flex flex-col gap-3">
      <span class="text-xs text-muted-foreground border-b border-border/30 pb-2">Manual mapping rules of M3U channel names to EPG guide IDs</span>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 items-end panel-box !p-3">
        <Input label="M3U Channel Name" bind:value={controller!.newOverrideKey} placeholder="e.g. Channel One HD" />
        <Input label="Namespaced EPG ID" bind:value={controller!.newOverrideValue} placeholder="e.g. EPG_Source_Alpha::channel1.net" />
        <Button variant="primary" size="sm" onclick={addMappingOverride} class="font-bold text-xs h-[36px] w-full sm:col-span-2 md:col-span-1 touch-btn">
          + Add Override Mapping
        </Button>
      </div>

      {#if !config.settings.mapping_overrides || Object.keys(config.settings.mapping_overrides).length === 0}
        <div class="panel-box !items-center !justify-center !p-4">
          No manual EPG mapping overrides defined.
        </div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each Object.entries(config.settings.mapping_overrides) as [key, val], idx (key)}
            {@const isExpanded = controller?.expandedOverridesIdx === idx}
            <AccordionCard
              title={`${key} ➔ ${val}`}
              open={isExpanded}
              ontoggle={(isOpen) => controller?.setExpandedOverridesIdx(isOpen ? idx : null)}
              badgeText="EPG Override"
              badgeVariant="primary"
              index={idx}
              totalCount={Object.keys(config.settings.mapping_overrides).length}
              onmoveup={() => moveMappingOverride(idx, -1)}
              onmovedown={() => moveMappingOverride(idx, 1)}
              ondelete={() => removeMappingOverride(key, idx)}
            >
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 items-end">
                <Input
                  label="M3U Channel Name"
                  value={key}
                  oninput={(e) => controller?.updateMappingOverrideKey(key, (e.target as HTMLInputElement).value, val)}
                />
                <Input
                  label="Target EPG Channel ID"
                  value={val}
                  oninput={(e) => controller?.updateMappingOverrideValue(key, (e.target as HTMLInputElement).value)}
                />
              </div>
            </AccordionCard>
          {/each}
        </div>
      {/if}
    </div>
  </Card>
</div>
