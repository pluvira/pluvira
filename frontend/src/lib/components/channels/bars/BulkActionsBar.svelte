<script lang="ts">
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';

  interface Props {
    selectedCount?: number;
    allSelected?: boolean;
    isIndeterminate?: boolean;
    onToggleSelectAll?: (select: boolean) => void;
    onIncludeAll?: () => void;
    onExcludeAll?: () => void;
    onTestAll?: () => void;
    onEditGroup?: () => void;
    onEditUserAgent?: () => void;
    onResetRewrites?: () => void;
    onClearSelection?: () => void;
    class?: string;
  }

  let {
    selectedCount = 0,
    allSelected = false,
    isIndeterminate = false,
    onToggleSelectAll,
    onIncludeAll,
    onExcludeAll,
    onTestAll,
    onEditGroup,
    onEditUserAgent,
    onResetRewrites,
    onClearSelection,
    class: className = ''
  }: Props = $props();
</script>

{#if selectedCount > 0}
  <div class="surface-card border-l-4 !border-l-primary p-3 shadow-elevated flex flex-wrap items-center justify-between gap-3 w-full animate-fade-in {className}">
    <div class="flex items-center gap-2">
      <Badge variant="primary">{selectedCount}</Badge>
      <span class="text-xs font-bold text-foreground uppercase tracking-wider">Channels Selected</span>
      <Button variant="ghost" size="sm" onclick={onClearSelection} class="text-xs !py-0.5">Clear</Button>
    </div>

    <div class="flex items-center gap-1.5 flex-wrap">
      {#if onToggleSelectAll}
        <label class="flex items-center gap-1.5 cursor-pointer select-none text-xs font-bold text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-card transition-colors mr-1">
          <input
            type="checkbox"
            checked={allSelected}
            indeterminate={isIndeterminate}
            onchange={(e) => onToggleSelectAll?.((e.target as HTMLInputElement).checked)}
            class="rounded text-primary cursor-pointer w-4 h-4"
            aria-label={allSelected ? 'Deselect all channels' : 'Select all channels'}
          />
          <span class="hidden sm:inline">{allSelected ? 'Deselect All' : 'Select All'}</span>
        </label>
      {/if}
      {#if onIncludeAll}
        <Button variant="secondary" size="sm" onclick={onIncludeAll} class="!py-1 text-xs" title="Make selected channels visible in catalog">
          SHOW
        </Button>
      {/if}
      {#if onExcludeAll}
        <Button variant="secondary" size="sm" onclick={onExcludeAll} class="!py-1 text-xs" title="Hide selected channels from catalog">
          HIDE
        </Button>
      {/if}
      {#if onTestAll}
        <Button variant="secondary" size="sm" onclick={onTestAll} class="!py-1 text-xs">
          TEST
        </Button>
      {/if}
      {#if onEditGroup}
        <Button variant="outline" size="sm" onclick={onEditGroup} class="!py-1 text-xs">
          GROUP
        </Button>
      {/if}
      {#if onEditUserAgent}
        <Button variant="outline" size="sm" onclick={onEditUserAgent} class="!py-1 text-xs">
          UA
        </Button>
      {/if}
      {#if onResetRewrites}
        <Button variant="danger" size="sm" onclick={onResetRewrites} class="!py-1 text-xs">
          RESET
        </Button>
      {/if}
    </div>
  </div>
{/if}
