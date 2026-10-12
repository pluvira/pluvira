<script lang="ts">
  import { Checkbox as BitsCheckbox } from 'bits-ui';
  import { Check, Minus } from '@lucide/svelte';

  interface Props {
    id?: string;
    checked?: boolean | 'indeterminate';
    disabled?: boolean;
    label?: string;
    'aria-label'?: string;
    onCheckedChange?: (checked: boolean | 'indeterminate') => void;
    class?: string;
  }

  let {
    id,
    checked = $bindable(),
    disabled = false,
    label = '',
    'aria-label': ariaLabel = '',
    onCheckedChange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `checkbox-${Math.random().toString(36).substring(2, 9)}`);
  const isChecked = $derived(checked === true);
  const isIndeterminate = $derived(checked === 'indeterminate');

  function handleCheckedChange(val: boolean) {
    checked = val;
    onCheckedChange?.(val);
  }
</script>

<div class="inline-flex items-center gap-2 select-none {className}">
  <BitsCheckbox.Root
    id={elementId}
    checked={isChecked}
    indeterminate={isIndeterminate}
    {disabled}
    aria-label={ariaLabel || label || undefined}
    onCheckedChange={handleCheckedChange}
    class="peer h-4 w-4 shrink-0 rounded-xs border border-border bg-background transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground cursor-pointer flex items-center justify-center"
  >
    {#snippet children({ checked, indeterminate })}
      {#if indeterminate}
        <Minus class="w-3 h-3 text-current stroke-[3]" />
      {:else if checked}
        <Check class="w-3 h-3 text-current stroke-[3]" />
      {/if}
    {/snippet}
  </BitsCheckbox.Root>
  {#if label}
    <label
      for={elementId}
      class="text-xs font-semibold text-foreground cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    >
      {label}
    </label>
  {/if}
</div>
