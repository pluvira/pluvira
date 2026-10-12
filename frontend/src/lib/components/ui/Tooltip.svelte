<script lang="ts">
  import type { Snippet } from 'svelte';
  import { Tooltip as BitsTooltip } from 'bits-ui';

  interface Props {
    text?: string;
    side?: 'top' | 'right' | 'bottom' | 'left';
    delayDuration?: number;
    children?: Snippet;
    content?: Snippet;
    class?: string;
  }

  let {
    text = '',
    side = 'top',
    delayDuration = 200,
    children,
    content,
    class: className = ''
  }: Props = $props();
</script>

<BitsTooltip.Root {delayDuration}>
  <BitsTooltip.Trigger class="inline-flex cursor-pointer">
    {#if children}
      {@render children()}
    {/if}
  </BitsTooltip.Trigger>
  <BitsTooltip.Portal>
    <BitsTooltip.Content
      {side}
      class="z-50 overflow-hidden rounded-md bg-card border border-border px-2.5 py-1 text-xs text-foreground shadow-md animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 {className}"
    >
      {#if content}
        {@render content()}
      {:else}
        <span>{text}</span>
      {/if}
      <BitsTooltip.Arrow class="border-t border-border fill-card" />
    </BitsTooltip.Content>
  </BitsTooltip.Portal>
</BitsTooltip.Root>
