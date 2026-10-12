<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Input from '../../ui/Input.svelte';
  import Dialog from '../../ui/Dialog.svelte';
  import { BackupPreviewModal } from '../modals';
  import { BackupController } from '../utils/BackupController.svelte';
  import { formatByteSize } from '../utils/BackupUtils';
  import Checkbox from '../../ui/Checkbox.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { Download, Upload, ShieldCheck, Cloud, Lock, Trash2, Pin, PinOff, RotateCcw } from '@lucide/svelte';

  interface Props {
    onimportsuccess?: () => void;
  }

  let { onimportsuccess }: Props = $props();

  const backupController = new BackupController();
  let fileInputElement: HTMLInputElement | null = $state(null);
  let isDragging = $state(false);
  let isPro = $derived($licenseStore.isPro);

  function triggerFileInput() {
    fileInputElement?.click();
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }

  function handleDragLeave() {
    isDragging = false;
  }

  onMount(() => {
    backupController.loadCloudSnapshots();
  });

  function handleFileInputChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) {
      backupController.handleFileSelected(file);
      target.value = '';
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) backupController.handleFileSelected(file);
  }

  function handlePromptUpload() {
    backupController.activeCloudAction = 'upload';
    backupController.passphrase = '';
    backupController.showPassphraseModal = true;
  }

  function handlePromptRestore(snapshot: any) {
    backupController.targetCloudSnapshot = snapshot;
    backupController.activeCloudAction = 'restore';
    backupController.passphrase = '';
    backupController.showPassphraseModal = true;
  }

  function handlePromptRestoreLatest() {
    backupController.targetCloudSnapshot = null;
    backupController.activeCloudAction = 'restore_latest';
    backupController.passphrase = '';
    backupController.showPassphraseModal = true;
  }
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <Card title="Export Configuration & Schedules Bundle">
    <div class="flex flex-col gap-4 w-full">
      <span class="text-xs text-muted-foreground leading-relaxed">
        Create and download a unified JSON backup bundle containing all global settings, IPTV playlist sources, EPG guide sources, metadata rewrites, channel merges, and scheduled update jobs.
      </span>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 items-stretch">
        <div class="panel-box !p-4 flex flex-col justify-between gap-3 border border-border">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <Download class="w-4 h-4 text-primary" />
              <span class="font-bold text-foreground text-sm">Full Complete Backup</span>
            </div>
            <span class="text-muted-foreground text-xs leading-relaxed">
              Includes all configuration and active credentials (admin passwords, JWT keys, and notification webhook URLs). Intended for private backup and server migrations.
            </span>
          </div>

          <Button
            variant="primary"
            size="sm"
            disabled={backupController.exporting}
            onclick={() => backupController.exportBackup(false)}
            class="font-bold w-full flex items-center justify-center gap-2 touch-btn"
          >
            <Download class="w-4 h-4" />
            <span>{backupController.exporting ? 'Generating...' : 'Download Full Backup'}</span>
          </Button>
        </div>

        <div class="panel-box !p-4 flex flex-col justify-between gap-3 border border-border">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <ShieldCheck class="w-4 h-4 text-primary" />
              <span class="font-bold text-foreground text-sm">Sanitized Shareable Backup</span>
              <Badge variant="success">SAFE TO SHARE</Badge>
            </div>
            <span class="text-muted-foreground text-xs leading-relaxed">
              Masks all sensitive secrets, passwords, and private webhook tokens with placeholder tags. Perfect for sharing templates, support diagnosing, or public setups.
            </span>
          </div>

          <Button
            variant="outline"
            size="sm"
            disabled={backupController.exporting}
            onclick={() => backupController.exportBackup(true)}
            class="font-bold w-full flex items-center justify-center gap-2 touch-btn"
          >
            <ShieldCheck class="w-4 h-4 text-primary" />
            <span>{backupController.exporting ? 'Generating...' : 'Download Sanitized Backup'}</span>
          </Button>
        </div>
      </div>
    </div>
  </Card>

  <Card title="Import & Restore Configuration">
    <div class="flex flex-col gap-4 w-full">
      <span class="text-xs text-muted-foreground leading-relaxed">
        Restore or merge settings from a previous JSON backup bundle. The file will be checked by the pre-flight validation engine before any changes are written to disk.
      </span>

      <input
        bind:this={fileInputElement}
        type="file"
        accept=".json,application/json"
        onchange={handleFileInputChange}
        class="hidden"
      />

      <div
        role="button"
        tabindex="0"
        onclick={triggerFileInput}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') triggerFileInput(); }}
        ondrop={handleDrop}
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        class="border-2 border-dashed rounded-lg p-6 sm:p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors select-none {isDragging ? 'border-primary bg-primary/10' : 'border-border/60 hover:border-border hover:bg-card/50'}"
      >
        {#if backupController.validating}
          <span class="spinner !w-8 !h-8 text-primary"></span>
          <span class="text-xs font-bold text-foreground">Reading and validating backup bundle...</span>
        {:else}
          <div class="p-3 rounded-full bg-card border border-border">
            <Upload class="w-6 h-6 text-primary" />
          </div>
          <div class="flex flex-col items-center gap-1 text-center">
            <span class="font-bold text-sm text-foreground">Click to upload or drag & drop backup JSON file</span>
            <span class="text-xs text-muted-foreground">Supported format: .json (Unified Backup Bundle)</span>
          </div>
        {/if}
      </div>
    </div>
  </Card>

  <Card title="Zero-Knowledge E2EE Cloud Backup Vault">
    <div class="flex flex-col gap-4 w-full">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <span class="text-xs text-muted-foreground leading-relaxed">
          Store client-side encrypted backup snapshots in Pluvira Cloud. Backups are encrypted with AES-256-GCM using your private passphrase. Decryption keys never touch the server.
        </span>
        <div class="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={backupController.cloudSnapshots.length === 0}
            onclick={handlePromptRestoreLatest}
            class="font-bold flex items-center gap-2 whitespace-nowrap touch-btn shrink-0"
            title="Restore latest snapshot directly"
          >
            <RotateCcw class="w-4 h-4" />
            <span>Restore Latest</span>
          </Button>
          <Button
            variant="primary"
            size="sm"
            onclick={handlePromptUpload}
            class="font-bold flex items-center gap-2 whitespace-nowrap touch-btn shrink-0"
          >
            <Cloud class="w-4 h-4" />
            <span>Create Cloud Snapshot</span>
          </Button>
        </div>
      </div>

      {#if backupController.loadingCloud}
        <div class="flex items-center gap-2 p-4 text-muted-foreground text-xs">
          <span class="spinner !w-4 !h-4 text-primary"></span>
          <span>Connecting to cloud vault...</span>
        </div>
      {:else if backupController.cloudSnapshots.length === 0}
        <div class="panel-box !p-6 flex flex-col items-center justify-center gap-2 text-center border border-border">
          <Lock class="w-6 h-6 text-muted-foreground" />
          <span class="text-xs font-bold text-foreground">No Cloud Snapshots Stored</span>
          <span class="text-xs text-muted-foreground max-w-md">
            Click "Create Cloud Snapshot" to encrypt and store your configuration vault in Pluvira Cloud.
          </span>
        </div>
      {:else}
        <div class="overflow-x-auto w-full border border-border rounded-lg">
          <table class="table-base w-full text-xs">
            <thead>
              <tr class="bg-card text-muted-foreground border-b border-border">
                <th class="p-3 text-left">Label & Checksum</th>
                <th class="p-3 text-center w-28">Size</th>
                <th class="p-3 text-center w-40">Created At</th>
                <th class="p-3 text-right w-36">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each backupController.cloudSnapshots as snap (snap.id)}
                <tr class="border-b border-border/50 hover:bg-card/40">
                  <td class="p-3">
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-foreground">{snap.snapshot_label || 'Manual Cloud Backup'}</span>
                        {#if snap.is_pinned}
                          <Badge variant="warning" class="inline-flex items-center gap-1 font-bold text-[10px] py-0 px-1.5 border-warning/40">
                            <Pin class="w-3 h-3 fill-current" />
                            <span>PINNED</span>
                          </Badge>
                        {/if}
                      </div>
                      <span class="text-[10px] text-muted-foreground font-mono">{snap.sha256_checksum.slice(0, 16)}...</span>
                    </div>
                  </td>
                  <td class="p-3 text-center font-mono text-muted-foreground">
                    {formatByteSize(snap.size_bytes)}
                  </td>
                  <td class="p-3 text-center text-muted-foreground">
                    {new Date(snap.created_at).toLocaleString()}
                  </td>
                  <td class="p-3 text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={backupController.pinLoading[snap.id] || !isPro}
                        onclick={() => backupController.togglePinSnapshot(snap, isPro)}
                        class="touch-btn p-1.5 {snap.is_pinned ? 'text-warning hover:bg-warning/10' : 'text-muted-foreground hover:bg-card/50'}"
                        title={!isPro ? 'Pinning requires Pro edition' : snap.is_pinned ? 'Unpin snapshot' : 'Pin snapshot'}
                      >
                        {#if snap.is_pinned}
                          <PinOff class="w-4 h-4" />
                        {:else}
                          <Pin class="w-4 h-4" />
                        {/if}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onclick={() => handlePromptRestore(snap)}
                        class="touch-btn text-xs py-1"
                      >
                        Restore
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onclick={() => backupController.deleteCloudSnapshot(snap.id)}
                        class="text-destructive hover:bg-destructive/10 touch-btn p-1.5"
                        title="Delete Snapshot"
                      >
                        <Trash2 class="w-4 h-4" />
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
</div>

<Dialog
  bind:open={backupController.showPassphraseModal}
  title={backupController.activeCloudAction === 'upload' ? 'Encrypt & Vault Cloud Backup' : backupController.activeCloudAction === 'restore_latest' ? 'Decrypt Latest Cloud Snapshot' : 'Decrypt Cloud Snapshot'}
>
  <div class="flex flex-col gap-4 p-4 text-xs">
    {#if backupController.activeCloudAction === 'upload'}
      <span class="text-muted-foreground leading-relaxed">
        Enter a strong encryption passphrase (min 8 characters). This passphrase will derive an AES-256-GCM encryption key.
        <strong>Pluvira Cloud does not store this passphrase; if lost, your backup cannot be recovered.</strong>
      </span>

      <Input
        label="Snapshot Label (Optional)"
        placeholder="e.g. Pre-Update Manual Snapshot"
        bind:value={backupController.snapshotLabel}
      />

      {#if isPro}
        <div class="flex items-center gap-2 mt-1">
          <Checkbox
            id="pin-snapshot-checkbox"
            checked={backupController.pinSnapshotOnCreate}
            onCheckedChange={(checked) => { backupController.pinSnapshotOnCreate = Boolean(checked); }}
            label="Pin snapshot (lock against FIFO auto-rotation)"
          />
        </div>
      {/if}
    {:else if backupController.activeCloudAction === 'restore_latest'}
      <span class="text-muted-foreground leading-relaxed">
        Enter your passphrase to decrypt and restore the latest cloud backup snapshot directly.
      </span>
    {:else}
      <span class="text-muted-foreground leading-relaxed">
        Enter the passphrase used to encrypt this snapshot to decrypt and preview its configuration.
      </span>
    {/if}

    <Input
      type="password"
      label="Zero-Knowledge Passphrase"
      placeholder="••••••••••••"
      bind:value={backupController.passphrase}
    />

    <div class="flex justify-end gap-2 mt-2">
      <Button
        variant="ghost"
        size="sm"
        onclick={() => { backupController.showPassphraseModal = false; }}
        class="touch-btn"
      >
        Cancel
      </Button>
      {#if backupController.activeCloudAction === 'upload'}
        <Button
          variant="primary"
          size="sm"
          disabled={backupController.uploadingCloud}
          onclick={() => backupController.executeCloudUpload()}
          class="font-bold touch-btn"
        >
          {backupController.uploadingCloud ? 'Encrypting & Uploading...' : 'Encrypt & Upload'}
        </Button>
      {:else if backupController.activeCloudAction === 'restore_latest'}
        <Button
          variant="primary"
          size="sm"
          disabled={backupController.validating}
          onclick={() => backupController.executeLatestCloudRestore()}
          class="font-bold touch-btn"
        >
          {backupController.validating ? 'Decrypting Latest...' : 'Decrypt & Restore Latest'}
        </Button>
      {:else}
        <Button
          variant="primary"
          size="sm"
          disabled={backupController.validating}
          onclick={() => backupController.executeCloudRestore()}
          class="font-bold touch-btn"
        >
          {backupController.validating ? 'Decrypting...' : 'Decrypt & Restore'}
        </Button>
      {/if}
    </div>
  </div>
</Dialog>

<BackupPreviewModal
  controller={backupController}
  bind:open={backupController.showPreviewModal}
  onsuccess={onimportsuccess}
/>
