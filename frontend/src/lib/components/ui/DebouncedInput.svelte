<script lang="ts">
  import { onDestroy } from 'svelte';
  import { DebouncedInputController } from './DebouncedInputController';
  import { X } from '@lucide/svelte';

  interface Props {
    id?: string;
    value?: string;
    placeholder?: string;
    delayMs?: number;
    label?: string;
    disabled?: boolean;
    onchange?: (val: string) => void;
    class?: string;
  }

  let {
    id,
    value = $bindable(),
    placeholder = 'Search...',
    delayMs = 300,
    label = '',
    disabled = false,
    onchange,
    class: className = ''
  }: Props = $props();

  const elementId = $derived(id || `debounced-input-${Math.random().toString(36).substring(2, 9)}`);
  const controller = new DebouncedInputController();

  function onInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = target.value;
    controller.handleInput(value, delayMs, (val) => {
      if (onchange) onchange(val);
    });
  }

  onDestroy(() => {
    controller.cancel();
  });
</script>

<div class="flex flex-col gap-1 w-full">
  {#if label}
    <label for={elementId} class="text-xs font-bold text-muted-foreground">{label}</label>
  {/if}
  <div class="relative flex items-center w-full">
    <input
      id={elementId}
      type="text"
      {value}
      {placeholder}
      {disabled}
      oninput={onInput}
      class="input-base {className}"
    />
    {#if value}
      <button
        type="button"
        onclick={() => {
          value = '';
          if (onchange) onchange('');
        }}
        class="absolute right-2 text-muted-foreground hover:text-foreground text-xs p-1 cursor-pointer"
        aria-label="Clear input"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    {/if}
  </div>
</div>
