<script lang="ts">
  import Badge from '../ui/Badge.svelte';
  import {
    getDayBounds,
    calculateBlockPosition,
    isProgrammeCurrentlyLive,
    type EpgProgramItem,
    type RenderedBlock
  } from './utils';

  interface Props {
    programmes?: EpgProgramItem[];
    selectedDateStr?: string;
    showDateBadge?: boolean;
    onselectprogram?: (block: RenderedBlock) => void;
    class?: string;
  }

  let {
    programmes = [],
    selectedDateStr = (() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    })(),
    showDateBadge = false,
    onselectprogram,
    class: className = ''
  }: Props = $props();

  let scrollContainer = $state<HTMLDivElement | null>(null);
  let liveRowEl = $state<HTMLTableRowElement | null>(null);

  function liveRowAction(node: HTMLTableRowElement, isLive: boolean) {
    if (isLive) {
      liveRowEl = node;
      requestAnimationFrame(() => {
        if (scrollContainer) {
          const theadHeight = scrollContainer.querySelector('thead')?.clientHeight || 28;
          scrollContainer.scrollTop = Math.max(0, node.offsetTop - theadHeight);
        }
      });
    }
  }

  $effect(() => {
    if (renderedBlocks.length > 0 && liveRowEl && scrollContainer) {
      const timer = setTimeout(() => {
        if (liveRowEl && scrollContainer) {
          const theadHeight = scrollContainer.querySelector('thead')?.clientHeight || 28;
          scrollContainer.scrollTop = Math.max(0, liveRowEl.offsetTop - theadHeight);
        }
      }, 50);
      return () => clearTimeout(timer);
    }
    return undefined;
  });

  let renderedBlocks = $derived.by(() => {
    const [dayStart, dayEnd] = getDayBounds(selectedDateStr);
    const result: RenderedBlock[] = [];
    const seen = new Set<string>();

    programmes.forEach((p) => {
      const key = `${p.s}::${p.e || ''}::${p.t}`;
      if (seen.has(key)) return;
      seen.add(key);
      const pos = calculateBlockPosition(p, dayStart, dayEnd);
      if (pos) result.push(pos);
    });

    return result;
  });
</script>

<div class="flex flex-col gap-1.5 w-full h-full min-h-0 max-h-full text-xs overflow-hidden {className}">
  {#if showDateBadge}
    <div class="flex items-center justify-end mb-1">
      <Badge variant="primary">{selectedDateStr}</Badge>
    </div>
  {/if}

  <div bind:this={scrollContainer} class="bg-background border border-border/30 rounded flex-1 min-h-0 h-full max-h-full overflow-y-auto overflow-x-hidden w-full relative scrollbar-thin">
    {#if renderedBlocks.length === 0}
      <div class="p-6 text-center text-muted-foreground italic">
        No programme schedules found for this date.
      </div>
    {:else}
      <table class="table-base table-fixed w-full">
        <thead class="sticky top-0 z-10 bg-card/95 backdrop-blur-xs border-b border-border/30">
          <tr>
            <th class="table-th w-16 text-left">Time</th>
            <th class="table-th text-left truncate">Title</th>
            <th class="table-th w-12 text-right">Dur</th>
          </tr>
        </thead>
        <tbody>
          {#each renderedBlocks as item, idx (item.program.s + '_' + (item.program.e || '') + '_' + item.program.t + '_' + idx)}
            {@const isLive = isProgrammeCurrentlyLive(item.program, new Date())}
            <tr
              use:liveRowAction={isLive}
              onclick={() => onselectprogram?.(item)}
              class="table-tr cursor-pointer {isLive ? 'bg-primary/15 hover:bg-primary/25 font-bold' : ''}"
            >
              <td class="table-td text-left font-mono text-[11px] {isLive ? 'text-primary font-bold' : 'text-foreground font-semibold'}">
                <div class="flex items-center gap-1">
                  {#if isLive}
                    <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shrink-0"></span>
                  {/if}
                  <span class="truncate">{item.timeLabel.split(' - ')[0] || item.timeLabel}</span>
                </div>
              </td>
              <td class="table-td text-left truncate">
                <span class="truncate block {isLive ? 'font-bold text-primary' : 'text-foreground'}">{item.program.t}</span>
              </td>
              <td class="table-td text-right text-[11px] font-mono text-muted-foreground">{item.durationMins}m</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>
