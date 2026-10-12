<script lang="ts">
  import type { GlobalConfig, Source } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import AccordionCard from '../../ui/AccordionCard.svelte';
  import { RewriteRulesManager } from '../sections';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import { Radio, RotateCw } from '@lucide/svelte';
  import Badge from '../../ui/Badge.svelte';
  import { formatNewlineList } from '$lib/utils/stringUtils';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { formatBslSourcesQuota, isSourcesQuotaExceeded } from '$lib/utils/bslUtils';

  interface Props {
    config: GlobalConfig;
    expandSource?: string | null;
    controller?: SettingsController;
  }

  let { config = $bindable(), expandSource = null, controller }: Props = $props();

  const confirmController = new ConfirmController();
  let isPro = $derived($licenseStore.isPro);
  let activeSourcesCount = $derived((config.sources || []).filter((s) => s.enabled).length);
  let isQuotaExceeded = $derived(isSourcesQuotaExceeded(activeSourcesCount, isPro));

  function toggleAllowedOpen(sourceIdx: number, val?: boolean) {
    controller?.toggleAllowedOpen(sourceIdx, val);
  }

  function toggleDeniedOpen(sourceIdx: number, val?: boolean) {
    controller?.toggleDeniedOpen(sourceIdx, val);
  }

  function toggleRewritesSectionOpen(sourceIdx: number, val?: boolean) {
    controller?.toggleRewritesSectionOpen(sourceIdx, val);
  }

  $effect(() => {
    if (expandSource && config.sources) {
      const idx = config.sources.findIndex((s) => s.name === expandSource);
      if (idx !== -1) {
        controller?.setExpandedIptvIdx(idx);
      }
    }
  });

  function addSource() {
    controller?.addSource();
  }

  function requestRemoveSource(index: number) {
    confirmController.requestConfirm('iptv_source', () => {
      controller?.removeSource(index);
      if (controller?.expandedIptvIdx === index) controller.setExpandedIptvIdx(null);
    });
  }

  function moveSource(index: number, direction: number) {
    controller?.moveSource(index, direction);
  }

  function testSourceConnection(url: string, index: number) {
    controller?.testSourceConnection(url, index);
  }

  function toggleSourceOverride(src: Source) {
    controller?.toggleSourceOverride(src);
  }
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  <div class="flex items-center justify-between border-b border-border/30 pb-2 flex-wrap gap-2">
    <div class="flex items-center gap-2">
      <span class="text-xs text-muted-foreground">Configure IPTV M3U playlist sources and provider settings</span>
      <Badge variant={isQuotaExceeded ? 'warning' : 'muted'} class="text-[10px]">
        {formatBslSourcesQuota(activeSourcesCount, isPro)}
      </Badge>
    </div>
    <Button variant="primary" size="sm" onclick={addSource} class="text-xs !py-1 touch-btn">
      + Add IPTV Source
    </Button>
  </div>

  {#if !config.sources || config.sources.length === 0}
    <div class="panel-box !items-center !justify-center !p-6">
      No IPTV sources defined. Click "+ Add IPTV Source" to create one.
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each config.sources as src, idx (idx)}
        {@const isExpanded = controller?.expandedIptvIdx === idx}
        {@const isTesting = controller?.testingSourceIndex === idx}
        {@const connStatus = controller?.iptvStatusMap[idx]}
        {@const statusDot = !src.enabled ? 'muted' : connStatus === 'ko' ? 'error' : 'success'}
        {@const statusDotTitle = !src.enabled ? 'Disabled' : connStatus === 'ko' ? 'Connection Error' : 'Active'}
        <AccordionCard
          title={src.name || 'Unnamed IPTV Source'}
          statusDot={statusDot}
          statusDotTitle={statusDotTitle}
          open={isExpanded}
          ontoggle={(isOpen) => controller?.setExpandedIptvIdx(isOpen ? idx : null)}
          index={idx}
          totalCount={config.sources.length}
          showRefresh={true}
          onrefresh={() => { if (src.enabled && controller) controller.refreshSources([src.name]); }}
          onmoveup={() => moveSource(idx, -1)}
          onmovedown={() => moveSource(idx, 1)}
          ondelete={() => requestRemoveSource(idx)}
        >
          <Input label="Name" bind:value={src.name} placeholder="e.g. IPTV_Source_Alpha" />

          <div class="flex items-end gap-2 w-full">
            <div class="flex-1 min-w-0">
              <Input label="URL / File Path" bind:value={src.m3u_url} placeholder="https://example.com/playlist.m3u or file://..." />
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={isTesting}
              onclick={() => testSourceConnection(src.m3u_url, idx)}
              class="h-[36px] w-[36px] !p-0 flex items-center justify-center shrink-0 touch-btn"
              title="Test Connection"
              aria-label="Test Connection"
            >
              {#if isTesting}
                <RotateCw class="w-4 h-4 animate-spin text-primary" />
              {:else}
                <Radio class="w-4 h-4 text-muted-foreground" />
              {/if}
            </Button>
          </div>

          <label class="flex items-center gap-2 cursor-pointer text-muted-foreground w-fit">
            <input type="checkbox" bind:checked={src.enabled} class="rounded text-primary" />
            <span class="font-bold text-xs">Enable</span>
          </label>

          <div class="border-t border-border/20 pt-4 mt-2">
            <label class="flex items-center gap-2 cursor-pointer text-muted-foreground font-bold mb-4">
              <input type="checkbox" checked={Boolean(src.settings)} onchange={() => toggleSourceOverride(src)} class="rounded text-primary" />
              <span>Enable Source-Specific Settings Overrides</span>
            </label>

            {#if src.settings}
              <div class="flex flex-col gap-4 mt-2">
                <Input label="Source-Specific User-Agent" bind:value={src.settings.user_agent} placeholder="Inherit global if empty..." />

                <label class="flex items-center gap-2 cursor-pointer text-muted-foreground font-bold">
                  <input type="checkbox" bind:checked={src.settings.force_proxy} class="rounded text-primary" />
                  <span class="text-xs">Force Server CORS Proxy for this source</span>
                </label>

                <!-- Allowed Channels Accordion -->
                <AccordionCard
                  title="Allowed Channels List"
                  open={controller ? Boolean(controller.openAllowedMap[idx]) : false}
                  ontoggle={(val) => toggleAllowedOpen(idx, val)}
                  badgeText={src.settings.allow_channels?.length ? `${src.settings.allow_channels.length} Channels` : 'Empty'}
                  badgeVariant={src.settings.allow_channels?.length ? 'primary' : 'muted'}
                  showMove={false}
                  showDelete={false}
                >
                  <div class="flex flex-col gap-2">
                    <span class="text-[10px] text-muted-foreground">If populated, only these channel names will be kept. Enter one name per line:</span>
                    <textarea
                      value={formatNewlineList(src.settings.allow_channels)}
                      oninput={(e) => controller?.updateAllowChannels(idx, (e.target as HTMLTextAreaElement).value)}
                      rows={4}
                      placeholder="e.g. Channel 1&#10;Channel 2"
                      class="textarea-base"
                    ></textarea>
                  </div>
                </AccordionCard>

                <!-- Denied Channels Accordion -->
                <AccordionCard
                  title="Denied Channels List"
                  open={controller ? Boolean(controller.openDeniedMap[idx]) : false}
                  ontoggle={(val) => toggleDeniedOpen(idx, val)}
                  badgeText={src.settings.deny_channels?.length ? `${src.settings.deny_channels.length} Channels` : 'Empty'}
                  badgeVariant={src.settings.deny_channels?.length ? 'warning' : 'muted'}
                  showMove={false}
                  showDelete={false}
                >
                  <div class="flex flex-col gap-2">
                    <span class="text-[10px] text-muted-foreground">Explicit list of channel names to exclude. Enter one name per line:</span>
                    <textarea
                      value={formatNewlineList(src.settings.deny_channels)}
                      oninput={(e) => controller?.updateDenyChannels(idx, (e.target as HTMLTextAreaElement).value)}
                      rows={4}
                      placeholder="e.g. Channel 3&#10;Channel 4"
                      class="textarea-base"
                    ></textarea>
                  </div>
                </AccordionCard>

                <!-- Source Metadata Rewrites Accordion -->
                <AccordionCard
                  title="Source Metadata Rewrites"
                  open={controller ? Boolean(controller.openRewritesSectionMap[idx]) : false}
                  ontoggle={(val) => toggleRewritesSectionOpen(idx, val)}
                  badgeText={src.settings.rewrites?.length ? `${src.settings.rewrites.length} Rules` : '0 Rules'}
                  badgeVariant="muted"
                  showMove={false}
                  showDelete={false}
                >
                  <RewriteRulesManager
                    bind:rules={src.settings.rewrites}
                    description="Source-specific rules applied sequentially before global rewrites"
                    storageKeyPrefix={`st_iptv_rw_${idx}`}
                  />
                </AccordionCard>
              </div>
            {/if}
          </div>
        </AccordionCard>
      {/each}
    </div>
  {/if}
</div>