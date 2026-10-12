<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import type { BackupController } from '../utils/BackupController.svelte';
  import { formatDiffSummary } from '../utils/BackupUtils';
  import { ShieldAlert, AlertTriangle, FileCheck } from '@lucide/svelte';

  interface Props {
    controller: BackupController;
    open?: boolean;
    onsuccess?: () => void;
    onclose?: () => void;
  }

  let {
    controller,
    open = $bindable(),
    onsuccess,
    onclose
  }: Props = $props();

  let diffRows = $derived(formatDiffSummary(controller.validationResult?.diff));
  let isSanitized = $derived(Boolean(controller.validationResult?.sanitized_detected));
  let isMigrationRequired = $derived(Boolean(controller.validationResult?.migration_required));

  function handleClose() {
    open = false;
    controller.resetStaging();
    onclose?.();
  }

  async function handleConfirm() {
    await controller.executeImport(() => {
      open = false;
      onsuccess?.();
    });
  }
</script>

<Dialog bind:open title="Backup Import Pre-Flight Validation" onclose={handleClose} class="max-w-2xl">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={handleClose} class="touch-btn">Cancel</Button>
    <Button
      variant="primary"
      size="sm"
      disabled={controller.importing || (controller.validationResult !== null && !controller.validationResult.valid)}
      onclick={handleConfirm}
      class="font-bold flex items-center gap-1.5 touch-btn"
    >
      {#if controller.importing}
        <span class="spinner !w-3.5 !h-3.5 mr-1"></span>
        <span>Importing...</span>
      {:else}
        <FileCheck class="w-4 h-4" />
        <span>Confirm & Import</span>
      {/if}
    </Button>
  {/snippet}

  <div class="flex flex-col gap-4 w-full text-xs">
    {#if controller.stagedBundle}
      <div class="panel-mono !p-3 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="text-muted-foreground font-bold">Bundle App Version:</span>
          <span class="font-bold text-foreground">{controller.stagedBundle.app_version || '0.1.0'}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-muted-foreground font-bold">Exported Date:</span>
          <span class="text-foreground">{controller.stagedBundle.exported_at || 'Unknown'}</span>
        </div>
      </div>
    {/if}

    {#if isSanitized}
      <div class="banner-warning">
        <div class="flex items-start gap-2.5">
          <ShieldAlert class="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <div class="flex flex-col gap-0.5 text-left">
            <span class="font-bold text-foreground text-xs">Sanitized Backup Detected</span>
            <span class="text-muted-foreground text-[11px] leading-relaxed">
              Credentials and sensitive webhook tokens are masked. Existing active passwords and keys currently on disk will be preserved.
            </span>
          </div>
        </div>
      </div>
    {/if}

    {#if isMigrationRequired}
      <div class="banner-warning">
        <div class="flex items-start gap-2.5">
          <AlertTriangle class="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <div class="flex flex-col gap-0.5 text-left">
            <span class="font-bold text-foreground text-xs">Schema Migration Required</span>
            <span class="text-muted-foreground text-[11px] leading-relaxed">
              This backup uses schema v{controller.validationResult?.bundle_version} and will be automatically migrated to v{controller.validationResult?.target_version}.
            </span>
          </div>
        </div>
      </div>
    {/if}

    <div class="surface-card p-3 flex flex-col gap-2 border border-border">
      <span class="font-bold text-foreground text-xs uppercase tracking-wider">Select Import Strategy</span>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label
          class="flex items-start gap-2.5 p-2.5 rounded border cursor-pointer transition-colors touch-btn {controller.importMode === 'destructive' ? 'bg-primary/10 border-primary' : 'bg-background border-border/40 hover:bg-muted'}"
        >
          <input
            type="radio"
            name="import_mode"
            value="destructive"
            checked={controller.importMode === 'destructive'}
            onchange={() => controller.setImportMode('destructive')}
            class="mt-0.5 text-primary cursor-pointer"
          />
          <div class="flex flex-col gap-0.5">
            <span class="font-bold text-foreground">Total Overwrite (Destructive)</span>
            <span class="text-[11px] text-muted-foreground">Replaces existing configuration and schedules completely.</span>
          </div>
        </label>

        <label
          class="flex items-start gap-2.5 p-2.5 rounded border cursor-pointer transition-colors touch-btn {controller.importMode === 'merge' ? 'bg-primary/10 border-primary' : 'bg-background border-border/40 hover:bg-muted'}"
        >
          <input
            type="radio"
            name="import_mode"
            value="merge"
            checked={controller.importMode === 'merge'}
            onchange={() => controller.setImportMode('merge')}
            class="mt-0.5 text-primary cursor-pointer"
          />
          <div class="flex flex-col gap-0.5">
            <span class="font-bold text-foreground">Incremental Merge</span>
            <span class="text-[11px] text-muted-foreground">Appends and updates items without deleting unreferenced ones.</span>
          </div>
        </label>
      </div>
    </div>

    <div class="flex flex-col gap-1.5 w-full">
      <span class="font-bold text-muted-foreground text-xs uppercase tracking-wider">Configuration Entities Diff</span>
      <div class="overflow-x-auto w-full border border-border/40 rounded-md max-h-48 md:max-h-60 overflow-y-auto">
        <table class="table-base">
          <thead>
            <tr>
              <th class="table-th">Entity Category</th>
              <th class="table-th text-center w-24">Added</th>
              <th class="table-th text-center w-24">Updated</th>
              <th class="table-th text-center w-24">Removed</th>
            </tr>
          </thead>
          <tbody>
            {#each diffRows as row (row.key)}
              <tr class="table-tr">
                <td class="table-td font-bold text-foreground">{row.label}</td>
                <td class="table-td text-center">
                  {#if row.added > 0}
                    <Badge variant="success">+{row.added}</Badge>
                  {:else}
                    <span class="text-muted-foreground">—</span>
                  {/if}
                </td>
                <td class="table-td text-center">
                  {#if row.updated > 0}
                    <Badge variant="warning">~{row.updated}</Badge>
                  {:else}
                    <span class="text-muted-foreground">—</span>
                  {/if}
                </td>
                <td class="table-td text-center">
                  {#if row.removed > 0}
                    <Badge variant="error">-{row.removed}</Badge>
                  {:else}
                    <span class="text-muted-foreground">—</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    {#if controller.validationResult?.diff?.settings_modified && controller.validationResult.diff.settings_modified.length > 0}
      <div class="panel-box !p-2.5 flex flex-col gap-1">
        <span class="text-[10px] font-bold text-primary uppercase">Modified Settings Keys:</span>
        <div class="flex flex-wrap gap-1">
          {#each controller.validationResult.diff.settings_modified as key (key)}
            <Badge variant="muted">{key}</Badge>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</Dialog>
