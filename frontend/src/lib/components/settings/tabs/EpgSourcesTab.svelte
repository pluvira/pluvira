<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import AccordionCard from '../../ui/AccordionCard.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { formatEpgSyncTiming } from '../utils/DashboardUtils';
  import ProTrialModal from '../../channels/modals/ProTrialModal.svelte';
  import { Zap, Sparkles, X, Clock, Radio, RotateCw } from '@lucide/svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';

  interface Props {
    config: GlobalConfig;
    expandSource?: string | null;
    controller?: SettingsController;
  }

  let { config = $bindable(), expandSource = null, controller }: Props = $props();

  $effect(() => {
    if (expandSource && config.epg_sources) {
      const idx = config.epg_sources.findIndex((s) => s.name === expandSource);
      if (idx !== -1) {
        controller?.setExpandedEpgIdx(idx);
      }
    }
  });

  const confirmController = new ConfirmController();
  let showTrialModal = $state(false);
  let isPro = $derived($licenseStore.isPro);
  let hasSlowSync = $derived(Boolean(controller?.hasSlowSyncWarning));

  function getEpgTiming(name: string): string {
    const s = controller?.epgSourcesStats?.find((item) => item.name === name);
    return s ? formatEpgSyncTiming(s.last_sync_programmes, s.last_sync_duration_s, s.is_turbo) : '';
  }

  function addEpgSource() {
    controller?.addEpgSource();
  }

  function requestRemoveEpgSource(index: number) {
    confirmController.requestConfirm('epg_source', () => {
      controller?.removeEpgSource(index);
      if (controller?.expandedEpgIdx === index) controller.setExpandedEpgIdx(null);
    });
  }

  function moveEpgSource(index: number, direction: number) {
    controller?.moveEpgSource(index, direction);
  }

  function testEpgConnection(url: string, index: number) {
    controller?.testEpgConnection(url, index);
  }
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  <div class="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border/30 pb-2 gap-2">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-xs text-muted-foreground">Configure global XMLTV schedule guides and EPG providers</span>
      {#if isPro}
        <Badge variant="primary" class="font-bold flex items-center gap-1">
          <Zap class="w-3 h-3 text-primary" />
          <span>Turbo Engine Active (Rust)</span>
        </Badge>
      {:else}
        <Badge variant="muted" class="font-medium">
          Standard Ingestion (Python)
        </Badge>
      {/if}
    </div>
    <Button variant="primary" size="sm" onclick={addEpgSource} class="text-xs !py-1 touch-btn shrink-0">
      + Add EPG Source
    </Button>
  </div>

  {#if hasSlowSync && !isPro}
    <div class="p-3.5 bg-primary/10 border border-primary/30 rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
      <div class="flex items-start gap-2.5">
        <Zap class="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-foreground text-sm">Accelerate TV Guide Updates</span>
          <p class="text-muted-foreground leading-relaxed">
            Your EPG guide took over 3 minutes to update. Pluvira Pro processes massive schedules in under 5 seconds with 95% less RAM.
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2 self-end sm:self-center shrink-0">
        <Button
          variant="primary"
          size="sm"
          onclick={() => (showTrialModal = true)}
          class="font-bold text-xs !py-1 flex items-center gap-1 touch-btn"
        >
          <Sparkles class="w-3.5 h-3.5" />
          <span>Upgrade to Pro</span>
        </Button>
        <button
          type="button"
          onclick={() => controller?.dismissEpgSlowNudge()}
          class="text-muted-foreground hover:text-foreground p-1 rounded cursor-pointer touch-btn"
          aria-label="Dismiss upgrade recommendation"
          title="Dismiss recommendation"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>
  {/if}

  {#if !config.epg_sources || config.epg_sources.length === 0}
    <div class="panel-box !items-center !justify-center !p-6">
      No global EPG sources defined. Click "+ Add EPG Source" to create one.
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each config.epg_sources as epg, idx (idx)}
        {@const isExpanded = controller?.expandedEpgIdx === idx}
        {@const isTesting = controller?.testingIndex === idx}
        {@const connStatus = controller?.epgStatusMap[idx]}
        {@const statusDot = !epg.enabled ? 'muted' : connStatus === 'ko' ? 'error' : 'success'}
        {@const statusDotTitle = !epg.enabled ? 'Disabled' : connStatus === 'ko' ? 'Connection Error' : 'Active'}
        <AccordionCard
          title={epg.name || 'Unnamed EPG Guide'}
          statusDot={statusDot}
          statusDotTitle={statusDotTitle}
          open={isExpanded}
          ontoggle={(isOpen) => controller?.setExpandedEpgIdx(isOpen ? idx : null)}
          index={idx}
          totalCount={config.epg_sources.length}
          showRefresh={true}
          onrefresh={() => { if (epg.enabled && controller) controller.refreshEpgSources([epg.name]); }}
          onmoveup={() => moveEpgSource(idx, -1)}
          onmovedown={() => moveEpgSource(idx, 1)}
          ondelete={() => requestRemoveEpgSource(idx)}
        >
          <Input label="Name" bind:value={epg.name} placeholder="e.g. EPG_Source_Alpha" />

          <div class="flex items-end gap-2 w-full">
            <div class="flex-1 min-w-0">
              <Input label="URL / File Path (.xml or .xml.gz)" bind:value={epg.url} placeholder="https://example.com/guide.xml.gz or file://..." />
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={isTesting}
              title="Test Connection"
              aria-label="Test Connection"
              onclick={() => testEpgConnection(epg.url, idx)}
              class="h-[36px] w-[36px] !p-0 flex items-center justify-center shrink-0 touch-btn"
            >
              {#if isTesting}
                <RotateCw class="w-4 h-4 animate-spin text-primary" />
              {:else}
                <Radio class="w-4 h-4 text-muted-foreground" />
              {/if}
            </Button>
          </div>

          <label class="flex items-center gap-2 cursor-pointer text-muted-foreground w-fit">
            <input type="checkbox" bind:checked={epg.enabled} class="rounded text-primary" />
            <span class="font-bold text-xs">Enable</span>
          </label>

          <Input label="EPG Custom User-Agent" bind:value={epg.user_agent} placeholder="Inherit global if empty..." />

          {@const timingStr = getEpgTiming(epg.name)}
          {#if timingStr}
            <div class="flex items-center gap-1.5 text-muted-foreground text-[11px] pt-0.5">
              <Clock class="w-3.5 h-3.5 text-muted-foreground/70 shrink-0" />
              <span>{timingStr}</span>
            </div>
          {/if}
        </AccordionCard>
      {/each}
    </div>
  {/if}

  <ProTrialModal bind:open={showTrialModal} />
</div>