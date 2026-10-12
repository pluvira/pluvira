<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { NOTIFICATION_PRESETS } from '../utils/SettingsUtils';
  import { Download, Radio, HardDrive, Trash2, ChevronDown, ChevronRight } from '@lucide/svelte';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();

  let isPro = $derived($licenseStore.isPro);
  let isNotificationsActive = $derived(isPro && Boolean(config.settings?.notifications?.enabled));

  const confirmController = new ConfirmController();

  function toggleSection(section: string) {
    controller?.toggleNotificationSection(section);
  }

  function addUrl() {
    controller?.addNotificationUrl();
  }

  function requestRemoveUrl(url: string) {
    confirmController.requestConfirm('notification_url', () => {
      controller?.removeNotificationUrl(url);
    });
  }

  function testNotification(url?: string) {
    controller?.testNotification(url, isPro);
  }

  function applyPreset(presetName: string) {
    controller?.applyNotificationPreset(presetName, isPro);
  }

</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  {#if !isPro}
    <div class="banner-warning">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 w-full">
        <span class="text-xs text-foreground">
          <strong class="font-bold">Core Edition:</strong> Basic status events logged to console. Pro Edition required for multi-target webhooks, custom event matrices, and thresholds.
        </span>
      </div>
    </div>
  {/if}

  <!-- Master Toggle -->
  <Card title="Universal Notification System">
    {#if config.settings.notifications}
      <label class="flex items-center gap-2 cursor-pointer text-muted-foreground font-bold">
        <input
          type="checkbox"
          bind:checked={config.settings.notifications.enabled}
          disabled={!isPro}
          class="rounded text-primary cursor-pointer disabled:cursor-not-allowed"
        />
        <span>Enable Global Event Notifications (master toggle)</span>
      </label>
    {/if}
  </Card>

  <fieldset disabled={!isNotificationsActive} class="contents disabled:opacity-50 disabled:pointer-events-none">
  <!-- URLs Editor -->
  <Card title="Notification Endpoints & Webhooks">
    <div class="flex flex-col gap-3">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/30 pb-2">
        <span class="text-xs text-muted-foreground">Specify notification endpoints (Telegram, Discord, Slack, Email, Webhooks, etc.)</span>
        {#if config.settings.notifications?.urls && config.settings.notifications.urls.length > 0}
          <Button
            variant="secondary"
            size="sm"
            disabled={controller?.testingUrl !== null}
            onclick={() => testNotification()}
            class="text-[11px] font-bold touch-btn shrink-0"
          >
            {controller?.testingUrl === 'all' ? 'Sending...' : 'Test All Endpoints'}
          </Button>
        {/if}
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-3 items-end panel-box !p-3">
        <div class="sm:col-span-2 md:col-span-3">
          <Input label="Notification Endpoint URL" bind:value={controller!.newNotificationUrl} placeholder="e.g. https://discord.com/api/webhooks/... or tgram://..." />
        </div>
        <Button variant="primary" size="sm" onclick={addUrl} class="font-bold text-xs h-[36px] w-full touch-btn">
          + Add Destination
        </Button>
      </div>

      {#if !config.settings.notifications?.urls || config.settings.notifications.urls.length === 0}
        <div class="panel-box !items-center !justify-center !p-4">
          No notification endpoints configured.
        </div>
      {:else}
        <div class="overflow-x-auto w-full border border-border/30 rounded">
          <table class="table-base">
            <tbody>
              {#each config.settings.notifications.urls as url (url)}
                {@const isTesting = controller?.testingUrl === url}
                <tr class="table-tr">
                  <td class="table-td font-mono text-muted-foreground break-all">{url}</td>
                  <td class="table-td w-36 text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <Button variant="outline" size="sm" disabled={isTesting} onclick={() => testNotification(url)} class="!py-0.5 !px-2 text-[10px] touch-btn">
                        {isTesting ? 'Sending...' : 'Test Send'}
                      </Button>
                      <Button variant="ghost" size="sm" onclick={() => requestRemoveUrl(url)} class="!p-1 text-xs text-destructive hover:opacity-80" title="Delete URL">
                        <Trash2 class="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </Card>

  <!-- Presets & Matrix -->
  <Card title="Event Triggers Presets Matrix">
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-1.5 flex-wrap border-b border-border/20 pb-3">
        {#each NOTIFICATION_PRESETS as p (p.value)}
          <button
            type="button"
            disabled={!isPro}
            onclick={() => applyPreset(p.value)}
            class="px-2.5 py-0.5 rounded text-[10px] font-semibold bg-secondary/70 hover:bg-secondary text-secondary-foreground border border-border/30 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed touch-btn"
            title={isPro ? `Apply ${p.label} preset` : 'Pro Edition required for presets'}
          >
            {p.label}
          </button>
        {/each}
      </div>

      <div class="flex flex-col gap-2">
        <!-- Section A: Acquisition -->
        <div class="surface-card overflow-hidden !p-0">
          <button
            type="button"
            onclick={() => toggleSection('runner')}
            class="w-full flex items-center justify-between px-4 py-2.5 surface-header font-bold text-foreground text-xs cursor-pointer select-none text-left"
          >
            <div class="flex items-center gap-2">
              <Download class="w-4 h-4" />
              <span>Acquisition & Runner Events</span>
            </div>
            {#if controller ? controller.notificationSections.runner : true}
              <ChevronDown class="w-4 h-4" />
            {:else}
              <ChevronRight class="w-4 h-4" />
            {/if}
          </button>
          {#if (controller ? controller.notificationSections.runner : true) && config.settings.notifications?.events}
            <div class="p-4 flex flex-col gap-3">
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.update_success} class="rounded text-primary" />
                <span>Update Success (complete playlist/EPG runs)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.update_failure} class="rounded text-primary" />
                <span>Update Failure (unhandled parser/network exceptions)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.source_download_failure} class="rounded text-primary" />
                <span>Source Download Failure (unreachable provider URLs)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.source_empty_malformed} class="rounded text-primary" />
                <span>Source Empty/Malformed (0 parsed channel records)</span>
              </label>
            </div>
          {/if}
        </div>

        <!-- Section B: Scanner -->
        <div class="surface-card overflow-hidden !p-0">
          <button
            type="button"
            onclick={() => toggleSection('scanner')}
            class="w-full flex items-center justify-between px-4 py-2.5 surface-header font-bold text-foreground text-xs cursor-pointer select-none text-left"
          >
            <div class="flex items-center gap-2">
              <Radio class="w-4 h-4" />
              <span>Link Scanner & Stream Health</span>
            </div>
            {#if controller ? controller.notificationSections.scanner : true}
              <ChevronDown class="w-4 h-4" />
            {:else}
              <ChevronRight class="w-4 h-4" />
            {/if}
          </button>
          {#if (controller ? controller.notificationSections.scanner : true) && config.settings.notifications?.events}
            <div class="p-4 flex flex-col gap-3">
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.link_test_report} class="rounded text-primary" />
                <span>Scanner Report (summary statistics sent after polite runs)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.link_ko_detected} class="rounded text-primary" />
                <span>Link KO Detected (alerts when a channel stream goes offline)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.link_recovered} class="rounded text-primary" />
                <span>Link Recovered (alerts when an offline channel goes back online)</span>
              </label>
            </div>
          {/if}
        </div>

        <!-- Section C: Hardware -->
        <div class="surface-card overflow-hidden !p-0">
          <button
            type="button"
            onclick={() => toggleSection('hardware')}
            class="w-full flex items-center justify-between px-4 py-2.5 surface-header font-bold text-foreground text-xs cursor-pointer select-none text-left"
          >
            <div class="flex items-center gap-2">
              <HardDrive class="w-4 h-4" />
              <span>Hardware & Storage Health</span>
            </div>
            {#if controller ? controller.notificationSections.hardware : true}
              <ChevronDown class="w-4 h-4" />
            {:else}
              <ChevronRight class="w-4 h-4" />
            {/if}
          </button>
          {#if (controller ? controller.notificationSections.hardware : true) && config.settings.notifications?.events}
            <div class="p-4 flex flex-col gap-3">
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.atomic_write_failure} class="rounded text-primary" />
                <span>Atomic Write Failure (ZFS/SMR storage permission or persistence errors)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" bind:checked={config.settings.notifications.events.disk_space_warning} class="rounded text-primary" />
                <span>RAM Disk Space Warning (low free space on temporary directory /dev/shm)</span>
              </label>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2 border-t border-border/20 pt-3">
                <Input type="number" label="Min Free Storage Warning Threshold (MB)" bind:value={config.settings.notifications.events.min_ram_disk_free_mb} />
                <Input type="number" label="Max Safe CPU Load (%)" bind:value={config.settings.notifications.events.cpu_load_threshold_pct} />
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </Card>
  </fieldset>
</div>