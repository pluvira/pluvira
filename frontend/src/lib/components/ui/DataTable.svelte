<script lang="ts" generics="T">
  import type { Snippet } from 'svelte';
  import { sortTableData, paginateData, type TableColumn, type SortState } from './TableUtils';
  import Button from './Button.svelte';
  import { ChevronUp, ChevronDown } from '@lucide/svelte';

  interface Props {
    data?: T[];
    columns?: TableColumn<T>[];
    rowKey?: keyof T;
    selectable?: boolean;
    selectedKeys?: Set<string>;
    pageSize?: number;
    class?: string;
    cellSnippet?: Snippet<[T, TableColumn<T>]>;
  }

  let {
    data = [],
    columns = [],
    rowKey = 'id' as keyof T,
    selectable = false,
    selectedKeys = $bindable(),
    pageSize = $bindable(),
    class: className = '',
    cellSnippet
  }: Props = $props();

  let currentPage = $state(1);
  let sortState = $state<SortState>({ columnKey: null, direction: null });
  let effectivePageSize = $derived(pageSize ?? 25);
  let currentSelectedKeys = $derived(selectedKeys ?? new Set<string>());

  let pipelineResult = $derived.by(() => {
    const sorted = sortTableData(data, sortState);
    const totalCount = sorted.length;
    const totalPages = Math.max(1, Math.ceil(totalCount / effectivePageSize));
    let safePage = currentPage;
    if (safePage > totalPages && totalPages > 0) safePage = totalPages;
    if (safePage < 1) safePage = 1;
    const items = paginateData(sorted, safePage, effectivePageSize);
    return { items, totalPages, totalCount, safePage };
  });

  let displayedItems = $derived(pipelineResult.items);
  let totalPages = $derived(pipelineResult.totalPages);
  let totalCount = $derived(pipelineResult.totalCount);

  $effect(() => {
    if (currentPage !== pipelineResult.safePage) {
      currentPage = pipelineResult.safePage;
    }
  });

  function handleSort(key: string) {
    if (sortState.columnKey !== key) {
      sortState = { columnKey: key, direction: 'asc' };
    } else if (sortState.direction === 'asc') {
      sortState = { columnKey: key, direction: 'desc' };
    } else {
      sortState = { columnKey: null, direction: null };
    }
  }

  function handleSelectRow(keyVal: string) {
    const newSet = new Set(currentSelectedKeys);
    if (newSet.has(keyVal)) newSet.delete(keyVal);
    else newSet.add(keyVal);
    selectedKeys = newSet;
  }

  function handleSelectAll() {
    const newSet = new Set(currentSelectedKeys);
    const allKeys = data.map((row) => String(row[rowKey]));
    const allSelected = allKeys.length > 0 && allKeys.every((k) => newSet.has(k));

    if (allSelected) {
      allKeys.forEach((k) => newSet.delete(k));
    } else {
      allKeys.forEach((k) => newSet.add(k));
    }
    selectedKeys = newSet;
  }

  function setPage(p: number) {
    if (p >= 1 && p <= totalPages) {
      currentPage = p;
    }
  }

  let isAllSelected = $derived(
    data.length > 0 && data.every((row) => currentSelectedKeys.has(String(row[rowKey])))
  );
</script>

<div class="surface-card overflow-hidden flex flex-col w-full {className}">
  <div class="overflow-x-auto w-full">
    <table class="table-base">
      <thead>
        <tr>
          {#if selectable}
            <th class="table-th w-9 text-center shrink-0">
              <input type="checkbox" checked={isAllSelected} onchange={handleSelectAll} class="cursor-pointer" />
            </th>
          {/if}
          {#each columns as col (col.key)}
            <th class="table-th select-none {col.width || ''} {col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left'}">
              {#if col.sortable}
                <button
                  type="button"
                  onclick={() => handleSort(col.key)}
                  class="flex items-center gap-1 hover:text-foreground cursor-pointer font-bold uppercase text-xs {col.align === 'center' ? 'justify-center mx-auto' : col.align === 'right' ? 'justify-end ml-auto' : 'justify-start'}"
                >
                  <span>{col.label}</span>
                  {#if sortState.columnKey === col.key}
                    {#if sortState.direction === 'asc'}
                      <ChevronUp class="w-3.5 h-3.5" />
                    {:else}
                      <ChevronDown class="w-3.5 h-3.5" />
                    {/if}
                  {/if}
                </button>
              {:else}
                <span class={col.align === 'center' ? 'block text-center' : col.align === 'right' ? 'block text-right' : ''}>{col.label}</span>
              {/if}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#if displayedItems.length === 0}
          <tr>
            <td colspan={columns.length + (selectable ? 1 : 0)} class="p-8 text-center text-muted-foreground italic">
              No data records found.
            </td>
          </tr>
        {:else}
          {#each displayedItems as row (String(row[rowKey]))}
            {@const keyStr = String(row[rowKey])}
            {@const isSelected = currentSelectedKeys.has(keyStr)}
            <tr class="table-tr {isSelected ? 'bg-primary/10' : ''}">
              {#if selectable}
                <td class="table-td w-9 text-center shrink-0">
                  <input type="checkbox" checked={isSelected} onchange={() => handleSelectRow(keyStr)} class="cursor-pointer" />
                </td>
              {/if}
              {#each columns as col (col.key)}
                <td class="table-td overflow-hidden {col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left'}">
                  {#if cellSnippet}
                    {@render cellSnippet(row, col)}
                  {:else}
                    {col.getValue ? col.getValue(row) : ((row as any)[col.key] ?? '—')}
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>

  <div class="flex items-center justify-between px-4 py-2 bg-background border-t border-border/30 text-xs text-muted-foreground flex-wrap gap-2">
    <span>Showing {displayedItems.length} of {totalCount} items</span>

    <div class="flex items-center gap-4">
      <div class="flex items-center gap-1.5">
        <label for="table-page-size-select" class="text-xs text-muted-foreground font-bold">Rows:</label>
        <select
          id="table-page-size-select"
          value={effectivePageSize}
          onchange={(e) => { pageSize = Number((e.target as HTMLSelectElement).value); }}
          class="select-compact"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={1000}>1000 (All)</option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <Button variant="ghost" size="sm" disabled={currentPage <= 1} onclick={() => setPage(currentPage - 1)}>
          Prev
        </Button>
        <span class="font-bold text-foreground">Page {currentPage} of {totalPages}</span>
        <Button variant="ghost" size="sm" disabled={currentPage >= totalPages} onclick={() => setPage(currentPage + 1)}>
          Next
        </Button>
      </div>
    </div>
  </div>
</div>
