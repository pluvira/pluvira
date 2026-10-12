<script lang="ts">
  import Dialog from '../ui/Dialog.svelte';
  import Button from '../ui/Button.svelte';
  import Badge from '../ui/Badge.svelte';
  import SegmentedControl, { type SegmentOption } from '../ui/SegmentedControl.svelte';
  import ConfirmDialog from '../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../ui/ConfirmController.svelte';
  import {
    bulletinStore, activeBulletins, archivedBulletins, resolveLocalizedText
  } from '$lib/stores/bulletinStore';
  import {
    Bell, CheckCheck, ExternalLink, ShieldAlert, AlertTriangle, Sparkles, Archive, X, Trash2
  } from '@lucide/svelte';

  interface Props {
    open?: boolean;
    onclose?: () => void;
    class?: string;
  }

  let { open = $bindable(), onclose, class: className = '' }: Props = $props();

  type DrawerTab = 'active' | 'archived';
  let activeTab = $state<DrawerTab>('active');
  const confirmController = new ConfirmController();

  let activeList = $derived($activeBulletins);
  let archivedList = $derived($archivedBulletins);
  let hasDismissible = $derived(activeList.some((b) => b.dismissible));

  const tabOptions = $derived<SegmentOption<DrawerTab>[]>([
    { value: 'active', label: `Active (${activeList.length})` },
    { value: 'archived', label: `Archived (${archivedList.length})` }
  ]);

  $effect(() => {
    if (open) {
      bulletinStore.fetchBulletins(true);
    }
  });

  $effect(() => {
    if (open && activeTab === 'active' && activeList.length > 0) {
      for (const b of activeList) {
        if (!b.is_read) {
          bulletinStore.markRead(b.id);
        }
      }
    }
  });

  async function handleDismiss(id: string) {
    await bulletinStore.dismiss(id);
  }

  async function handleDismissAll() {
    const dismissibleList = activeList.filter((b) => b.dismissible);
    for (const b of dismissibleList) {
      await bulletinStore.dismiss(b.id);
    }
  }

  function handleDeleteSingle(id: string) {
    confirmController.requestConfirm('bulletin_single', () => {
      bulletinStore.deleteBulletin(id);
    });
  }

  function handleDeleteAllArchived() {
    confirmController.requestConfirm('bulletin_archived_all', () => {
      bulletinStore.clearArchived();
    });
  }

  function handleClose() {
    open = false;
    if (onclose) onclose();
  }
</script>

<Dialog
  bind:open
  title="Notices"
  onclose={handleClose}
  class="max-w-xl {className}"
>
  <div class="flex flex-col gap-3 py-1">
    <div class="flex items-center justify-between">
      <SegmentedControl
        options={tabOptions}
        value={activeTab}
        onchange={(val) => { activeTab = val; }}
      />
    </div>

    {#if activeTab === 'active'}
      {#if activeList.length === 0}
        <div class="flex flex-col items-center justify-center py-8 text-center text-muted-foreground gap-2">
          <Bell class="w-10 h-10 opacity-30" />
          <p class="text-sm font-medium">No active system notices.</p>
          {#if archivedList.length > 0}
            <Button
              variant="ghost"
              size="sm"
              onclick={() => { activeTab = 'archived'; }}
              class="text-xs text-primary hover:underline touch-btn cursor-pointer"
            >
              <Archive class="w-3.5 h-3.5 mr-1" />
              View Archived Notices ({archivedList.length})
            </Button>
          {:else}
            <p class="text-xs text-muted-foreground/70">All system notices have been read or resolved.</p>
          {/if}
        </div>
      {:else}
        {#each activeList as b (b.id)}
          <div class="surface-card p-3 flex flex-col gap-2 relative border transition-colors {
            b.level === 'security'
              ? 'border-destructive/50 bg-destructive/10'
              : b.level === 'critical'
              ? 'border-destructive/40 bg-destructive/5'
              : b.level === 'warning'
              ? 'border-primary/40 bg-primary/5'
              : 'border-border/60 bg-card'
          }">
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2">
                {#if b.level === 'security'}
                  <ShieldAlert class="w-4 h-4 text-destructive shrink-0 animate-pulse" />
                  <Badge variant="error">SECURITY</Badge>
                {:else if b.level === 'critical'}
                  <AlertTriangle class="w-4 h-4 text-destructive shrink-0" />
                  <Badge variant="error">CRITICAL</Badge>
                {:else if b.level === 'warning'}
                  <AlertTriangle class="w-4 h-4 text-primary shrink-0" />
                  <Badge variant="warning">WARNING</Badge>
                {:else}
                  <Sparkles class="w-4 h-4 text-primary shrink-0" />
                  <Badge variant="primary">NOTICE</Badge>
                {/if}
                <span class="text-xs font-bold text-foreground truncate max-w-[280px]">
                  {resolveLocalizedText(b.title)}
                </span>
              </div>

              {#if b.dismissible}
                <button
                  type="button"
                  onclick={() => handleDismiss(b.id)}
                  class="text-muted-foreground hover:text-foreground p-1 rounded-md transition-colors touch-btn cursor-pointer"
                  title="Dismiss notice"
                  aria-label="Dismiss notice"
                >
                  <X class="w-4 h-4" />
                </button>
              {/if}
            </div>

            <p class="text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
              {resolveLocalizedText(b.message)}
            </p>

            {#if b.action_url}
              <div class="flex items-center justify-end pt-1">
                <a
                  href={b.action_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 no-underline transition-colors touch-btn"
                >
                  <span>{b.action_label ? resolveLocalizedText(b.action_label) : 'Learn More'}</span>
                  <ExternalLink class="w-3 h-3" />
                </a>
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    {:else}
      {#if archivedList.length === 0}
        <div class="flex flex-col items-center justify-center py-8 text-center text-muted-foreground gap-2">
          <Archive class="w-10 h-10 opacity-30" />
          <p class="text-sm font-medium">No archived notices.</p>
        </div>
      {:else}
        {#each archivedList as b (b.id)}
          <div class="surface-card p-3 flex flex-col gap-2 relative border border-border/40 bg-card/60 opacity-80">
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2">
                <Badge variant="muted">ARCHIVED</Badge>
                <span class="text-xs font-bold text-foreground/90 truncate max-w-[280px]">
                  {resolveLocalizedText(b.title)}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono text-muted-foreground/70">
                  {b.dismissed_at ? new Date(b.dismissed_at).toLocaleDateString() : 'Dismissed'}
                </span>
                <button
                  type="button"
                  onclick={() => handleDeleteSingle(b.id)}
                  class="text-muted-foreground hover:text-destructive p-1 rounded-md transition-colors touch-btn cursor-pointer"
                  title="Delete notice"
                  aria-label="Delete notice"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <p class="text-xs text-muted-foreground/80 leading-relaxed whitespace-pre-line">
              {resolveLocalizedText(b.message)}
            </p>

            {#if b.action_url}
              <div class="flex items-center justify-end pt-1">
                <a
                  href={b.action_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-xs font-bold text-muted-foreground hover:text-foreground no-underline transition-colors touch-btn"
                >
                  <span>{b.action_label ? resolveLocalizedText(b.action_label) : 'Reference Link'}</span>
                  <ExternalLink class="w-3 h-3" />
                </a>
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    {/if}
  </div>

  {#snippet footer()}
    <div class="flex items-center justify-between w-full">
      {#if activeTab === 'active' && activeList.length > 0 && hasDismissible}
        <Button
          variant="ghost"
          size="sm"
          onclick={handleDismissAll}
          class="text-xs text-muted-foreground hover:text-destructive touch-btn"
        >
          <CheckCheck class="w-3.5 h-3.5 mr-1" />
          Dismiss All
        </Button>
      {:else if activeTab === 'archived' && archivedList.length > 0}
        <Button
          variant="ghost"
          size="sm"
          onclick={handleDeleteAllArchived}
          class="text-xs text-muted-foreground hover:text-destructive touch-btn"
        >
          <Trash2 class="w-3.5 h-3.5 mr-1" />
          Delete All Archived
        </Button>
      {:else}
        <div></div>
      {/if}
      <Button
        variant="secondary"
        size="sm"
        onclick={handleClose}
        class="touch-btn"
      >
        Close
      </Button>
    </div>
  {/snippet}
</Dialog>

<ConfirmDialog
  bind:open={confirmController.open}
  scope={confirmController.scope}
  onconfirm={() => confirmController.handleConfirm()}
/>
