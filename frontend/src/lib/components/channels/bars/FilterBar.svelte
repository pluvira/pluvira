<script lang="ts">
  import type { Snippet } from 'svelte';
  import DebouncedInput from '../../ui/DebouncedInput.svelte';
  import Select, { type SelectOption } from '../../ui/Select.svelte';

  interface Props {
    searchQuery?: string;
    selectedGroup?: string;
    selectedSource?: string;
    groupOptions?: SelectOption[] | string[];
    sourceOptions?: SelectOption[] | string[];
    delayMs?: number;
    onsearch?: (query: string) => void;
    ongroupchange?: (group: string) => void;
    onsourcechange?: (source: string) => void;
    extraFilters?: Snippet;
    class?: string;
  }

  let {
    searchQuery = $bindable(),
    selectedGroup = $bindable(),
    selectedSource = $bindable(),
    groupOptions = [],
    sourceOptions = [],
    delayMs = 300,
    onsearch,
    ongroupchange,
    onsourcechange,
    extraFilters,
    class: className = ''
  }: Props = $props();

  function handleSearch(val: string) {
    searchQuery = val;
    if (onsearch) onsearch(val);
  }

  function handleGroupChange() {
    if (ongroupchange) ongroupchange(selectedGroup ?? '');
  }

  function handleSourceChange() {
    if (onsourcechange) onsourcechange(selectedSource ?? '');
  }
</script>

<div class="surface-card p-3 flex flex-wrap items-end gap-3 w-full {className}">
  <div class="w-full sm:w-64">
    <DebouncedInput label="Search" bind:value={searchQuery} {delayMs} placeholder="Search channels..." onchange={handleSearch} />
  </div>

  {#if groupOptions.length > 0}
    <div class="w-full sm:w-48">
      <Select
        bind:value={selectedGroup}
        options={groupOptions}
        label="Group"
        onchange={handleGroupChange}
      />
    </div>
  {/if}

  {#if sourceOptions.length > 0}
    <div class="w-full sm:w-48">
      <Select
        bind:value={selectedSource}
        options={sourceOptions}
        label="Source"
        onchange={handleSourceChange}
      />
    </div>
  {/if}

  {#if extraFilters}
    <div class="flex items-end gap-2 flex-wrap">
      {@render extraFilters()}
    </div>
  {/if}
</div>
