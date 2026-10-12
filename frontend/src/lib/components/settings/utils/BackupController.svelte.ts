import { api } from '$lib/api/client';
import type { BackupBundle, BackupValidationResult, BackupImportPayload, CloudBackupSnapshot } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import { readBackupFileAsJson } from './BackupUtils';

export class BackupController {
  public exporting = $state(false);
  public validating = $state(false);
  public importing = $state(false);
  public stagedBundle = $state<BackupBundle | null>(null);
  public validationResult = $state<BackupValidationResult | null>(null);
  public importMode = $state<'destructive' | 'merge'>('destructive');
  public showPreviewModal = $state(false);

  // Cloud E2EE Vault State
  public cloudSnapshots = $state<CloudBackupSnapshot[]>([]);
  public loadingCloud = $state(false);
  public uploadingCloud = $state(false);
  public passphrase = $state('');
  public snapshotLabel = $state('');
  public showPassphraseModal = $state(false);
  public activeCloudAction = $state<'upload' | 'restore' | 'restore_latest' | null>(null);
  public targetCloudSnapshot = $state<CloudBackupSnapshot | null>(null);
  public pinLoading = $state<Record<string, boolean>>({});
  public pinSnapshotOnCreate = $state(false);

  /**
[END IN]
[2 START IN]
      const result = await api.createAndUploadCloudSnapshot({
        passphrase: this.passphrase,
        snapshot_label: this.snapshotLabel.trim() || 'Manual Cloud Backup'
      });

      toastStore.success(result.message || 'Snapshot successfully vaulted in Pluvira Cloud!');
      this.passphrase = '';
      this.snapshotLabel = '';
      this.showPassphraseModal = false;
[END IN]
[START OUT]
      const result = await api.createAndUploadCloudSnapshot({
        passphrase: this.passphrase,
        snapshot_label: this.snapshotLabel.trim() || 'Manual Cloud Backup',
        pin_snapshot: this.pinSnapshotOnCreate
      });

      toastStore.success(result.message || 'Snapshot successfully vaulted in Pluvira Cloud!');
      this.passphrase = '';
      this.snapshotLabel = '';
      this.pinSnapshotOnCreate = false;
      this.showPassphraseModal = false;
   * Fetches stored snapshots from Pluvira Cloud vault.
   */
  public async loadCloudSnapshots(): Promise<void> {
    this.loadingCloud = true;
    try {
      this.cloudSnapshots = await api.getCloudSnapshots();
    } catch {
      // Instance might be unlinked or offline
      this.cloudSnapshots = [];
    } finally {
      this.loadingCloud = false;
    }
  }

  /**
   * Exports, encrypts, and vaults a snapshot to Pluvira Cloud via local backend daemon.
   */
  public async executeCloudUpload(): Promise<boolean> {
    if (!this.passphrase || this.passphrase.length < 8) {
      toastStore.error('Passphrase must be at least 8 characters long.');
      return false;
    }

    this.uploadingCloud = true;
    toastStore.info('Encrypting and uploading cloud backup snapshot via local backend...');

    try {
      const result = await api.createAndUploadCloudSnapshot({
        passphrase: this.passphrase,
        snapshot_label: this.snapshotLabel.trim() || 'Manual Cloud Backup'
      });

      toastStore.success(result.message || 'Snapshot successfully vaulted in Pluvira Cloud!');
      this.passphrase = '';
      this.snapshotLabel = '';
      this.showPassphraseModal = false;
      await this.loadCloudSnapshots();
      return true;
    } catch (err: any) {
      toastStore.error(`Cloud upload failed: ${err.message}`);
      return false;
    } finally {
      this.uploadingCloud = false;
    }
  }

  /**
   * Downloads and decrypts a snapshot via local backend daemon, staging it for preview.
   */
  public async executeCloudRestore(): Promise<boolean> {
    if (!this.targetCloudSnapshot) return false;
    if (!this.passphrase) {
      toastStore.error('Please enter your decryption passphrase.');
      return false;
    }

    this.validating = true;
    toastStore.info('Downloading and decrypting cloud snapshot via local backend...');

    try {
      const bundle = await api.downloadAndDecryptCloudSnapshot({
        backup_id: this.targetCloudSnapshot.id,
        passphrase: this.passphrase
      });

      this.stagedBundle = bundle;
      const payload: BackupImportPayload = { bundle, mode: this.importMode };
      this.validationResult = await api.validateBackup(payload);

      this.showPassphraseModal = false;
      this.passphrase = '';
      this.showPreviewModal = true;
      toastStore.success('Cloud snapshot decrypted successfully. Review diff to confirm.');
      return true;
    } catch (err: any) {
      toastStore.error(`Restore failed: ${err.message}`);
      return false;
    } finally {
      this.validating = false;
    }
  }

  /**
   * Deletes a cloud snapshot from the SaaS vault.
   */
  public async deleteCloudSnapshot(id: string): Promise<void> {
    try {
      await api.deleteCloudSnapshot(id);
      toastStore.success('Snapshot removed from cloud vault.');
      await this.loadCloudSnapshots();
    } catch (err: any) {
      toastStore.error(`Failed to delete snapshot: ${err.message}`);
    }
  }

  /**
   * Toggles the pinning lock status of a snapshot against FIFO auto-purge.
   */
  public async togglePinSnapshot(snapshot: CloudBackupSnapshot, isPro: boolean): Promise<void> {
    if (!isPro) {
      toastStore.warning('Snapshot pinning requires Pluvira Pro or Ultra edition.');
      return;
    }

    const targetState = !snapshot.is_pinned;
    this.pinLoading[snapshot.id] = true;

    try {
      const updated = await api.pinCloudBackupSnapshot(snapshot.id, targetState);
      snapshot.is_pinned = updated.is_pinned ?? targetState;
      toastStore.success(targetState ? 'Snapshot pinned successfully.' : 'Snapshot unpinned.');
    } catch (err: any) {
      toastStore.error(err.message || 'Failed to update snapshot pin state.');
    } finally {
      this.pinLoading[snapshot.id] = false;
    }
  }

  /**
   * Executes 1-click atomic disaster recovery from the latest cloud backup snapshot.
   */
  public async executeLatestCloudRestore(): Promise<boolean> {
    if (!this.passphrase) {
      toastStore.error('Please enter your decryption passphrase.');
      return false;
    }

    this.validating = true;
    toastStore.info('Downloading and decrypting latest cloud snapshot...');

    try {
      const bundle = await api.downloadLatestAndDecryptCloudBackup({
        passphrase: this.passphrase
      });

      this.stagedBundle = bundle;
      const payload: BackupImportPayload = { bundle, mode: this.importMode };
      this.validationResult = await api.validateBackup(payload);

      this.showPassphraseModal = false;
      this.passphrase = '';
      this.showPreviewModal = true;
      toastStore.success('Latest cloud snapshot decrypted successfully. Review diff to confirm.');
      return true;
    } catch (err: any) {
      toastStore.error(`Restore failed: ${err.message}`);
      return false;
    } finally {
      this.validating = false;
    }
  }

  /**
   * Downloads a full or sanitized configuration backup bundle.
   *
   * @param sanitized Whether credentials and webhook tokens should be masked.
   */
  public async exportBackup(sanitized = false): Promise<void> {
    this.exporting = true;
    toastStore.info(`Generating ${sanitized ? 'sanitized' : 'full'} backup bundle...`);
    try {
      await api.exportBackup(sanitized);
      toastStore.success(`Backup bundle (${sanitized ? 'Sanitized' : 'Full'}) downloaded.`);
    } catch (err: any) {
      toastStore.error(`Backup export failed: ${err.message}`);
    } finally {
      this.exporting = false;
    }
  }

  /**
   * Ingests a user-selected JSON file, parses it, and triggers pre-flight validation.
   *
   * @param file Target File object from file input.
   */
  public async handleFileSelected(file: File): Promise<void> {
    if (!file) return;
    this.validating = true;
    this.resetStaging();

    try {
      const bundle = await readBackupFileAsJson(file);
      this.stagedBundle = bundle;

      const payload: BackupImportPayload = {
        bundle,
        mode: this.importMode
      };

      const validation = await api.validateBackup(payload);
      this.validationResult = validation;

      if (!validation.valid && validation.errors && validation.errors.length > 0) {
        toastStore.error(`Backup validation failed: ${validation.errors.join(', ')}`);
      } else {
        this.showPreviewModal = true;
        if (validation.sanitized_detected) {
          toastStore.warning('Sanitized backup detected: existing passwords/tokens on disk will be preserved.');
        }
      }
    } catch (err: any) {
      toastStore.error(err.message || 'Failed to read backup file.');
      this.resetStaging();
    } finally {
      this.validating = false;
    }
  }

  /**
   * Updates import mode and re-validates if staged bundle is loaded.
   *
   * @param mode Target import strategy ('destructive' | 'merge').
   */
  public async setImportMode(mode: 'destructive' | 'merge'): Promise<void> {
    this.importMode = mode;
    if (this.stagedBundle) {
      try {
        const payload: BackupImportPayload = {
          bundle: this.stagedBundle,
          mode: this.importMode
        };
        this.validationResult = await api.validateBackup(payload);
      } catch {
        // Retain current validation state
      }
    }
  }

  /**
   * Executes atomic backup import on backend with rollback protection.
   *
   * @param onSuccess Optional callback executed after successful import.
   */
  public async executeImport(onSuccess?: () => void): Promise<boolean> {
    if (!this.stagedBundle) {
      toastStore.error('No backup bundle staged for import.');
      return false;
    }

    this.importing = true;
    try {
      const payload: BackupImportPayload = {
        bundle: this.stagedBundle,
        mode: this.importMode,
        trigger_sync: true
      };

      const result = await api.importBackup(payload);
      if (result.success) {
        const hasSources = Boolean(
          (this.stagedBundle.sources && this.stagedBundle.sources.length > 0) ||
          (this.stagedBundle.config?.sources && this.stagedBundle.config.sources.length > 0)
        );
        if (hasSources) {
          toastStore.success('Backup imported. Synchronizing media catalog in background...');
        } else {
          toastStore.success(result.message || 'Backup imported successfully!');
        }
        this.showPreviewModal = false;
        this.resetStaging();
        if (onSuccess) {
          onSuccess();
        }
        return true;
      } else {
        toastStore.error(result.message || 'Backup import failed.');
        return false;
      }
    } catch (err: any) {
      toastStore.error(`Import error: ${err.message}`);
      return false;
    } finally {
      this.importing = false;
    }
  }

  /**
   * Resets staged upload state and clears preview dialog.
   */
  public resetStaging(): void {
    this.stagedBundle = null;
    this.validationResult = null;
    this.showPreviewModal = false;
  }
}
