<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Switch from '../../ui/Switch.svelte';
  import MultiSelectTags from '../../ui/MultiSelectTags.svelte';
  import type { SearchController } from '../SearchController.svelte';
  import { RotateCcw } from '@lucide/svelte';

  interface Props {
    controller: SearchController;
    open?: boolean;
    onclose?: () => void;
  }

  let {
    controller,
    open = $bindable(),
    onclose
  }: Props = $props();

  function handleClose() {
    if (onclose) onclose();
    else controller.closeAdvancedModal();
  }
</script>

<Dialog
  {open}
  title="EPG Discovery & Search Filters"
  onclose={handleClose}
>
  <div class="flex flex-col gap-4 text-sm">
    <p class="text-xs text-muted-foreground">
      Configure intelligent search scoring algorithms, multi-facet channel categories, and relevance thresholds.
    </p>

    <!-- Curated List Filter Switch -->
    <div class="flex items-center justify-between p-3 bg-muted/20 border border-border/30 rounded-lg">
      <div class="flex flex-col">
        <span class="font-bold text-xs text-foreground">Curated Channels Only (My List)</span>
        <span class="text-[11px] text-muted-foreground">Restricts search results to channels saved in your personal playlist</span>
      </div>
      <Switch
        checked={controller.curatedOnly}
        onCheckedChange={(val) => { controller.curatedOnly = val; }}
      />
    </div>

    <!-- Multi-Select Category Groups -->
    {#if controller.availableGroups.length > 0}
      <div class="flex flex-col gap-1.5 p-3 bg-muted/20 border border-border/30 rounded-lg">
        <span class="text-xs font-bold text-foreground uppercase tracking-wider">Channel Groups</span>
        <MultiSelectTags
          placeholder="Filter by category groups..."
          options={controller.availableGroups}
          selectedValues={controller.selectedGroups}
          onchange={(vals) => { controller.selectedGroups = vals; }}
        />
      </div>
    {/if}

    <!-- Multi-Select Source Providers -->
    {#if controller.availableSources.length > 0}
      <div class="flex flex-col gap-1.5 p-3 bg-muted/20 border border-border/30 rounded-lg">
        <span class="text-xs font-bold text-foreground uppercase tracking-wider">Source Providers</span>
        <MultiSelectTags
          placeholder="Filter by IPTV sources..."
          options={controller.availableSources}
          selectedValues={controller.selectedSources}
          onchange={(vals) => { controller.selectedSources = vals; }}
        />
      </div>
    {/if}

    <!-- Minimum Score Threshold -->
    <div class="flex flex-col gap-1.5 p-3 bg-muted/20 border border-border/30 rounded-lg">
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-foreground uppercase tracking-wider">Minimum Score Threshold</span>
        <span class="font-mono font-bold text-primary text-xs">{controller.minScore}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        step="5"
        value={controller.minScore}
        oninput={(e) => controller.setMinScore(parseInt((e.target as HTMLInputElement).value, 10))}
        class="w-full accent-primary cursor-pointer"
        aria-label="Minimum Score Threshold"
      />
      <span class="text-[11px] text-muted-foreground">Filter out programme matches below this score.</span>
    </div>

    <!-- Scoring Methods Configuration -->
    <div class="flex flex-col gap-3 p-3 bg-muted/20 border border-border/30 rounded-lg">
      <span class="text-xs font-bold text-foreground uppercase tracking-wider">Algorithm Scoring Methods</span>

      <div class="flex items-center justify-between gap-2">
        <div class="flex flex-col">
          <span class="font-bold text-xs text-foreground">Method A: Relevance Weighting</span>
          <span class="text-[11px] text-muted-foreground">Applies tiered title and description point weights</span>
        </div>
        <Switch
          checked={controller.searchMethods.method_a ?? true}
          onCheckedChange={(val) => { controller.searchMethods.method_a = val; }}
        />
      </div>

      <div class="flex items-center justify-between gap-2">
        <div class="flex flex-col">
          <span class="font-bold text-xs text-foreground">Method B: Stopwords Removal</span>
          <span class="text-[11px] text-muted-foreground">Filters language stopwords and articles</span>
        </div>
        <Switch
          checked={controller.searchMethods.method_b ?? true}
          onCheckedChange={(val) => { controller.searchMethods.method_b = val; }}
        />
      </div>

      <div class="flex items-center justify-between gap-2">
        <div class="flex flex-col">
          <span class="font-bold text-xs text-foreground">Method C: Diacritics & Boundaries</span>
          <span class="text-[11px] text-muted-foreground">Normalizes accents and word boundaries</span>
        </div>
        <Switch
          checked={controller.searchMethods.method_c ?? true}
          onCheckedChange={(val) => { controller.searchMethods.method_c = val; }}
        />
      </div>

      <div class="flex items-center justify-between gap-2">
        <div class="flex flex-col">
          <span class="font-bold text-xs text-foreground">Method D: Time-Aware Boost</span>
          <span class="text-[11px] text-muted-foreground">Prioritizes live broadcasts and near-future shows</span>
        </div>
        <Switch
          checked={controller.searchMethods.method_d ?? true}
          onCheckedChange={(val) => { controller.searchMethods.method_d = val; }}
        />
      </div>
    </div>

    <!-- Action Buttons Footer -->
    <div class="flex items-center justify-between gap-2 pt-2 border-t border-border/20">
      <Button
        variant="ghost"
        size="sm"
        onclick={() => controller.resetFilters()}
        class="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1.5 touch-btn"
      >
        <RotateCcw class="w-3.5 h-3.5" />
        <span>Reset All</span>
      </Button>

      <Button
        variant="primary"
        size="sm"
        onclick={handleClose}
        class="touch-btn text-xs font-bold"
      >
        Done
      </Button>
    </div>
  </div>
</Dialog>
