<script lang="ts">
  export interface SelectOption {
    label: string;
    value: string;
  }

  interface Props {
    id?: string;
    value?: string | number | null;
    options?: SelectOption[] | string[];
    label?: string;
    disabled?: boolean;
    onchange?: (e: Event) => void;
    class?: string;
  }

  let {
    id,
    value = $bindable(),
    options = [],
    label = '',
    disabled = false,
    onchange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `select-${Math.random().toString(36).substring(2, 9)}`);

  let formattedOptions = $derived(
    options.map((opt) => (typeof opt === 'string' ? { label: opt, value: opt } : opt))
  );
</script>

<div class="flex flex-col gap-1 w-full">
  {#if label}
    <label for={elementId} class="text-xs font-bold text-muted-foreground">{label}</label>
  {/if}
  <select
    id={elementId}
    bind:value
    {disabled}
    {onchange}
    class="input-base cursor-pointer {className}"
  >
    {#each formattedOptions as opt (opt.value)}
      <option value={opt.value} class="bg-card text-foreground">{opt.label}</option>
    {/each}
  </select>
</div>
