<script module lang="ts">
  import type { Component } from 'svelte';

  export interface SegmentOption<V extends string = string> {
    value: V;
    label: string;
    icon?: Component;
    badge?: string | number;
  }
</script>

<script lang="ts" generics="T extends string">
  import { Tabs as BitsTabs } from 'bits-ui';
  import Badge from './Badge.svelte';

  interface Props {
    options: SegmentOption<T>[];
    value?: T;
    onchange?: (val: T) => void;
    class?: string;
  }

  let {
    options = [],
    value = $bindable() as T,
    onchange,
    class: className = ''
  }: Props = $props();

  function handleValueChange(newVal: string) {
    value = newVal as T;
    onchange?.(newVal as T);
  }
</script>

<BitsTabs.Root
  value={value}
  onValueChange={handleValueChange}
  class="w-full"
>
  <BitsTabs.List
    class="segmented-control {className}"
    aria-label="View selection"
  >
    {#each options as opt (opt.value)}
      {@const isActive = value === opt.value}
      {@const IconComponent = opt.icon}
      <BitsTabs.Trigger
        value={opt.value}
        class="segmented-item {isActive ? 'segmented-item-active' : ''}"
      >
        {#if IconComponent}
          <IconComponent class="w-3.5 h-3.5 shrink-0" />
        {/if}
        <span>{opt.label}</span>
        {#if opt.badge !== undefined}
          <Badge variant={isActive ? 'muted' : 'primary'} class="text-[10px] !py-0 !px-1">
            {opt.badge}
          </Badge>
        {/if}
      </BitsTabs.Trigger>
    {/each}
  </BitsTabs.List>
</BitsTabs.Root>
