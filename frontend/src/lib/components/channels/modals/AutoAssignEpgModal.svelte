<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Checkbox from '../../ui/Checkbox.svelte';
  import { Calendar, Sparkles, Zap, ShieldCheck } from '@lucide/svelte';
  import { licenseStore } from '$lib/stores/licenseStore';

  interface Props {
    open?: boolean;
    unmappedCount?: number;
    autoAssigning?: boolean;
    onassign?: (scope: 'curated' | 'all', threshold: number, overwrite: boolean) => void;
    onupgradepro?: () => void;
    onclose?: () => void;
    class?: string;
  }

  let {
    open = $bindable(),
    unmappedCount = 0,
    autoAssigning = false,
    onassign,
    onupgradepro,
    onclose,
    class: className = ''
  }: Props = $props();

  let overwrite = $state(false);
  let isPro = $derived($licenseStore.isPro);

  function handleCurated() {
    if (onassign) onassign('curated', 0.85, overwrite);
  }

  function handleAll() {
    if (!isPro) {
      open = false;
      if (onupgradepro) onupgradepro();
      return;
    }
    if (onassign) onassign('all', 0.85, overwrite);
  }
</script>

<Dialog bind:open title="Auto-Assign EPG Guide" class="max-w-xl {className}">
  {#snippet footer()}
    <div class="flex items-center justify-end gap-2 w-full">
      <Button
        variant="ghost"
        size="sm"
        onclick={() => { open = false; if (onclose) onclose(); }}
        disabled={autoAssigning}
        class="touch-btn"
      >
        Cancel
      </Button>
    </div>
  {/snippet}

  <div class="flex flex-col gap-4 text-xs">
    <div class="p-3 bg-primary/10 border border-primary/20 rounded-md flex items-start gap-3">
      <div class="p-2 rounded-full bg-primary/20 text-primary shrink-0">
        <Sparkles class="w-4 h-4" />
      </div>
      <div class="flex flex-col gap-0.5">
        <span class="font-bold text-foreground">Intelligent EPG Matcher</span>
        <span class="text-muted-foreground leading-relaxed">
          Automatically maps missing guide schedules to channel names using normalized title sanitization and high-confidence matching.
          {#if unmappedCount > 0}
            Currently detecting <strong class="text-foreground">{unmappedCount} unmapped channel(s)</strong>.
          {/if}
        </span>
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <!-- Option A: Free Curated Scope -->
      <div class="surface-card p-3 rounded-md flex flex-col sm:flex-row sm:items-center justify-between gap-3 border border-border/40 hover:border-primary/40 transition-colors">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-1.5 font-bold text-foreground">
            <Calendar class="w-4 h-4 text-primary" />
            <span>Auto-Map My List (Free)</span>
          </div>
          <span class="text-muted-foreground text-[11px] leading-relaxed">
            Evaluates curated channels in your active personal playlist (up to 25 channels) with confidence &ge; 85%.
          </span>
        </div>
        <Button
          variant="primary"
          size="sm"
          onclick={handleCurated}
          disabled={autoAssigning}
          class="shrink-0 font-bold touch-btn flex items-center justify-center gap-1.5"
        >
          {#if autoAssigning}
            <span class="spinner w-3.5 h-3.5 mr-1"></span>
          {/if}
          <span>Run My List</span>
        </Button>
      </div>

      <!-- Option B: Pro All Catalog Scope -->
      <div class="surface-card p-3 rounded-md flex flex-col sm:flex-row sm:items-center justify-between gap-3 border border-border/40 hover:border-primary/40 transition-colors">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-1.5 font-bold text-foreground">
            <Zap class="w-4 h-4 text-warning" />
            <span>Auto-Map All Channels</span>
            <Badge variant="warning" class="text-[9px] font-bold uppercase tracking-wider">Pro</Badge>
          </div>
          <span class="text-muted-foreground text-[11px] leading-relaxed">
            Catalog-wide deep fuzzy matching and multi-source disambiguation across all ingested playlist channels.
          </span>
        </div>
        <Button
          variant={isPro ? 'primary' : 'outline'}
          size="sm"
          onclick={handleAll}
          disabled={autoAssigning}
          class="shrink-0 font-bold touch-btn flex items-center justify-center gap-1.5"
        >
          {#if isPro}
            <span>Run All Catalog</span>
          {:else}
            <ShieldCheck class="w-3.5 h-3.5 text-warning" />
            <span>Unlock with Pro</span>
          {/if}
        </Button>
      </div>
    </div>

    <!-- Options & Preferences -->
    <div class="pt-2 border-t border-border/30 flex items-center gap-2">
      <Checkbox
        id="auto-assign-overwrite-toggle"
        bind:checked={overwrite}
        disabled={autoAssigning}
        label="Overwrite existing manual EPG mappings"
      />
    </div>
  </div>
</Dialog>
