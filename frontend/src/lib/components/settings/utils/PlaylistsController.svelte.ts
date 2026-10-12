import { api } from '$lib/api/client';
import type { PlaylistItem } from '$lib/api/types';
import { copyToClipboard } from '$lib/utils/clipboardUtils';
import { toastStore } from '$lib/stores/toastStore';
import { playlistStore } from '$lib/stores/playlistStore';

export class PlaylistsController {
  public loading = $state(false);
  public saving = $state(false);
  public playlists = $state<PlaylistItem[]>([]);
  public newPlaylistName = $state('');
  public editingPlaylistId = $state<string | null>(null);
  public editingPlaylistName = $state('');

  /**
   * Loads all personal playlists from API.
   */
  public async loadPlaylists(): Promise<void> {
    this.loading = true;
    try {
      const list = await api.getPlaylists();
      this.playlists = list;
      playlistStore.setPlaylists(list);
    } catch (err: any) {
      toastStore.error(`Failed to load playlists: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Creates a new personal playlist.
   */
  public async createPlaylist(isPro = true): Promise<boolean> {
    const name = this.newPlaylistName.trim();
    if (!name) {
      toastStore.warning('Please enter a playlist name.');
      return false;
    }
    if (!isPro && this.playlists.length >= 1) {
      toastStore.warning('Personal Free Tier is limited to 1 curated playlist. Upgrade to Pro for unlimited playlists.');
      return false;
    }
    this.saving = true;
    try {
      const created = await api.createPlaylist({ name });
      this.newPlaylistName = '';
      toastStore.success(`Playlist '${created.name}' created successfully.`);
      await this.loadPlaylists();
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to create playlist: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Updates an existing playlist name.
   */
  public async updatePlaylist(playlistId: string): Promise<boolean> {
    const name = this.editingPlaylistName.trim();
    if (!name) return false;
    this.saving = true;
    try {
      await api.updatePlaylist(playlistId, { name });
      this.editingPlaylistId = null;
      this.editingPlaylistName = '';
      toastStore.success('Playlist updated successfully.');
      await this.loadPlaylists();
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to update playlist: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Regenerates the security export token for a playlist.
   */
  public async regenerateToken(playlistId: string): Promise<string | null> {
    this.saving = true;
    try {
      const res = await api.regeneratePlaylistToken(playlistId);
      toastStore.success(res.message || 'Export token regenerated successfully.');
      await this.loadPlaylists();
      return res.token;
    } catch (err: any) {
      toastStore.error(`Failed to regenerate token: ${err.message}`);
      return null;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Deletes a personal playlist.
   */
  public async deletePlaylist(playlistId: string): Promise<boolean> {
    this.saving = true;
    try {
      await api.deletePlaylist(playlistId);
      toastStore.info('Playlist deleted.');
      await this.loadPlaylists();
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to delete playlist: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Copies dynamic M3U export URL to user clipboard.
   */
  public async copyExportUrl(playlist: PlaylistItem): Promise<void> {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const tokenQuery = playlist.export_token ? `&token=${encodeURIComponent(playlist.export_token)}` : '';
    const exportUrl = `${origin}/api/v1/export/m3u?list=${encodeURIComponent(playlist.id)}${tokenQuery}`;

    const success = await copyToClipboard(exportUrl);
    if (success) {
      toastStore.success('M3U export URL copied to clipboard.');
    } else {
      toastStore.info(`Export URL: ${exportUrl}`);
    }
  }
}
