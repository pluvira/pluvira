<script lang="ts">
  import type { RenderedBlock } from './utils';

  interface Props {
    block: RenderedBlock;
    isSearchActive?: boolean;
    onclick?: (block: RenderedBlock) => void;
    class?: string;
  }

  let { block, isSearchActive = false, onclick, class: className = '' }: Props = $props();

  let isMatch = $derived(isSearchActive && (block.matchScore || 0) > 0);
  let isDimmed = $derived(isSearchActive && (block.matchScore || 0) === 0);
</script>

<button
  type="button"
  onclick={() => onclick?.(block)}
  style="left: {block.leftPx}px; width: {block.widthPx}px;"
  class="surface-card absolute top-1 bottom-1 hover:bg-card/90 hover:border-foreground !p-1 text-left flex flex-col justify-center cursor-pointer overflow-hidden transition-all duration-150 !shadow-xs {isMatch ? '!bg-primary/20 !border-primary !text-foreground z-20 shadow-md ring-1 ring-primary/50' : isDimmed ? 'opacity-30 grayscale-[60%]' : ''} {className}"
  title={`${block.program.t} (${block.timeLabel}, ${block.durationMins}m)${isMatch ? ` [Match Score: ${block.matchScore}]` : ''}`}
>
  <div class="flex items-center justify-between gap-1 w-full truncate">
    <span class="text-xs font-bold truncate flex-1 {isMatch ? 'text-primary font-bold' : 'text-foreground'}">
      {block.program.t}
    </span>
    {#if isMatch}
      <span class="bg-primary text-primary-foreground text-[9px] font-extrabold px-1 rounded shrink-0">MATCH</span>
    {/if}
  </div>
  <span class="text-[10px] truncate w-full block {isMatch ? 'text-primary' : 'text-muted-foreground'}">
    {block.timeLabel} ({block.durationMins}m)
  </span>
</button>
