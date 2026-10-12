<script lang="ts">
  import { Radio } from '@lucide/svelte';

  interface Props {
    label?: string;
    animate?: boolean;
    onclick?: (e: MouseEvent) => void;
    class?: string;
  }

  let {
    label = 'LIVE',
    animate = true,
    onclick,
    class: className = ''
  }: Props = $props();
</script>

{#if onclick}
  <button
    type="button"
    {onclick}
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-destructive/20 border border-destructive/40 text-destructive hover:bg-destructive/30 transition-colors cursor-pointer touch-btn select-none {animate ? 'animate-pulse' : ''} {className}"
    title={label}
  >
    <Radio class="w-3 h-3 text-destructive shrink-0" />
    <span>{label}</span>
  </button>
{:else}
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-destructive/20 border border-destructive/40 text-destructive select-none {animate ? 'animate-pulse' : ''} {className}"
    title={label}
  >
    <Radio class="w-3 h-3 text-destructive shrink-0" />
    <span>{label}</span>
  </span>
{/if}
