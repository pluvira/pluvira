<script lang="ts">
  import type { Snippet } from 'svelte';
  import { DropdownMenu as BitsDropdownMenu } from 'bits-ui';

  export interface DropdownMenuItemConfig {
    label: string;
    disabled?: boolean;
    onclick?: () => void;
  }

  interface Props {
    open?: boolean;
    trigger?: Snippet;
    items?: DropdownMenuItemConfig[];
    children?: Snippet;
    class?: string;
  }

  let {
    open = $bindable(),
    trigger,
    items = [],
    children,
    class: className = ''
  }: Props = $props();
</script>

<BitsDropdownMenu.Root bind:open>
  <BitsDropdownMenu.Trigger class="inline-flex cursor-pointer">
    {#if trigger}
      {@render trigger()}
    {/if}
  </BitsDropdownMenu.Trigger>

  <BitsDropdownMenu.Portal>
    <BitsDropdownMenu.Content
      class="surface-modal min-w-[140px] p-1 shadow-elevated z-50 rounded-md border border-border/60 bg-card text-card-foreground text-xs flex flex-col gap-0.5 {className}"
    >
      {#if children}
        {@render children()}
      {:else}
        {#each items as item (item.label)}
          <BitsDropdownMenu.Item
            disabled={item.disabled}
            onSelect={() => item.onclick?.()}
            class="px-2.5 py-1.5 rounded cursor-pointer select-none text-xs font-semibold text-foreground/90 hover:bg-primary/20 hover:text-foreground transition-colors disabled:opacity-40 disabled:cursor-not-allowed outline-hidden"
          >
            {item.label}
          </BitsDropdownMenu.Item>
        {/each}
      {/if}
    </BitsDropdownMenu.Content>
  </BitsDropdownMenu.Portal>
</BitsDropdownMenu.Root>
