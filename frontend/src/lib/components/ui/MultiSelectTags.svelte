<script lang="ts">
  import { X } from '@lucide/svelte';
  import {
    formatTagOptions,
    getUnselectedTagOptions,
    addTagValue,
    removeTagValue,
    type TagOption
  } from '$lib/utils/arrayUtils';

  interface Props {
    id?: string;
    label?: string;
    selectedValues?: string[];
    options?: TagOption[] | string[];
    placeholder?: string;
    onchange?: (selected: string[]) => void;
    class?: string;
  }

  let {
    id,
    label = '',
    selectedValues = $bindable(),
    options = [],
    placeholder = 'Select items...',
    onchange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `multiselect-${Math.random().toString(36).substring(2, 9)}`);

  let currentSelected = $derived(selectedValues || []);
  let formattedOptions = $derived<TagOption[]>(formatTagOptions(options));
  let unselectedOptions = $derived<TagOption[]>(getUnselectedTagOptions(formattedOptions, currentSelected));

  function handleAddTag(val: string) {
    if (!val) return;
    selectedValues = addTagValue(currentSelected, val);
    if (onchange) onchange(selectedValues);
  }

  function handleRemoveTag(val: string) {
    selectedValues = removeTagValue(currentSelected, val);
    if (onchange) onchange(selectedValues);
  }

  function handleClearAll() {
    selectedValues = [];
    if (onchange) onchange([]);
  }

  function handleSelectChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    const val = target.value;
    if (val) {
      handleAddTag(val);
      target.value = '';
    }
  }
</script>

<div class="flex flex-col gap-1 w-full {className}">
  <div class="flex items-center justify-between">
    {#if label}
      <label for={elementId} class="text-xs font-bold text-muted-foreground">{label}</label>
    {/if}
    {#if currentSelected.length > 0}
      <button
        type="button"
        onclick={handleClearAll}
        class="text-[10px] text-muted-foreground hover:text-foreground cursor-pointer underline"
      >
        Clear ({currentSelected.length})
      </button>
    {/if}
  </div>

  {#if currentSelected.length > 0}
    <div class="flex flex-wrap items-center gap-1.5 p-1.5 bg-background border border-border rounded-md min-h-[36px]">
      {#each currentSelected as val (val)}
        {@const optLabel = formattedOptions.find((o) => o.value === val)?.label || (val === '' ? '(Uncategorized)' : val)}
        <span class="inline-flex items-center gap-1 bg-card text-foreground border border-border/50 text-xs px-2 py-0.5 rounded-sm">
          <span>{optLabel}</span>
          <button
            type="button"
            onclick={() => handleRemoveTag(val)}
            class="text-muted-foreground hover:text-primary text-xs font-bold cursor-pointer ml-1"
            title="Remove filter tag"
          >
            <X class="w-3 h-3" />
          </button>
        </span>
      {/each}
    </div>
  {/if}

  <select
    id={elementId}
    onchange={handleSelectChange}
    class="input-base cursor-pointer"
  >
    <option value="" class="bg-card text-muted-foreground">{placeholder}</option>
    {#each unselectedOptions as opt (opt.value)}
      <option value={opt.value} class="bg-card text-foreground">{opt.label}</option>
    {/each}
  </select>
</div>
