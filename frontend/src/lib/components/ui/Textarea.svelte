<script lang="ts">
  interface Props {
    id?: string;
    value?: string;
    placeholder?: string;
    rows?: number;
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
    rows = 4,
    disabled = false,
    label = '',
    oninput,
    onchange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `textarea-${Math.random().toString(36).substring(2, 9)}`);
</script>

<div class="flex flex-col gap-1 w-full">
  {#if label}
    <label for={elementId} class="text-xs font-bold text-muted-foreground">{label}</label>
  {/if}
  <textarea
    id={elementId}
    {placeholder}
    {rows}
    {disabled}
    bind:value
    {oninput}
    {onchange}
    class="textarea-base {className}"
  ></textarea>
</div>
