<script lang="ts">
  import { criticalBulletins, activeBulletins, bulletinStore, resolveLocalizedText } from '$lib/stores/bulletinStore';
  import { ShieldAlert, AlertTriangle, Sparkles, X, ExternalLink, ChevronLeft, ChevronRight } from '@lucide/svelte';
  import type { BulletinDTO } from '$lib/api/types';

  interface Props {
    bulletins?: BulletinDTO[];
    class?: string;
  }

  let { bulletins, class: className = '' }: Props = $props();

  let activeList = $derived(
    bulletins ??
      $activeBulletins.filter(
        (b) =>
          $criticalBulletins.some((c) => c.id === b.id) ||
          b.level === 'critical' ||
          b.level === 'security' ||
          !b.dismissible ||
          b.id.startsWith('rel_') ||
          b.id.startsWith('update_')
      )
  );
  let currentIndex = $state(0);

  $effect(() => {
    if (currentIndex >= activeList.length && activeList.length > 0) {
      currentIndex = activeList.length - 1;
    }
  });

  let currentBulletin = $derived(activeList[currentIndex] || null);

  $effect(() => {
    if (currentBulletin && !currentBulletin.is_read) {
      bulletinStore.markRead(currentBulletin.id);
    }
  });
  let title = $derived(currentBulletin ? resolveLocalizedText(currentBulletin.title) : '');
  let message = $derived(currentBulletin ? resolveLocalizedText(currentBulletin.message) : '');
  let actionLabel = $derived(
    currentBulletin?.action_label ? resolveLocalizedText(currentBulletin.action_label) : 'Learn More'
  );

  function next() {
    if (activeList.length > 0) currentIndex = (currentIndex + 1) % activeList.length;
  }

  function prev() {
    if (activeList.length > 0) currentIndex = (currentIndex - 1 + activeList.length) % activeList.length;
  }

  async function handleDismiss() {
    if (currentBulletin) {
      await bulletinStore.dismiss(currentBulletin.id);
    }
  }
</script>

{#if currentBulletin}
  <aside
    class="w-full border-b px-3 py-2 flex items-center justify-between gap-3 text-xs sm:text-sm font-medium transition-colors z-30 shrink-0 {
      currentBulletin.level === 'security'
        ? 'bg-destructive/20 border-destructive/50 text-destructive-foreground'
        : currentBulletin.level === 'critical'
        ? 'bg-destructive/15 border-destructive/40 text-foreground'
        : currentBulletin.level === 'warning'
        ? 'bg-primary/15 border-primary/40 text-foreground'
        : 'bg-primary/10 border-primary/30 text-foreground'
    } {className}"
    aria-label="System Advisory"
  >
    <div class="flex items-center gap-2 min-w-0 flex-1">
      {#if currentBulletin.level === 'security'}
        <ShieldAlert class="w-4 h-4 shrink-0 text-destructive animate-pulse" />
      {:else if currentBulletin.level === 'critical'}
        <AlertTriangle class="w-4 h-4 shrink-0 text-destructive" />
      {:else if currentBulletin.level === 'warning'}
        <AlertTriangle class="w-4 h-4 shrink-0 text-primary" />
      {:else}
        <Sparkles class="w-4 h-4 shrink-0 text-primary" />
      {/if}

      <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5 truncate">
        <strong class="font-bold truncate">{title}</strong>
        {#if message}
          <span class="text-muted-foreground truncate hidden sm:inline">&mdash; {message}</span>
        {/if}
      </div>
    </div>

    <div class="flex items-center gap-2 shrink-0">
      {#if activeList.length > 1}
        <div class="flex items-center text-[10px] text-muted-foreground mr-1">
          <button
            type="button"
            onclick={prev}
            class="p-0.5 hover:text-foreground cursor-pointer touch-btn"
            aria-label="Previous announcement"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
          </button>
          <span class="px-1">{currentIndex + 1}/{activeList.length}</span>
          <button
            type="button"
            onclick={next}
            class="p-0.5 hover:text-foreground cursor-pointer touch-btn"
            aria-label="Next announcement"
          >
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>
      {/if}

      {#if currentBulletin.action_url}
        <a
          href={currentBulletin.action_url}
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-md bg-card/80 hover:bg-card border border-border/60 text-foreground no-underline transition-colors touch-btn"
        >
          <span>{actionLabel}</span>
          <ExternalLink class="w-3 h-3" />
        </a>
      {/if}

      {#if currentBulletin.dismissible}
        <button
          type="button"
          onclick={handleDismiss}
          class="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-card/50 cursor-pointer transition-colors touch-btn"
          aria-label="Dismiss announcement"
          title="Dismiss"
        >
          <X class="w-4 h-4" />
        </button>
      {/if}
    </div>
  </aside>
{/if}
