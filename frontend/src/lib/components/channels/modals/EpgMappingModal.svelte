<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import Dialog from '../../ui/Dialog.svelte';
  import Select from '../../ui/Select.svelte';
  import DebouncedInput from '../../ui/DebouncedInput.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import type { ChannelItem, EpgChannelIndexItem } from '$lib/api/types';
  import { ScannerMappingController, calculateSimilarityScore } from '../utils/ScannerMappingController.svelte';
  import { Search, Check, Radio } from '@lucide/svelte';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let { channel = null, open = $bindable(), onclose, onsaved }: Props = $props();

  const controller = new ScannerMappingController();

  let selectedSource = $state('');
  let searchQuery = $state('');
  let selectedEpgId = $state('');
  let isGlobal = $state(false);
  let searchResults = $state<Array<EpgChannelIndexItem & { score: number }>>([]);

  let sourceOptions = $derived([
    { label: 'All Sources', value: '' },
    ...controller.epgSources.map((s) => ({ label: s.name, value: s.name }))
  ]);

  async function performSearch(source: string, query: string) {
    const res = await controller.searchEpgChannels(source || undefined, query.trim() || undefined, 100);
    const targetName = channel?.name || '';
    searchResults = res.map((item) => ({
      ...item,
      score: calculateSimilarityScore(targetName, query, item.name)
    })).sort((a, b) => b.score - a.score);
  }

  function handleSourceChange(source: string | number | null | undefined) {
    selectedSource = String(source ?? '');
    performSearch(selectedSource, searchQuery);
  }

  function handleQueryChange(query: string) {
    searchQuery = query;
    performSearch(selectedSource, searchQuery);
  }

  let lastInitKey = '';
  function initModalState(ch: ChannelItem) {
    selectedEpgId = ch.epg_id || '';
    searchQuery = ch.name || '';
    selectedSource = ch.epg_id && ch.epg_id.includes('::') ? ch.epg_id.split('::')[0] : '';
    performSearch(selectedSource, searchQuery);
  }

  $effect(() => {
    if (!open) { lastInitKey = ''; return; }
    if (open && channel) {
      const currentKey = `${channel.id}_${channel.source}`;
      if (currentKey !== lastInitKey) {
        lastInitKey = currentKey;
        untrack(() => initModalState(channel!));
      }
    }
  });

  async function handleSave() {
    if (!channel || !selectedEpgId.trim()) return;
    const ok = await controller.saveEpgMapping({
      channel_name: channel.name,
      source_name: channel.source,
      epg_id: selectedEpgId.trim(),
      is_global: isGlobal
    });
    if (ok) {
      channel.epg_id = selectedEpgId.trim();
      channel.is_mapped = true;
      open = false;
      onsaved?.();
    }
  }

  onMount(() => { controller.loadEpgSources(); });
</script>

<Dialog bind:open title="Manual EPG Mapping Override" {onclose} class="max-w-2xl">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">Cancel</Button>
    <Button variant="primary" size="sm" disabled={controller.savingMapping || !selectedEpgId.trim()} onclick={handleSave} class="font-bold touch-btn">
      {controller.savingMapping ? 'Saving...' : 'Save Mapping'}
    </Button>
  {/snippet}

  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs">
      <!-- Clean Channel Identity Header -->
      <div class="surface-darkest p-3 rounded border border-border/40 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 truncate">
          <Radio class="w-4 h-4 text-primary shrink-0" />
          <span class="font-bold text-foreground text-sm truncate">{channel.name}</span>
          <span class="text-muted-foreground text-xs">({channel.source})</span>
        </div>
        {#if selectedEpgId}
          <Badge variant="primary" class="font-mono text-[10px] shrink-0">Mapped</Badge>
        {/if}
      </div>

      <!-- Controls Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
        <Select
          label="EPG Source"
          bind:value={selectedSource}
          options={sourceOptions}
          onchange={(e) => handleSourceChange((e.target as HTMLSelectElement).value)}
        />

        <DebouncedInput
          label="Channel Name"
          bind:value={searchQuery}
          delayMs={250}
          placeholder="Search EPG channel..."
          onchange={handleQueryChange}
        />
      </div>

      <!-- Results List Ordered by Confidence -->
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-muted-foreground font-bold">
          <span class="text-caps-label flex items-center gap-1">
            <Search class="w-3.5 h-3.5 text-primary" />
            <span>Matching EPG Channels:</span>
          </span>
          {#if searchResults.length > 0}
            <span class="text-[10px] font-normal">{searchResults.length} candidate(s)</span>
          {/if}
        </div>

        {#if controller.loadingEpgChannels}
          <div class="surface-darkest p-6 rounded border border-border/30 flex items-center justify-center gap-2 text-muted-foreground">
            <span class="spinner !w-4 !h-4"></span>
            <span>Searching EPG index across guides...</span>
          </div>
        {:else if searchResults.length === 0}
          <div class="surface-darkest p-6 rounded border border-border/30 text-center text-muted-foreground italic">
            No matching EPG channels found for '{searchQuery}'. Try searching with different keywords or source.
          </div>
        {:else}
          <div class="surface-darkest border border-border/40 rounded-md max-h-56 overflow-y-auto flex flex-col gap-1 p-1">
            {#each searchResults as item (item.id)}
              {@const isSelected = selectedEpgId === item.id}
              <button
                type="button"
                onclick={() => (selectedEpgId = item.id)}
                class="flex items-center justify-between p-2 rounded text-left transition-colors cursor-pointer border {isSelected ? 'bg-primary/15 border-primary text-foreground' : 'border-border/20 hover:bg-card text-muted-foreground hover:text-foreground'}"
              >
                <div class="flex items-center gap-2 min-w-0 pr-2">
                  <span class="w-2.5 h-2.5 rounded-full border {isSelected ? 'bg-primary border-primary' : 'border-muted-foreground/50'} shrink-0"></span>
                  <div class="flex flex-col gap-0.5 truncate">
                    <div class="flex items-center gap-1.5 truncate">
                      <span class="font-bold text-xs text-foreground truncate">{item.name}</span>
                      <Badge variant="muted" class="text-[9px] py-0 px-1">{item.source}</Badge>
                    </div>
                    <span class="font-mono text-[10px] text-muted-foreground truncate">id: {item.id}</span>
                  </div>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  <Badge variant={item.score >= 90 ? 'success' : item.score >= 75 ? 'warning' : 'muted'} class="text-[10px]">
                    {item.score}% Match
                  </Badge>
                  {#if isSelected}
                    <Check class="w-4 h-4 text-primary shrink-0" />
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <label class="flex items-center gap-2 cursor-pointer text-muted-foreground select-none pt-1">
        <input type="checkbox" bind:checked={isGlobal} class="rounded text-primary" />
        <span>Make mapping global across all playlist sources</span>
      </label>
    </div>
  {/if}
</Dialog>
