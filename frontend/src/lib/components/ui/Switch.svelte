<script lang="ts">
  import { Switch as BitsSwitch } from 'bits-ui';

  interface Props {
    id?: string;
    checked?: boolean;
    disabled?: boolean;
    label?: string;
    onCheckedChange?: (checked: boolean) => void;
    class?: string;
  }

  let {
    id,
    checked = $bindable(),
    disabled = false,
    label = '',
    onCheckedChange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `switch-${Math.random().toString(36).substring(2, 9)}`);
</script>

<div class="inline-flex items-center gap-2 select-none {className}">
  <BitsSwitch.Root
    id={elementId}
    bind:checked
    {disabled}
    {onCheckedChange}
    class="peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-muted"
  >
    <BitsSwitch.Thumb
      class="pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0"
    />
  </BitsSwitch.Root>
  {#if label}
    <label
      for={elementId}
      class="text-xs font-semibold text-foreground cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    >
      {label}
    </label>
  {/if}
</div>
