<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import { PlaylistsController } from '../utils/PlaylistsController.svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { ListMusic, Plus, RotateCw, Copy, Trash2, Pencil, Check, X, ShieldCheck } from '@lucide/svelte';
  import type { PlaylistItem } from '$lib/api/types';

  const controller = new PlaylistsController();
  const confirmController = new ConfirmController();
  let isPro = $derived($licenseStore.isPro);

  function handleCreate() {
    controller.createPlaylist(isPro);
  }

  function handleStartEdit(pl: PlaylistItem) {
    controller.editingPlaylistId = pl.id;
    controller.editingPlaylistName = pl.name;
  }

  function handleSaveEdit(pl: PlaylistItem) {
    controller.updatePlaylist(pl.id);
  }

  function handleCancelEdit() {
    controller.editingPlaylistId = null;
    controller.editingPlaylistName = '';
  }

  function requestDelete(pl: PlaylistItem) {
    confirmController.requestConfirm('iptv_source', () => {
      controller.deletePlaylist(pl.id);
    });
  }

  onMount(() => {
    controller.loadPlaylists();
  });
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  <Card title="Curated Personal Playlists Management">
    <div class="flex flex-col gap-4 w-full">
      <span class="text-xs text-muted-foreground leading-relaxed">
        Manage curated playlists, configure secure M3U export tokens, and export custom stream lists for external media players.
      </span>

      <!-- Create New Playlist Row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-3 items-end panel-box !p-3">
        <div class="sm:col-span-2 md:col-span-3">
          <Input
            label="New Playlist Name"
            bind:value={controller.newPlaylistName}
            placeholder="e.g. Living Room TV, Sports Hub..."
            disabled={!isPro && controller.playlists.length >= 1}
          />
        </div>
        <Button
          variant="primary"
          size="sm"
          disabled={controller.saving || (!isPro && controller.playlists.length >= 1)}
          onclick={handleCreate}
          class="font-bold text-xs h-[36px] w-full flex items-center justify-center gap-1.5 touch-btn"
        >
          <Plus class="w-4 h-4" />
          <span>Add Playlist</span>
        </Button>
      </div>

      {#if !isPro && controller.playlists.length >= 1}
        <div class="banner-warning !p-3">
          <span class="text-xs text-amber-200">
            <strong>Personal Free Tier Limit:</strong> Free tier is restricted to 1 curated playlist. Upgrade to Pluvira Pro for unlimited custom playlists.
          </span>
        </div>
      {/if}

      <!-- Playlists Table / Cards -->
      <div class="overflow-x-auto w-full border border-border/30 rounded-md">
        <table class="table-base">
          <thead>
            <tr>
              <th class="table-th w-12 text-center">Icon</th>
              <th class="table-th">Playlist Name</th>
              <th class="table-th text-center w-28">Status</th>
              <th class="table-th text-center w-36">Export Token</th>
              <th class="table-th text-right pr-4 w-32">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#if controller.loading && controller.playlists.length === 0}
              <tr>
                <td colspan="5" class="p-6 text-center text-muted-foreground italic">
                  Loading playlists...
                </td>
              </tr>
            {:else if controller.playlists.length === 0}
              <tr>
                <td colspan="5" class="p-6 text-center text-muted-foreground italic">
                  No curated playlists found.
                </td>
              </tr>
            {:else}
              {#each controller.playlists as pl (pl.id)}
                {@const isEditing = controller.editingPlaylistId === pl.id}
                <tr class="table-tr">
                  <td class="table-td text-center">
                    <ListMusic class="w-4 h-4 text-primary mx-auto" />
                  </td>

                  <td class="table-td font-bold text-foreground">
                    {#if isEditing}
                      <div class="flex items-center gap-1.5">
                        <Input bind:value={controller.editingPlaylistName} placeholder="Playlist name..." class="!py-0.5 !text-xs" />
                        <Button variant="ghost" size="sm" onclick={() => handleSaveEdit(pl)} class="!p-1 text-primary touch-btn" title="Save name">
                          <Check class="w-3.5 h-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" onclick={handleCancelEdit} class="!p-1 text-muted-foreground touch-btn" title="Cancel">
                          <X class="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    {:else}
                      <span>{pl.name}</span>
                    {/if}
                  </td>

                  <td class="table-td text-center">
                    <Badge variant={pl.is_default ? 'primary' : 'success'}>
                      {pl.is_default ? 'DEFAULT' : 'ACTIVE'}
                    </Badge>
                  </td>

                  <td class="table-td text-center font-mono text-[11px] text-muted-foreground">
                    {#if pl.export_token}
                      <div class="flex items-center justify-center gap-1">
                        <ShieldCheck class="w-3.5 h-3.5 text-primary" />
                        <span class="truncate max-w-[100px]" title={pl.export_token}>••••••••</span>
                      </div>
                    {:else}
                      <span class="text-muted-foreground/60 italic">Public (None)</span>
                    {/if}
                  </td>

                  <td class="table-td text-right pr-4">
                    <div class="flex items-center justify-end gap-1 whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        onclick={() => controller.copyExportUrl(pl)}
                        class="!p-1 text-xs text-muted-foreground hover:text-foreground touch-btn"
                        title="Copy M3U export URL to clipboard"
                        aria-label="Copy M3U export URL to clipboard"
                      >
                        <Copy class="w-3.5 h-3.5" />
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={controller.saving}
                        onclick={() => controller.regenerateToken(pl.id)}
                        class="!p-1 text-xs text-primary hover:text-primary/80 touch-btn"
                        title="Regenerate export security token"
                      >
                        <RotateCw class="w-3.5 h-3.5" />
                      </Button>

                      {#if !isEditing}
                        <Button
                          variant="ghost"
                          size="sm"
                          onclick={() => handleStartEdit(pl)}
                          class="!p-1 text-xs text-muted-foreground hover:text-foreground touch-btn"
                          title="Rename playlist"
                        >
                          <Pencil class="w-3.5 h-3.5" />
                        </Button>
                      {/if}

                      {#if !pl.is_default}
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={controller.saving}
                          onclick={() => requestDelete(pl)}
                          class="!p-1 text-xs text-destructive hover:opacity-80 touch-btn"
                          title="Delete playlist"
                        >
                          <Trash2 class="w-3.5 h-3.5" />
                        </Button>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </div>
  </Card>
</div>
