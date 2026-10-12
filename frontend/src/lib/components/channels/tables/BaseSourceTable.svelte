<script lang="ts" generics="T extends { name: string; enabled: boolean; status: string }">
  import type { Snippet } from 'svelte';
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import { RotateCw, Zap, Pause } from '@lucide/svelte';

  interface Props {
    title: string;
    items?: T[];
    isCompact?: boolean;
    nameHeader?: string;
    refreshTitle?: string;
    ontogglestatus?: (name: string) => void;
    onsetallstate?: (enable: boolean) => void;
    onrefreshnames?: (names: string[]) => void;
    extraHeaders?: Snippet;
    rowCells?: Snippet<[T]>;
    actionLinks?: Snippet<[T]>;
    class?: string;
  }

  let {
    title,
    items = [],
    isCompact = false,
    nameHeader = 'Source Provider',
    refreshTitle = 'Refresh All Sources',
    ontogglestatus,
    onsetallstate,
    onrefreshnames,
    extraHeaders,
    rowCells,
    actionLinks,
    class: className = ''
  }: Props = $props();
</script>

{#if items.length > 0}
  <Card {title} class="w-full h-full flex flex-col justify-between {className}">
    {#snippet actions()}
      <Button variant="ghost" size="sm" onclick={() => onrefreshnames?.(items.map(s => s.name))} class="!p-1 text-xs text-blue-400" title={refreshTitle}>
        <RotateCw class="w-3.5 h-3.5" />
      </Button>
      <Button variant="ghost" size="sm" onclick={() => onsetallstate?.(true)} class="!p-1 text-xs" title="Enable All Sources">
        <Zap class="w-3.5 h-3.5" />
      </Button>
      <Button variant="ghost" size="sm" onclick={() => onsetallstate?.(false)} class="!p-1 text-xs" title="Disable All Sources">
        <Pause class="w-3.5 h-3.5" />
      </Button>
    {/snippet}

    <div class="overflow-x-auto w-full flex-1 max-h-80 overflow-y-auto">
      <table class="table-base {isCompact ? '!text-[11px]' : ''}">
        <thead>
          <tr>
            <th class="table-th">{nameHeader}</th>
            <th class="table-th text-center">Status</th>
            {#if !isCompact && extraHeaders}
              {@render extraHeaders()}
            {/if}
            <th class="table-th text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each items as src (src.name)}
            <tr class="table-tr {!src.enabled ? 'opacity-60' : ''}">
              <td class="table-td font-bold text-foreground {isCompact ? '!p-1.5' : ''}">{src.name}</td>
              <td class="table-td text-center">
                <Button
                  variant={src.enabled ? 'primary' : 'secondary'}
                  size="sm"
                  onclick={() => ontogglestatus?.(src.name)}
                  class="!py-0.5 !px-2 text-xs font-bold uppercase"
                >
                  {src.status}
                </Button>
              </td>
              {#if !isCompact && rowCells}
                {@render rowCells(src)}
              {/if}
              <td class="table-td text-center">
                <div class="flex items-center justify-center gap-1">
                  {#if actionLinks}
                    {@render actionLinks(src)}
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </Card>
{/if}
