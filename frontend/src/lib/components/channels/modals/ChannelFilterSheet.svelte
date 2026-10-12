<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Select from '../../ui/Select.svelte';
  import MultiSelectTags from '../../ui/MultiSelectTags.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import { RotateCcw, Check } from '@lucide/svelte';
  import type { ChannelFilterOptions } from '../utils/ChannelsUtils';
  import { countChannelFilters } from '$lib/utils/objectUtils';
  import { playlistStore } from '$lib/stores/playlistStore';

  interface Props {
    open?: boolean;
    filters: ChannelFilterOptions;
    availableGroups?: Array<{ label: string; value: string }>;
    availableSources?: Array<{ label: string; value: string }>;
    onapply?: (draft: ChannelFilterOptions) => void;
    onclose?: () => void;
  }

  let {
    open = $bindable(),
    filters,
    availableGroups = [],
    availableSources = [],
    onapply,
    onclose
  }: Props = $props();

  const confirmController = new ConfirmController();

  let draftFilters = $state<ChannelFilterOptions>({
    searchQuery: '',
    selectedGroups: [],
    selectedSources: [],
    linkStatus: 'all',
    inclusionStatus: 'all',
    epgStatus: 'all',
    corsStatus: 'all',
    bookmarkStatus: 'all'
  });

  $effect(() => {
    if (open) {
      draftFilters = {
        searchQuery: filters.searchQuery || '',
        selectedGroups: [...(filters.selectedGroups || [])],
        selectedSources: [...(filters.selectedSources || [])],
        linkStatus: filters.linkStatus || 'all',
        inclusionStatus: filters.inclusionStatus || 'all',
        epgStatus: filters.epgStatus || 'all',
        corsStatus: filters.corsStatus || 'all',
        bookmarkStatus: filters.bookmarkStatus || 'all'
      };
    }
  });

  let activeDraftCount = $derived(countChannelFilters(draftFilters));

  let favoriteOptions = $derived.by(() => {
    const base = [
      { label: 'All Channels', value: 'all' },
      { label: 'Any Curated List (★)', value: 'bookmarked' },
      { label: 'Non-Favorites Only', value: 'not_bookmarked' }
    ];
    const lists = $playlistStore.playlists || [];
    if (lists.length > 0) {
      const listOptions = lists.map((pl) => ({
        label: `In: ${pl.name || pl.id}`,
        value: `playlist:${pl.id}`
      }));
      return [base[0], base[1], ...listOptions, base[2]];
    }
    return base;
  });

  function handleReset() {
    confirmController.requestConfirm('filter_reset', () => {
      draftFilters = {
        searchQuery: '',
        selectedGroups: [],
        selectedSources: [],
        linkStatus: 'all',
        inclusionStatus: 'all',
        epgStatus: 'all',
        corsStatus: 'all',
        bookmarkStatus: 'all'
      };
      onapply?.(draftFilters);
      open = false;
    });
  }

  function handleApply() {
    onapply?.(draftFilters);
    open = false;
  }
</script>

<Dialog bind:open title="Filter Channels" {onclose} class="max-w-lg">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={handleReset} class="flex items-center gap-1.5 touch-btn text-muted-foreground hover:text-foreground">
      <RotateCcw class="w-3.5 h-3.5" />
      <span>Reset Filters</span>
    </Button>
    <Button variant="primary" size="sm" onclick={handleApply} class="flex items-center gap-1.5 font-bold touch-btn">
      <Check class="w-3.5 h-3.5" />
      <span>Apply Filters {activeDraftCount > 0 ? `(${activeDraftCount})` : ''}</span>
    </Button>
  {/snippet}

  <div class="flex flex-col gap-4 w-full text-xs">
    <ConfirmDialog
      bind:open={confirmController.open}
      scope={confirmController.scope}
      onconfirm={() => confirmController.handleConfirm()}
    />
    <MultiSelectTags
      label="Groups Filter"
      placeholder="Select groups..."
      options={availableGroups}
      bind:selectedValues={draftFilters.selectedGroups}
    />

    <MultiSelectTags
      label="Sources Filter"
      placeholder="Select sources..."
      options={availableSources}
      bind:selectedValues={draftFilters.selectedSources}
    />

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <Select
        label="Stream Link Status"
        bind:value={draftFilters.linkStatus}
        options={[
          { label: 'All Links', value: 'all' },
          { label: 'Online (OK)', value: 'online' },
          { label: 'Offline (KO)', value: 'offline' },
          { label: 'Unchecked', value: 'unchecked' }
        ]}
      />

      <Select
        label="Catalog Visibility"
        bind:value={draftFilters.inclusionStatus}
        options={[
          { label: 'All Channels', value: 'all' },
          { label: 'Visible Only', value: 'included' },
          { label: 'Hidden Only', value: 'excluded' }
        ]}
      />
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <Select
        label="EPG Guide Mapping"
        bind:value={draftFilters.epgStatus}
        options={[
          { label: 'All EPG', value: 'all' },
          { label: 'Mapped Only', value: 'mapped' },
          { label: 'Unmapped Only', value: 'unmapped' }
        ]}
      />

      <Select
        label="CORS / Proxy Mode"
        bind:value={draftFilters.corsStatus}
        options={[
          { label: 'All CORS', value: 'all' },
          { label: 'CORS OK', value: 'cors_ok' },
          { label: 'Requires Proxy', value: 'needs_proxy' }
        ]}
      />
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <Select
        label="Favorites / Curated List"
        bind:value={draftFilters.bookmarkStatus}
        options={favoriteOptions}
      />
    </div>
  </div>
</Dialog>
