<script lang="ts">
  interface Props {
    id?: string;
    value?: string | number | null;
    placeholder?: string;
    type?: string;
    disabled?: boolean;
    label?: string;
    oninput?: (e: Event) => void;
    onchange?: (e: Event) => void;
    class?: string;
  }

  let {
    id,
    value = $bindable(),
    placeholder = '',
    type = 'text',
    disabled = false,
    label = '',
    oninput,
    onchange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `input-${Math.random().toString(36).substring(2, 9)}`);
</script>

<div class="flex flex-col gap-1 w-full">
  {#if label}
    <label for={elementId} class="text-xs font-bold text-muted-foreground">{label}</label>
  {/if}
  <input
    id={elementId}
    {type}
    {placeholder}
    {disabled}
    bind:value
    {oninput}
    {onchange}
    class="input-base {className}"
  />
</div>
